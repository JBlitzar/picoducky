import time
import pwmio
import board


class PDLED:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PDLED, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        self.red_pwm = pwmio.PWMOut(board.GP19, frequency=1000, duty_cycle=0)
        self.green_pwm = pwmio.PWMOut(board.GP20, frequency=1000, duty_cycle=0)
        self.blue_pwm = pwmio.PWMOut(board.GP21, frequency=1000, duty_cycle=0)

    def set_color(self, r: int, g: int, b: int):
        self.red_pwm.duty_cycle = int((r / 255) * 65535)
        self.green_pwm.duty_cycle = int((g / 255) * 65535)
        self.blue_pwm.duty_cycle = int((b / 255) * 65535)

    def turn_off(self):
        self.set_color(0, 0, 0)

    def flash(self, r: int, g: int, b: int, duration: float = 0.05):
        self.set_color(r, g, b)
        time.sleep(duration)
        self.turn_off()
