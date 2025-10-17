import time
import pwmio
import board


class PDLED:
    RED = (255, 0, 0)
    GREEN = (0, 255, 0)
    BLUE = (0, 0, 255)
    WHITE = (255, 255, 255)
    OFF = (0, 0, 0)
    CYAN = (0, 255, 255)
    MAGENTA = (255, 0, 255)
    YELLOW = (255, 255, 0)
    ORANGE = (255, 165, 0)
    PURPLE = (128, 0, 128)
    GRAY = (128, 128, 128)

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

    def set_color_tuple(self, color: tuple):
        self.set_color(color[0], color[1], color[2])

    def turn_off(self):
        self.set_color(0, 0, 0)

    def flash_blocking(self, r: int, g: int, b: int, duration: float = 0.05):
        self.set_color(r, g, b)
        time.sleep(duration)
        self.turn_off()

    def _run_async(self, func, *args):
        import _thread

        _thread.start_new_thread(func, args)

    def gradient_blocking(
        self,
        start_color: tuple,
        end_color: tuple,
        total_duration: float = 1,
        steps: int = 20,
    ):
        r1, g1, b1 = start_color
        r2, g2, b2 = end_color
        for step in range(steps + 1):
            r = int(r1 + (r2 - r1) * step / steps)
            g = int(g1 + (g2 - g1) * step / steps)
            b = int(b1 + (b2 - b1) * step / steps)
            self.set_color(r, g, b)
            time.sleep(total_duration / steps)
