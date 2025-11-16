import time
import socket
import threading
import os
import base64
import io
import struct
import subprocess
import sys
import binascii
import shutil
import glob
import json
from PIL import Image
try:
    import serial  # type: ignore
except Exception:
    serial = None

SERVER_IP_PORT = "192.168.7.188:9337"

# Profiling toggle: set PD_PROFILE=1 to enable JSON logs
PROFILE = True  # os.getenv("PD_PROFILE", "0") == "1"

_perf = time.perf_counter
_last_hid_sent = None
_frame_id = 0
_shot_pending = False
_last_trigger_time = 0.0

_SCALE_FACTOR = int(os.getenv("PD_SCALE_FACTOR", "4"))
_JPEG_QUALITY = int(os.getenv("PD_JPEG_QUALITY", "70"))

_ser_handle = None
_ser_port = None
_ser_lock = threading.Lock()


def get_clipboard_content():
    if sys.platform == "darwin":  # macOS
        return subprocess.check_output("pbpaste", universal_newlines=True)
    elif sys.platform == "win32":  # Windows
        return subprocess.check_output(
            "powershell Get-Clipboard", universal_newlines=True
        )
    else:  # Linux
        return subprocess.check_output("xclip -o", universal_newlines=True)


def write_to_clipboard(content):
    if sys.platform == "darwin":  # macOS
        subprocess.run("pbcopy", universal_newlines=True, input=content)
    elif sys.platform == "win32":  # Windows
        subprocess.run(
            "powershell Set-Clipboard", universal_newlines=True, input=content
        )
    else:  # Linux
        subprocess.run(
            "xclip -selection clipboard", universal_newlines=True, input=content
        )


def _ensure_serial():
    global _ser_handle, _ser_port
    if serial is None:
        return None
    if _ser_handle is not None:
        return _ser_handle
    patterns = ["/dev/cu.usbmodem*", "/dev/tty.usbmodem*", "/dev/ttyACM*"]
    devs = []
    for p in patterns:
        devs.extend(glob.glob(p))
    for port in sorted(set(devs)):
        try:
            h = serial.Serial(port=port, baudrate=115200, timeout=0, write_timeout=0)
            try:
                h.dtr = True
            except Exception:
                pass
            _ser_handle = h
            _ser_port = port
            return _ser_handle
        except Exception:
            continue
    return None


def send_command_to_usb_device(command: str):
    MAGIC_SEQUENCE = b"\x4a\x42\x67\x41"
    payload = MAGIC_SEQUENCE + command.encode("utf-8")
    if not payload.endswith(b"\n"):
        payload += b"\n"

    if serial is not None:
        with _ser_lock:
            h = _ensure_serial()
            if h is not None:
                try:
                    h.write(payload)
                    h.flush()
                    print(f"Sent command to {_ser_port}: {command!r}")
                    return
                except Exception as e:
                    try:
                        h.close()
                    except Exception:
                        pass
                    globals()["_ser_handle"] = None
                    globals()["_ser_port"] = None
                    print(f"Serial write failed, will retry later: {e}")
                    return

    patterns = ["/dev/tty.usbmodem*", "/dev/cu.usbmodem*", "/dev/ttyACM*"]
    devices = []
    for pattern in patterns:
        devices.extend(glob.glob(pattern))
    for device in sorted(set(devices)):
        try:
            with open(device, "wb", buffering=0) as f:
                f.write(payload)
            print(f"Sent command to {device}: {command!r}")
            return
        except (OSError, IOError):
            continue
    print("Could not send command")


# https://pillow.readthedocs.io/en/stable/_modules/PIL/ImageGrab.html#grabclipboard
def grabclipboard_img() -> bytes | list[str] | None:
    if sys.platform == "darwin":
        p = subprocess.run(
            ["osascript", "-e", "get the clipboard as «class PNGf»"],
            capture_output=True,
        )
        if p.returncode != 0:
            return None

        return binascii.unhexlify(p.stdout[11:-3])
    else:
        return NotImplementedError("haha lol macos only")


