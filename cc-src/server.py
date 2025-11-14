import pygame
import socket
import threading
import base64
import io
from PIL import Image
import time

PORT = 9337

# should be (w,h)
display_size = None
remote_size = None


def screenshot_callback(img_data: bytes):
    try:
        print("DING DING DING SCREENSHOT CALLBACK")
        # Scale image to half size

        image = Image.open(
            io.BytesIO(img_data)
        )  # haha reparse and get bytes back from image
        # idk ai wrote this part

        original_size = image.size
        new_size = (original_size[0] // 4, original_size[1] // 4)
        new_image = image.resize(new_size, Image.Resampling.LANCZOS)

        # image.save("latest_screenshot.png")

        mode = new_image.mode
        size = new_image.size

        data = new_image.tobytes()

        pygame_image = pygame.image.fromstring(data, size, mode)

        screen = pygame.display.get_surface()
        if screen:
            screen.blit(pygame_image, (0, 0))
            pygame.display.flip()

        # Record sizes for coordinate scaling
        global display_size, remote_size
        display_size = new_size
        remote_size = original_size

    except Exception as e:
        print(f"Error displaying screenshot: {e}")


def handle_client_connection(client_socket, client_address):
    try:
        buffer = ""
        while True:
            data = client_socket.recv(65536)
            if not data:
                break

            buffer += data.decode("utf-8")

            ss_prefix = "SCREENSHOT:"
            if buffer.startswith(ss_prefix):
                # Find the end of the screenshot data (assuming it's complete)
                screenshot_data = buffer[len(ss_prefix) :]
                try:
                    img_data = base64.b64decode(screenshot_data)
                    print("About to call screenshot_callback")
                    screenshot_callback(img_data)
                    buffer = ""
                except Exception as e:
                    print(f"haha error: {e}")
            else:
                if "\n" in buffer or len(buffer) > 100 * 1024 * 1024:
                    print(f"Received command: {buffer[:100]}")
                    buffer = ""

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
