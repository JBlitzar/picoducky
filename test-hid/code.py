import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from adafruit_hid.mouse import Mouse
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
import board
import time


kbd = Keyboard(usb_hid.devices)
layout = KeyboardLayoutUS(kbd)
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
