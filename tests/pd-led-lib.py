import time
import pwmio
import board

import _thread
from enum import Enum


class LEDPattern(Enum):
    SOLID = "solid"
    FLASH = "flash"
    PULSE = "pulse"
    CYCLE = "cycle"


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
        self._current_pattern_id = None

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

    def _sleep_with_interrupt(
        self, seconds: float, pattern_id: float | None, chunk: float = 0.01
    ):
        if seconds is None or seconds <= 0:
            return
        remaining = seconds
        while remaining > 0:
            if pattern_id is not None and self._current_pattern_id != pattern_id:
                break
            sl = chunk if remaining > chunk else remaining
            time.sleep(sl)
            remaining -= sl

    def gradient_blocking(
        self,
        start_color: tuple,
        end_color: tuple,
        total_duration: float = 1,
        steps: int = 20,
        pattern_id: float | None = None,
    ):
        r1, g1, b1 = start_color
        r2, g2, b2 = end_color
        for step in range(steps + 1):
            if pattern_id is not None and self._current_pattern_id != pattern_id:
                break
            r = int(r1 + (r2 - r1) * step / steps)
            g = int(g1 + (g2 - g1) * step / steps)
            b = int(b1 + (b2 - b1) * step / steps)
            self.set_color(r, g, b)
            self._sleep_with_interrupt(total_duration / steps, pattern_id)

    def interrupt(self):
        self._current_pattern_id = None
        self.turn_off()

    def start_pattern_async(
        self, pattern: LEDPattern, color: tuple, duration: float = None, **kwargs
    ):
        # Interrupt any existing pattern before starting a new one
        self.interrupt()
        self._current_pattern_id = time.time()
        pattern_id = self._current_pattern_id

        if pattern == LEDPattern.SOLID:
            _thread.start_new_thread(self._solid_pattern, (pattern_id, color, duration))
        elif pattern == LEDPattern.FLASH:
            flash_rate = kwargs.get("flash_rate", 0.5)
            _thread.start_new_thread(
                self._flash_pattern, (pattern_id, color, duration, flash_rate)
            )
        elif pattern == LEDPattern.PULSE:
            pulse_speed = kwargs.get("pulse_speed", 1.0)
            _thread.start_new_thread(
                self._pulse_pattern, (pattern_id, color, duration, pulse_speed)
            )
        elif pattern == LEDPattern.CYCLE:
            colors = kwargs.get("colors", [self.RED, self.GREEN, self.BLUE])
            cycle_speed = kwargs.get("cycle_speed", 1.0)
            _thread.start_new_thread(
                self._cycle_pattern, (pattern_id, colors, duration, cycle_speed)
            )

    def _solid_pattern(self, pattern_id, color, duration):
        if self._current_pattern_id != pattern_id:
            return
        self.set_color_tuple(color)
        if duration:
            self._sleep_with_interrupt(duration, pattern_id)
            if self._current_pattern_id == pattern_id:
                self._current_pattern_id = None
                self.turn_off()

    def _flash_pattern(self, pattern_id, color, duration, flash_rate):
        start_time = time.time()
        while self._current_pattern_id == pattern_id:
            if duration and time.time() - start_time >= duration:
                break
            self.set_color_tuple(color)
            self._sleep_with_interrupt(flash_rate / 2, pattern_id)
            if self._current_pattern_id != pattern_id:
                break
            self.turn_off()
            self._sleep_with_interrupt(flash_rate / 2, pattern_id)
        if self._current_pattern_id == pattern_id:
            self._current_pattern_id = None

    def _pulse_pattern(self, pattern_id, color, duration, pulse_speed):
        start_time = time.time()
        steps = 20
        while self._current_pattern_id == pattern_id:
            if duration and time.time() - start_time >= duration:
                break
            self.gradient_blocking((0, 0, 0), color, pulse_speed / 2, steps, pattern_id)
            if self._current_pattern_id != pattern_id:
                break
            self.gradient_blocking(color, (0, 0, 0), pulse_speed / 2, steps, pattern_id)
        if self._current_pattern_id == pattern_id:
            self._current_pattern_id = None

    def _cycle_pattern(self, pattern_id, colors, duration, cycle_speed):
        start_time = time.time()
        color_index = 0
        while self._current_pattern_id == pattern_id:
            if duration and time.time() - start_time >= duration:
                break
            self.set_color_tuple(colors[color_index])
            self._sleep_with_interrupt(cycle_speed, pattern_id)
            color_index = (color_index + 1) % len(colors)
        if self._current_pattern_id == pattern_id:
            self._current_pattern_id = None


if __name__ == "__main__":
    led = PDLED()
    led.start_pattern_async(LEDPattern.CYCLE, None, duration=3, cycle_speed=0.5)
    time.sleep(5)
    led.start_pattern_async(LEDPattern.PULSE, PDLED.BLUE, duration=3, pulse_speed=1.0)
    time.sleep(5)
    led.start_pattern_async(LEDPattern.FLASH, PDLED.RED, duration=5, flash_rate=0.2)
    time.sleep(2)
    led.start_pattern_async(LEDPattern.SOLID, PDLED.GREEN, duration=2)
    time.sleep(2)
    led.interrupt()
    led.turn_off()
