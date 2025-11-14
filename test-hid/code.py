import time
import usb_cdc  # type: ignore
import board
import digitalio


# Minimal USB serial listener (uses usb_cdc.data enabled in boot.py)
led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT

ser = usb_cdc.data

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
                    led.value = not led.value
                else:
                    ser.write(b"echo: " + line + b"\n")
                break
    time.sleep(0.01)
