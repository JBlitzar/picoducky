import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from adafruit_hid.mouse import Mouse
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
import board


kbd = Keyboard(usb_hid.devices)
layout = KeyboardLayoutUS(kbd)
layout.write("hello world")
