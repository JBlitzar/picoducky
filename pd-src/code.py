import time
import usb_cdc  # type: ignore
import usb_hid  # type: ignore
from adafruit_hid.keyboard import Keyboard  # type: ignore
from adafruit_hid.keycode import Keycode  # type: ignore
from adafruit_hid.mouse_abs import Mouse  # type: ignore
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS  # type: ignore

MAGIC_SEQUENCE = b"\x4a\x42\x67\x41"
BOOTSTRAP_URL = "https://raw.githubusercontent.com/JBlitzar/picoducky/refs/heads/main/cc-src/bootstrap.sh"

ser = usb_cdc.data

kbd = Keyboard(usb_hid.devices)
layout = KeyboardLayoutUS(kbd)
mouse = Mouse(usb_hid.devices)

SYM_TO_MOD = {
    "⌘": Keycode.GUI,
    "⇧": Keycode.SHIFT,
    "⌥": Keycode.ALT,
    "⌃": Keycode.CONTROL,
}


def _char_to_keycode(ch: str):
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


def type_sequence(seq):
    for token in seq:
        mods = []
        enter = False
        chars = []
        for ch in token:
            if ch in SYM_TO_MOD:
                mods.append(SYM_TO_MOD[ch])
            elif ch == "↩︎":
                enter = True
            else:
                chars.append(ch)

        if enter:
            if mods:
                kbd.press(*mods, Keycode.ENTER)
                kbd.release_all()
            else:
                kbd.press(Keycode.ENTER)
                kbd.release_all()
            time.sleep(0.03)
            continue

        named = "".join(chars).lower()

        # Handle named special keys first (works with or without modifiers)
        special_map = {
            "space": Keycode.SPACEBAR,
            "backspace": Keycode.BACKSPACE,
            "tab": Keycode.TAB,
            "enter": Keycode.ENTER,
            "return": Keycode.ENTER,
            "escape": Keycode.ESCAPE,
            "esc": Keycode.ESCAPE,
        }
        if named in special_map:
            kc = special_map[named]
            if mods:
                kbd.press(*mods, kc)
                kbd.release_all()
            else:
                kbd.press(kc)
                kbd.release_all()
            time.sleep(0.02)
            continue

        if mods and chars:
            for ch in chars:
                kc = _char_to_keycode(ch)
                if kc is None:
                    continue
                kbd.press(*mods, kc)
                kbd.release_all()
                time.sleep(0.02)
            continue

        if not mods and chars:
            layout.write("".join(chars))
            time.sleep(0.02)


_mx = 0
_my = 0


def _send_abs_mouse(x=None, y=None, wheel=0):
    global _mx, _my
    if x is None:
        x = _mx
    if y is None:
        y = _my
    mouse.move(x, y, wheel)
    _mx = x
    _my = y


# Initial bootstrap: open Terminal and run bootstrap script
kbd.press(Keycode.GUI, Keycode.SPACE)
kbd.release_all()
time.sleep(0.5)
layout.write("terminal")
time.sleep(0.5)
kbd.press(Keycode.ENTER)
kbd.release_all()
time.sleep(0.5)
layout.write(f"curl -sSL {BOOTSTRAP_URL} | bash")
kbd.press(Keycode.ENTER)
kbd.release_all()
time.sleep(0.8)

# Center the mouse
mouse.move(16384, 16384, 0)
# Track last absolute position so wheel/clicks don't jump to 0,0
_mx = 16384
_my = 16384

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
    # process full lines
    if b"\n" in buffer or b"\r" in buffer:
        for sep in (b"\r\n", b"\n", b"\r"):
            if sep in buffer:
                line, _, rest = buffer.partition(sep)
                buffer = bytearray(rest)
                try:
                    if not line.startswith(MAGIC_SEQUENCE):
                        break
                    payload = line[len(MAGIC_SEQUENCE) :].decode("utf-8", "replace")
                    parts = payload.split(";")
                    cmd = parts[0] if parts else ""
                    if cmd == "mouse" and len(parts) > 1:
                        sx, sy = parts[1].split(",")
                        _send_abs_mouse(int(sx), int(sy), 0)
                    elif cmd in ("mousewheel", "wheel") and len(parts) > 1:
                        _send_abs_mouse(None, None, int(parts[1]))
                    elif cmd == "mouseclick" and len(parts) > 1:
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
                    elif cmd == "type" and len(parts) > 1:
                        sequence = "".join(parts[1:]).split(",,")
                        type_sequence(sequence)
                except Exception:
                    pass
                break
    time.sleep(0.01)
