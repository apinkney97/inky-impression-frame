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
import datetime
import os
import random
import subprocess
import time
from pathlib import Path
from typing import List

from inky import BLACK
from inky.inky_uc8159 import Inky
from picamera import PiCamera
from PIL import Image

from buttons import Button, ButtonManager


class PatientInky(Inky):
    # Waits for longer than the standard Inky before exploding
    def _busy_wait(self, timeout=60.0):
        super()._busy_wait(timeout)


class FrameRunner:
    def __init__(self):
        self._auto_cycle_times = [
            datetime.time(hour=3),
            datetime.time(hour=15),
        ]
        self._storage_dir = Path(os.environ["HOME"]) / "Pictures" / "frame"
        self._raw_dir = self._storage_dir / "raw"
        self._processed_dir = self._storage_dir / "processed"
        self._show_dir = self._storage_dir / "show"

        self._placeholder_image = self._processed_dir / "placeholder.jpg"

        for path in (
            self._storage_dir,
            self._raw_dir,
            self._processed_dir,
            self._show_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

        self._inky = PatientInky()
        self._inky.set_border(BLACK)

        self._last_show = datetime.datetime.now()

        self._files: List[Path] = []
        self._refresh_file_list()

        if len(self._files):
            self._current_photo = random.choice(self._files)
        else:
            self._current_photo = self._placeholder_image

        self.show_photo()

    async def auto_cycle(self):
        while True:
            now = datetime.datetime.now()
            now_time = now.time()
            # wait until next cycle time
            for cycle_time in sorted(self._auto_cycle_times):
                if now_time < cycle_time:
                    wait_until = now.replace(
                        hour=cycle_time.hour,
                        minute=cycle_time.minute,
                        second=cycle_time.second,
                    )
                    break
            else:
                cycle_time = self._auto_cycle_times[0]
                wait_until = (now + datetime.timedelta(days=1)).replace(
                    hour=cycle_time.hour,
                    minute=cycle_time.minute,
                    second=cycle_time.second,
                    microsecond=cycle_time.microsecond,
                )

            print(f"Scheduling auto-cycle for {wait_until.isoformat()}")
            await asyncio.sleep((wait_until - now).total_seconds())

            if (now - self._last_show) < datetime.timedelta(hours=1):
                print("Skipping auto-cycle due to recent change")
            else:
                print("Auto cyling")
                self.next_photo(0)

    def _refresh_file_list(self):
        self._files = sorted(self._show_dir.glob("*.jpg"))

    def take_photo(self, delay=2):
        print("Taking photo")
        camera = PiCamera()
        camera.resolution = (600, 448)
        camera.rotation = 90

        camera.start_preview()
        time.sleep(delay)  # allegedly needed for warmup time

        now = time.time()
        filename = f"{now}.jpg"
        save_path = self._processed_dir / filename
        show_path = self._show_dir / filename

        camera.capture(str(save_path))
        camera.close()

        show_path.symlink_to(save_path)
        self._current_photo = show_path
        self.show_photo()

    def show_photo(self, saturation=0.5):
        print(f"Drawing photo {self._current_photo}")
        image = Image.open(self._current_photo)
        self._inky.set_image(image, saturation=saturation)
        self._inky.show()
        self._last_show = datetime.datetime.now()
        print(f"Drawing finished")

    def next_photo(self, offset: int = 1):
        self._refresh_file_list()

        if len(self._files) < 2:
            return

        if not offset:
            # 0 means random, avoid picking the same index again
            offset = random.randint(1, len(self._files) - 1)

        index = (self._files.index(self._current_photo) + offset) % len(self._files)

        self._current_photo = self._files[index]
        self.show_photo()

    def delete_current_photo(self):
        # Go to previous photo, then delete the old one
        self._refresh_file_list()
        if len(self._files) == 0:
            return

        to_delete = self._current_photo

        if len(self._files) == 1:
            self._current_photo = self._placeholder_image
        else:
            self.next_photo(-1)
        to_delete.unlink()

    def undelete_all(self):
        for file in self._processed_dir.glob("*.jpg"):
            show_path = self._show_dir / file.name
            show_path.symlink_to(file)


async def button_loop(bm: ButtonManager, fr: FrameRunner):
    long_press_secs = 1
    long_long_press_secs = 5

    async for event in bm.get_events():
        if event.duration_secs > 60:
            print(f"Ignoring event of {event.duration_secs:.2f} seconds")
            continue

        is_short = event.duration_secs < long_press_secs
        is_long = long_press_secs <= event.duration_secs < long_long_press_secs
        is_long_long = long_long_press_secs <= event.duration_secs

        if event.button is Button.A:
            if is_short:
                fr.next_photo(-1)  # PREVIOUS PHOTO
            elif is_long:
                fr.next_photo(0)  # RANDOM PHOTO
        elif event.button is Button.B:
            if is_short or is_long:
                fr.take_photo(delay=2)  # PHOTO 2 SEC DELAY
            elif is_long_long:
                shutdown()  # SHUT DOWN
        elif event.button is Button.C:
            if is_long:
                fr.delete_current_photo()  # DELETE PHOTO
            elif is_long_long:
                fr.undelete_all()  # UNDELETE ALL
        elif event.button is Button.D:
            if is_short:
                fr.next_photo(1)  # NEXT PHOTO
            elif is_long:
                fr.next_photo(0)  # RANDOM PHOTO


async def async_main():
    bm = ButtonManager()
    fr = FrameRunner()

    await asyncio.gather(button_loop(bm, fr), fr.auto_cycle())


def main():
    asyncio.run(async_main())


def shutdown():
    print("Shutting down")
    subprocess.run("sudo shutdown --poweroff now", shell=True)


if __name__ == "__main__":
    main()
