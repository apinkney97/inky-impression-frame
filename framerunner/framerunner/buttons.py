import time
from asyncio import Queue, get_event_loop
from enum import Enum, auto
from typing import AsyncGenerator, NamedTuple

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


class ButtonPressType(Enum):
    SHORT = auto()
    LONG = auto()
    VERY_LONG = auto()


class RawButtonPress(NamedTuple):
    direction: PressDirection
    button: Button
    monotonic_time: float


class ButtonPress(NamedTuple):
    button: Button
    duration_secs: float
    end_time_monotonic: float


class ButtonManager:
    """
    Detects short vs long button presses
    """

    def __init__(
        self,
        debounce_ms: int = 50,
    ):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup([b.value for b in Button], GPIO.IN, pull_up_down=GPIO.PUD_UP)

        self._raw_event_queue: Queue[RawButtonPress] = Queue()

        self._loop = get_event_loop()

        # Assume all buttons begin unpressed
        self._button_states = {
            button: RawButtonPress(
                direction=PressDirection.BUTTON_UP,
                button=button,
                monotonic_time=time.monotonic(),
            )
            for button in Button
        }

        for button in Button:
            print(f"Adding handler for {button.value}")
            GPIO.add_event_detect(
                button.value,
                GPIO.BOTH,
                self.handle_button_press,
                bouncetime=debounce_ms,
            )

    def handle_button_press(self, pin: int):
        # read the pin to work out if it was an up or down press
        direction = PressDirection(GPIO.input(pin))
        press = RawButtonPress(direction, Button(pin), time.monotonic())
        # print(f"PUT {press}")

        # This method is called in a thread via an interrupt.
        # To make the asyncio queue work properly, we need to call its
        # methods via the main thread's event loop.
        self._loop.call_soon_threadsafe(self._raw_event_queue.put_nowait, press)

    async def get_events(self) -> AsyncGenerator[ButtonPress, None]:
        while True:

            press = await self._raw_event_queue.get()
            if press.direction is PressDirection.BUTTON_DOWN:
                # Button depressed
                self._button_states[press.button] = press
                continue

            # Button released
            old_press = self._button_states[press.button]
            press_duration = press.monotonic_time - old_press.monotonic_time

            yield ButtonPress(
                button=press.button,
                duration_secs=press_duration,
                end_time_monotonic=press.monotonic_time,
            )
