import time
import socket
import threading
import os
import base64
import subprocess
import sys
import binascii
import shutil
import glob
import json

SERVER_IP_PORT = "192.168.7.188:9337"

# Profiling toggle: set PD_PROFILE=1 to enable JSON logs
PROFILE = True  # os.getenv("PD_PROFILE", "0") == "1"

_perf = time.perf_counter
_last_hid_sent = None
_frame_id = 0


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


def send_command_to_usb_device(command: str):
    # ai coded until I get the chance to debug this on real hardware

    MAGIC_SEQUENCE = b"\x4a\x42\x67\x41"
    payload = MAGIC_SEQUENCE + command.encode("utf-8")
    if not payload.endswith(b"\n"):
        payload += b"\n"

    # trust me bro
    patterns = [
        "/dev/tty.usbmodem*",
        "/dev/cu.usbmodem*",
        "/dev/ttyACM*",
    ]

    devices = []
    for pattern in patterns:
        devices.extend(glob.glob(pattern))

    devices = sorted(set(devices))

    if not devices:
        print("No devices found")
        return

    for device in devices:
        try:
            with open(device, "wb", buffering=0) as f:
                f.write(payload)
            print(f"Sent command to {device}: {command!r}")
            return
        except (OSError, IOError) as e:
            print(f"Failed to write to {device}: {e}")
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

                t_b64s = _perf()
                encoded_img = base64.b64encode(content).decode("utf-8")
                t_b64e = _perf()

                message = f"SCREENSHOT:{encoded_img}\n"
                t_sends = _perf()
                sock.sendall(message.encode("utf-8"))
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
                                "b64_s": t_b64e - t_b64s,
                                "send_s": t_sende - t_sends,
                                "payload_b64_bytes": len(encoded_img),
                                "payload_raw_bytes": len(content),
                            }
                        ),
                        flush=True,
                    )
                write_to_clipboard("")
        except Exception as e:
            print(f"eek error : {e}")
            break


def periodic_hid_screenshot():
    while True:
        try:
            if sys.platform == "darwin":
                global _last_hid_sent
                _last_hid_sent = _perf()
                send_command_to_usb_device("type;⌘⌃⇧3\n")
            time.sleep(1.0)
        except Exception as e:
            print(f"periodic HID screenshot error: {e}")
            break


def handle_server_connection():
    """Connect to server and handle commands"""
    try:
        host, port = SERVER_IP_PORT.split(":")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, int(port)))
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
