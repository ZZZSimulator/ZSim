import os
import cv2
import mss
import numpy as np


CHARACTER_IMAGE_PATH = "./zsim/data/character_img"


with mss.mss() as sct:
    # Take a screenshot during fullscreen gaming on a *4K* monitor
    # left, top = 1875, 375
    # right, bottom = 1929, 429

    # Take a screenshot during fullscreen gaming on a *2K* monitor
    # left, top = 1250, 249
    # right, bottom = 1286, 285
    
    # Take a screenshot during fullscreen gaming on a *1K* monitor
    left, top = 937, 187
    right, bottom = 965, 215
    
    width = right - left + 1
    height = bottom - top + 1

    monitor = {"left": left, "top": top, "width": width, "height": height}
    img = np.array(sct.grab(monitor))[:, :, :3]

    ch_id = "1041"
    cv2.imwrite(os.path.join(CHARACTER_IMAGE_PATH, "1k", ch_id + ".png"), img)