def monitor_and_send_screenshots(sock):
    while True:
        try:
            t_clip = _perf()
            content = grabclipboard_img()
            if content is not None:
                global _frame_id
                _frame_id += 1
                # Decode PNG, downscale, JPEG encode, send binary frame
                t_open_s = _perf()
                img = Image.open(io.BytesIO(content))
                orig_w, orig_h = img.size
                t_open_e = _perf()

                t_down_s = _perf()
                if _SCALE_FACTOR > 1:
                    img = img.reduce(_SCALE_FACTOR)
                t_down_e = _perf()

                t_jpeg_s = _perf()
                bio = io.BytesIO()
                img.convert("RGB").save(
                    bio, format="JPEG", quality=_JPEG_QUALITY, optimize=True
                )
                jpeg_bytes = bio.getvalue()
                t_jpeg_e = _perf()

                header = b"SSV1" + struct.pack(">III", len(jpeg_bytes), orig_w, orig_h)
                t_sends = _perf()
                sock.sendall(header)
                sock.sendall(jpeg_bytes)
                t_sende = _perf()

                if PROFILE:
                    hid_to_clip = None
                    if _last_hid_sent is not None:
                        hid_to_clip = max(0.0, t_clip - _last_hid_sent)
                    print(
                        json.dumps(
                            {
                                "side": "client",
                                "event": "frame",
                                "id": _frame_id,
                                "hid_to_clip_s": hid_to_clip,
                                "open_s": t_open_e - t_open_s,
                                "downscale_s": t_down_e - t_down_s,
                                "jpeg_s": t_jpeg_e - t_jpeg_s,
                                "send_s": t_sende - t_sends,
                                "jpeg_bytes": len(jpeg_bytes),
                                "orig_bytes": len(content),
                                "orig_size": [orig_w, orig_h],
                            }
                        ),
                        flush=True,
                    )
                write_to_clipboard("")
                # mark this screenshot as processed so trigger thread can request next one
                global _shot_pending
                _shot_pending = False
            else:
                time.sleep(0.01)
        except Exception as e:
            print(f"eek error : {e}")
            break


def periodic_hid_screenshot():
    while True:
        try:
            if sys.platform == "darwin":
                global _last_hid_sent, _shot_pending, _last_trigger_time
                now = _perf()
                if (not _shot_pending) or (now - _last_trigger_time > 0.2):
                    _last_hid_sent = now
                    send_command_to_usb_device("type;⌘⌃⇧3\n")
                    _shot_pending = True
                    _last_trigger_time = now
            time.sleep(0.1)
        except Exception as e:
            print(f"periodic HID screenshot error: {e}")
            break


def handle_server_connection():
    """Connect to server and handle commands"""
    try:
        host, port = SERVER_IP_PORT.split(":")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Optional: bind to a specific source IP (e.g., your 192.168.7.x)
        src_ip = os.getenv("PD_SRC_IP")
        if not src_ip:
            src_ip = SERVER_IP_PORT.split(":")[0]
        if src_ip:
            try:
                sock.bind((src_ip, 0))
            except Exception as _e:
                pass

        # Retry on transient ENETUNREACH (errno 51)
        for attempt in range(5):
            try:
                sock.connect((host, int(port)))
                break
            except OSError as e:
                if getattr(e, "errno", None) == 51 and attempt < 4:
                    time.sleep(1.0)
                    continue
                raise
        print(f"Connected to server at {SERVER_IP_PORT}")

        screenshot_thread = threading.Thread(
            target=monitor_and_send_screenshots, args=(sock,)
        )
        screenshot_thread.daemon = True
        screenshot_thread.start()

        hid_ss_thread = threading.Thread(target=periodic_hid_screenshot)
        hid_ss_thread.daemon = True
        hid_ss_thread.start()

        while True:
            data = sock.recv(1024)
            if not data:
                break

            command = data.decode("utf-8").strip()
            for thing in command.split("\n"):
                if thing:
                    send_command_to_usb_device(thing)

    except Exception as e:
        print(f"Connection error: {e}")
    finally:
        sock.close()


if __name__ == "__main__":
    handle_server_connection()
