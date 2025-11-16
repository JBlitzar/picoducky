import pygame
import socket
import threading
import io
import struct
from PIL import Image
import time
import json
import os

PORT = 9337

# should be (w,h)
display_size = None
remote_size = None

# Profiling toggle: set PD_PROFILE=1 to enable JSON logs
PROFILE = True  # os.getenv("PD_PROFILE", "0") == "1" if 'os' in globals() else False


def screenshot_callback(img_data: bytes, orig_size):
    try:
        if PROFILE:
            print(json.dumps({"side": "server", "event": "callback"}), flush=True)
        t_open_s = time.perf_counter()
        image = Image.open(io.BytesIO(img_data))
        t_open_e = time.perf_counter()
        new_image = image
        new_size = new_image.size
        t_resize_s = t_open_e
        t_resize_e = t_open_e

        # image.save("latest_screenshot.png")

        mode = new_image.mode
        size = new_image.size

        t_bytes_s = time.perf_counter()
        data = new_image.tobytes()
        t_bytes_e = time.perf_counter()

        t_pyg_s = time.perf_counter()
        pygame_image = pygame.image.fromstring(data, size, mode)
        t_pyg_e = time.perf_counter()

        t_blit_s = time.perf_counter()
        screen = pygame.display.get_surface()
        if screen:
            screen.blit(pygame_image, (0, 0))
            pygame.display.flip()
        t_blit_e = time.perf_counter()

        # Record sizes for coordinate scaling
        global display_size, remote_size
        display_size = new_size
        remote_size = orig_size

        if PROFILE:
            print(
                json.dumps(
                    {
                        "side": "server",
                        "event": "display",
                        "open_s": t_open_e - t_open_s,
                        "resize_s": t_resize_e - t_resize_s,
                        "to_bytes_s": t_bytes_e - t_bytes_s,
                        "pygame_from_s": t_pyg_e - t_pyg_s,
                        "blit_flip_s": t_blit_e - t_blit_s,
                        "display_size": list(display_size),
                        "remote_size": list(remote_size),
                    }
                ),
                flush=True,
            )

    except Exception as e:
        print(f"Error displaying screenshot: {e}")


def handle_client_connection(client_socket, client_address):
    try:
        buffer = b""
        t_recv0 = None
        recv_calls = 0
        MAGIC = b"SSV1"
        HEADER_SIZE = 4 + 12  # magic + length(uint32) + orig_w(uint32) + orig_h(uint32)
        while True:
            chunk = client_socket.recv(65536)
            if not chunk:
                break
            buffer += chunk
            recv_calls += 1

            while True:
                if len(buffer) < 4:
                    break
                # align to magic
                if not buffer.startswith(MAGIC):
                    idx = buffer.find(MAGIC)
                    if idx == -1:
                        buffer = b""
                        break
                    buffer = buffer[idx:]
                    t_recv0 = None
                    recv_calls = 0
                if len(buffer) < HEADER_SIZE:
                    break
                _, length, ow, oh = (buffer[:4],) + struct.unpack(">III", buffer[4:16])
                total = HEADER_SIZE + length
                if len(buffer) < total:
                    if t_recv0 is None:
                        t_recv0 = time.perf_counter()
                    break
                payload = buffer[HEADER_SIZE:total]
                buffer = buffer[total:]
                t_done = time.perf_counter()
                if PROFILE and t_recv0 is not None:
                    print(
                        json.dumps(
                            {
                                "side": "server",
                                "event": "recv_frame",
                                "recv_window_s": t_done - t_recv0,
                                "recv_calls": recv_calls,
                                "frame_bytes": length,
                                "orig_size": [ow, oh],
                            }
                        ),
                        flush=True,
                    )
                screenshot_callback(payload, (ow, oh))
                t_recv0 = None
                recv_calls = 0

    except Exception as e:
        print(f"haha error: {e}")
    finally:
        client_socket.close()


_client_socket = None


def send_command_to_client(command: str):
    global _client_socket
    if _client_socket is None:
        return
    try:
        _client_socket.sendall(command.encode("utf-8"))
        print(f"Sent command: {command}")
    except Exception as e:
        print(f"Error sending command: {e}")


