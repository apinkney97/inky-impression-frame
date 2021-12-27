"""
Images must be 600 * 448 (landscape) or 448 * 600 (portrait)

"""
import asyncio
import datetime
import os
import random
import subprocess
import time
from pathlib import Path
from typing import Dict, List

from inky import BLACK
from inky.inky_uc8159 import Inky
from picamera import PiCamera
from PIL import Image

from buttons import Button, ButtonManager


class PatientInky(Inky):
    # Waits for longer than the standard Inky before exploding
    def _busy_wait(self, timeout=60.0):
        super()._busy_wait(timeout)


SCREEN_RESOLUTION = (600, 448)


class FrameRunner:
    def __init__(self):
        self._auto_cycle_times = [
            datetime.time(hour=3),
            datetime.time(hour=15),
        ]
        self._storage_dir = Path(os.environ["HOME"]) / "Pictures" / "frame"
        self._camera_save_dir = self._storage_dir / "camera_images"
        self._show_dir = self._storage_dir / "show"

        self._placeholder_image = self._storage_dir / "placeholder.jpg"

        for path in (
            self._storage_dir,
            self._camera_save_dir,
            self._show_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

        self._inky = PatientInky()
        self._inky.set_border(BLACK)

        self._last_show = datetime.datetime.now()

        self._known_images: Dict[Path, bool] = {}

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
        # sort by modification time
        files = sorted(self._show_dir.glob("*.*"), key=lambda p: p.stat().st_mtime)

        usable_files = []

        for path in files:
            if path in self._known_images:
                is_ok = self._known_images[path]
                if is_ok:
                    usable_files.append(path)
                continue

            # try to open the image, skip on error
            try:
                image = Image.open(path)
            except Exception as e:
                print(f"Can't open {path} as an image, ignoring it")
                print(f"Error was {type(e).__name__}: {e}")
                self._known_images[path] = False
                continue

            try:
                if image.size != SCREEN_RESOLUTION:
                    print(f"Need to resize {path} - currently {image.size}")
                    new_image = self._resize_image(image)
                    # overwrite the old path
                    new_image.save(path)
            except Exception as e:
                print("Something went wrong")
                print(f"Error was {type(e).__name__}: {e}")
                self._known_images[path] = False
                continue

            self._known_images[path] = True
            usable_files.append(path)

        self._files = usable_files

    @staticmethod
    def _resize_image(image):

        image_w, image_h = image.size

        if image_w < image_h:
            image = image.rotate(270, expand=True)
            print(f"Rotating, dimensions now {image.size}")

        image_w, image_h = image.size

        screen_w, screen_h = SCREEN_RESOLUTION

        scale = min([screen_w / image_w, screen_h / image_h])
        new_w = int(image_w * scale)
        new_h = int(image_h * scale)

        image = image.resize((new_w, new_h))

        dx = (screen_w - new_w) // 2
        dy = (screen_h - new_h) // 2

        print(f"Scaling image to {new_w}, {new_h} with border {dx}, {dy}")

        new_image = Image.new("RGB", SCREEN_RESOLUTION)
        new_image.paste(image, (dx, dy))

        return new_image

    def take_photo(self, delay=2):
        print("Taking photo")
        camera = PiCamera()
        camera.resolution = SCREEN_RESOLUTION
        camera.rotation = 90

        camera.start_preview()
        time.sleep(delay)  # allegedly needed for warmup time

        now = time.time()
        filename = f"{now}.jpg"
        save_path = self._camera_save_dir / filename
        show_path = self._show_dir / filename

        camera.capture(str(save_path))
        camera.close()

        show_path.symlink_to(save_path)
        self._current_photo = show_path
        self.show_photo()

    def show_photo(self, saturation=0.75):
        print(f"Drawing photo {self._current_photo}")
        start = time.monotonic()
        image = Image.open(self._current_photo)
        self._inky.set_image(image, saturation=saturation)
        self._inky.show()
        self._last_show = datetime.datetime.now()
        print(f"Drawing finished, took {time.monotonic() - start:.2f} seconds")

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
        for file in self._camera_save_dir.glob("*.jpg"):
            show_path = self._show_dir / file.name
            show_path.symlink_to(file)


async def button_loop(bm: ButtonManager, fr: FrameRunner):
    long_press_secs = 1
    long_long_press_secs = 5

    async for event in bm.get_events():
        if event.duration_secs > 60:
            print(f"Ignoring long button press ({int(event.duration_secs)} seconds)")
            continue

        event_age = time.monotonic() - event.end_time_monotonic
        if event_age > 5:
            print(f"Ignoring stale button press ({int(event_age)} seconds)")
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
