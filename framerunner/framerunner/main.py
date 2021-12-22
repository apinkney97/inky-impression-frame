"""
Images must be 600 * 448 (landscape) or 448 * 600 (portrait)

Buttons:
    - Take photo
    - Cycle next photo
    - Cycle prev photo
    - Remove current photo

In general, should cycle 1 picture per N hours (N=12?)
"""
import asyncio
import os
import time
from pathlib import Path

from inky import BLACK
from inky.inky_uc8159 import Inky
from picamera import PiCamera
from PIL import Image

from buttons import Button, ButtonPress, PressDirection, init_buttons


STORAGE_DIR = Path(os.environ["HOME"]) / "Pictures" / "frame"
RAW_DIR = STORAGE_DIR / "raw"
PROCESSED_DIR = STORAGE_DIR / "processed"
SHOW_DIR = STORAGE_DIR / "show"


class PatientInky(Inky):
    # Waits for longer than the standard Inky before exploding
    def _busy_wait(self, timeout=60.0):
        super()._busy_wait(timeout)


def init_directories():
    for path in (STORAGE_DIR, RAW_DIR, PROCESSED_DIR, SHOW_DIR):
        path.mkdir(parents=True, exist_ok=True)


def take_photo():
    print("Taking photo")
    camera = PiCamera()
    camera.resolution = (600, 448)
    camera.rotation = 90

    camera.start_preview()
    time.sleep(2)  # allegedly needed for warmup time

    now = time.time()
    filename = f"{now}.jpg"
    save_path = PROCESSED_DIR / filename
    show_path = SHOW_DIR / filename

    camera.capture(str(save_path))
    camera.close()

    show_path.symlink_to(save_path)

    show_photo(show_path)


def show_photo(path: Path, saturation=0.5):
    print(f"Drawing photo {path}")
    inky = PatientInky()
    image = Image.open(path)
    inky.set_image(image, saturation=saturation)
    inky.set_border(BLACK)
    inky.show()


async def async_main():
    init_directories()

    button_queue = asyncio.Queue()
    init_buttons(asyncio.get_event_loop(), button_queue)

    while True:
        print("Waiting for button press")
        press = await button_queue.get()
        print(f"GET {press}")
        if press.pin is Button.B and press.direction is PressDirection.BUTTON_DOWN:
            take_photo()


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
