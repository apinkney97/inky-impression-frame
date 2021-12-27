# inky-impression-frame
Project to mount a
[Pimoroni Inky Impression](https://shop.pimoroni.com/products/inky-impression-5-7)
display inside a photo frame.

## User Manual

### Important note about unplugging the power
You should not disconnect the power without safely shutting down the photo frame. To do this, you must hold the "photo" button (B, see below) for more than 5 seconds and then release it. The green LED will flash for a few seconds and then turn off. At this point it is safe to remove the power.

If you do not follow this process, the SD card in the Raspberry Pi can become corrupted and the frame may stop working.

### Button Presses
With the frame facing you in portrait orientation with the buttons at the bottom, from left to right
the buttons are labelled A, B, C, D.

#### Short press - hold for less than 1 second:
- A: Previous image
- B: Take a new photo
- C: [No action]
- D: Next image

#### Long press - hold for more than 1 second, but less than 5 seconds:
- A: Random photo
- B: Take a new photo
- C: Delete the currently displayed image
- D: Random photo

#### Very long press - more thab 5 seconds:
- A: [No action]
- B: Shut down safely (it's safe to remove power once the green LED turns off)
- C: Undelete all deleted camera photos
- D: [No action]


### Image Deletion
Images taken with the camera on the frame are never truly deleted. These can be undeleted by holding button "C" (the "delete" button) for more than 5 seconds.

Deleting an image that has been copied onto the frame manually is permanent.