def start_server():
    global _client_socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("0.0.0.0", PORT))
    server_socket.listen(5)
    print(f"Server listening on port {PORT}")

    try:
        while True:
            if _client_socket is not None:
                continue
            client_socket, client_address = server_socket.accept()
            client_thread = threading.Thread(
                target=handle_client_connection, args=(client_socket, client_address)
            )
            client_thread.daemon = True
            client_thread.start()
            _client_socket = client_socket
    except KeyboardInterrupt:
        print("Server shutting down...")
    finally:
        server_socket.close()


last_mouse_sent_timestamp = 0


def on_mouse_move(x, y):
    global last_mouse_sent_timestamp
    current_time = time.time()
    if current_time - last_mouse_sent_timestamp < 0.05:
        return

    # scaling coordinates because HID absolute range is 0..32767 for both X and Y
    if display_size and remote_size:
        dw, dh = display_size
        rw, rh = remote_size

        sx = max(0, min(x, max(dw - 1, 0)))
        sy = max(0, min(y, max(dh - 1, 0)))

        rx = int(sx * rw / max(dw, 1))
        ry = int(sy * rh / max(dh, 1))

        abs_x = int(rx * 32767 / max(rw - 1, 1))
        abs_y = int(ry * 32767 / max(rh - 1, 1))

        send_command_to_client(f"mouse;{abs_x},{abs_y}\n")
    else:
        # Fallback: assume remote is 16:9 (e.g., 1920x1080) and map window coords to 0..32767
        try:
            surf = pygame.display.get_surface()
            if surf is not None:
                dw, dh = surf.get_size()
            else:
                dw, dh = 1280, 720

            sx = max(0, min(x, max(dw - 1, 0)))
            sy = max(0, min(y, max(dh - 1, 0)))

            rw, rh = 1920, 1080
            rx = int(sx * rw / max(dw, 1))
            ry = int(sy * rh / max(dh, 1))

            abs_x = int(rx * 32767 / max(rw - 1, 1))
            abs_y = int(ry * 32767 / max(rh - 1, 1))
            send_command_to_client(f"mouse;{abs_x},{abs_y}\n")
        except Exception:
            # Last resort: clamp to 0..32767 using window size directly
            surf = pygame.display.get_surface()
            if surf is not None:
                dw, dh = surf.get_size()
            else:
                dw, dh = 1, 1
            abs_x = int(max(0, min(x, max(dw - 1, 0))) * 32767 / max(dw - 1, 1))
            abs_y = int(max(0, min(y, max(dh - 1, 0))) * 32767 / max(dh - 1, 1))
            send_command_to_client(f"mouse;{abs_x},{abs_y}\n")

    last_mouse_sent_timestamp = current_time


def on_mouse_wheel(delta):
    try:
        send_command_to_client(f"wheel;{int(delta)}\n")
    except Exception:
        pass


# the truly elegant solution would to just have seperate press and release command propogate properly
pressed_keys = []


def on_key_press(key):
    pressed_keys.append(key)


def on_key_release(key):
    global pressed_keys

    combo = []
    for k in list(pressed_keys):
        key_str = pygame.key.name(k)
        if "meta" in key_str:
            key_str = "⌘"
        elif "alt" in key_str:
            key_str = "⌥"
        elif "shift" in key_str:
            key_str = "⇧"
        elif "ctrl" in key_str:
            key_str = "⌃"
        elif "return" in key_str:
            key_str = "↩︎"
        combo.append(key_str)
    if combo:
        send_command_to_client(f"type;{''.join(combo)}\n")
    pressed_keys = []


def main():
    pygame.init()
    screen = pygame.display.set_mode(
        (
            1728 // 2,
            1117 // 2,
        )
    )
    pygame.display.set_caption("CC server")
    clock = pygame.time.Clock()
    running = True

    # Start server in a separate thread
    server_thread = threading.Thread(target=start_server)
    server_thread.daemon = True
    server_thread.start()

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEMOTION:
                on_mouse_move(event.pos[0], event.pos[1])
            elif event.type == pygame.MOUSEWHEEL:
                on_mouse_wheel(event.y)
            elif event.type == pygame.KEYDOWN:
                on_key_press(event.key)
            elif event.type == pygame.KEYUP:
                on_key_release(event.key)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                send_command_to_client(f"mouseclick;{event.button},1\n")
            elif event.type == pygame.MOUSEBUTTONUP:
                send_command_to_client(f"mouseclick;{event.button},0\n")

        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
