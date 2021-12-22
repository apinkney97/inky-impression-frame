import asyncio
import time
from enum import Enum
from typing import NamedTuple

from RPi import GPIO


# Maps button name to BCM pin number
class Button(Enum):
    A = 5
    B = 6
    C = 16
    D = 24


class PressDirection(Enum):
    BUTTON_DOWN = GPIO.LOW
    BUTTON_UP = GPIO.HIGH


class ButtonPress(NamedTuple):
    direction: PressDirection
    pin: int
    monotonic_time: int


def init_buttons(loop, queue: asyncio.Queue, bounce_time=50):
    GPIO.setmode(GPIO.BCM)
    GPIO.setup([b.value for b in Button], GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def handle_button_press(pin: int):
        # read the pin to work out if it was an up or down press
        direction = PressDirection(GPIO.input(pin))
        press = ButtonPress(direction, Button(pin), time.monotonic())
        # print(f"PUT {press}")
        loop.call_soon_threadsafe(queue.put_nowait, press)

    for button in Button:
        print(f"Adding handler for {button.value}")
        GPIO.add_event_detect(
            button.value,
            GPIO.BOTH,
            handle_button_press,
            bouncetime=bounce_time,
        )
