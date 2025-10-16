import time
import socket
import threading
import os
import tempfile
import base64
import io
import glob

SERVER_IP_PORT = "127.0.0.1:9337"


def send_command_to_usb_device(command: str):
    print(f"Would send command to USB device: {command}")
    MAGIC_SEQUENCE = b"\x42\x67\x4a\x79"
    data = MAGIC_SEQUENCE + command.encode("utf-8")
    # lol


def monitor_and_send_screenshots(sock):
    desktop_path = os.path.expanduser("~/Desktop")

    while True:
        try:
            for filename in glob.glob(os.path.join(desktop_path, "Screenshot*.png")):
                file_path = os.path.join(desktop_path, filename)
                try:
                    with open(file_path, "rb") as img_file:
                        img_data = img_file.read()
                        encoded_img = base64.b64encode(img_data).decode("utf-8")

                    message = f"SCREENSHOT:{encoded_img}\n"
                    sock.sendall(message.encode("utf-8"))

                    os.remove(file_path)

                except Exception as e:
                    print(f"eek error : {e}")

            time.sleep(1)
        except Exception as e:
            print(f"eek error (outside) : {e}")
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
