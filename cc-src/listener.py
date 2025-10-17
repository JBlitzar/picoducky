import time
import socket
import threading
import os
import base64
import subprocess
import sys
import binascii
import shutil

SERVER_IP_PORT = "127.0.0.1:9337"


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
    print(f"Would send command to USB device: {command}")
    MAGIC_SEQUENCE = b"\x4a\x42\x67\x41"
    data = MAGIC_SEQUENCE + command.encode("utf-8")
    # lol


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
            content = grabclipboard_img()
            if content is not None:
                # Assuming the content is a base64 encoded image
                encoded_img = base64.b64encode(content).decode("utf-8")
                message = f"SCREENSHOT:{encoded_img}\n"
                sock.sendall(message.encode("utf-8"))

                # Clear the clipboard
                write_to_clipboard("")
        except Exception as e:
            print(f"eek error : {e}")
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
