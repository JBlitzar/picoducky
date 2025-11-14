import time
import usb_cdc  # type: ignore
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from adafruit_hid.mouse_abs import Mouse
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS


ser = usb_cdc.data


kbd = Keyboard(usb_hid.devices)
layout = KeyboardLayoutUS(kbd)
layout.write("hello world")
kbd.press(Keycode.GUI, Keycode.SPACE)
kbd.release_all()
time.sleep(0.5)
layout.write("terminal")
time.sleep(0.5)
kbd.press(Keycode.ENTER)
kbd.release_all()
time.sleep(0.5)
layout.write("echo hello world")
kbd.press(Keycode.ENTER)
kbd.release_all()
time.sleep(1)

mouse = Mouse(usb_hid.devices)
mouse.move(16384, 16384, 0)

# Wait for host to open the serial port
while not ser.connected:
    time.sleep(0.05)

ser.write(b"READY\n")

buffer = bytearray()
while True:
    if ser.in_waiting:
        chunk = ser.read(ser.in_waiting)
        if chunk:
            buffer.extend(chunk)
    # Process complete lines
    if b"\n" in buffer or b"\r" in buffer:
        # Normalize any of \r, \n, or \r\n
        for sep in (b"\r\n", b"\n", b"\r"):
            if sep in buffer:
                line, _, rest = buffer.partition(sep)
                buffer = bytearray(rest)
                text = line.decode("utf-8", "replace").strip()
                if text.lower() == "ping":
                    ser.write(b"pong\n")
                else:
                    ser.write(b"echo: " + line + b"\n")
                break
    time.sleep(0.01)
