"""
Contains all code related to turning a screenshot into a string
"""

from typing import Any
import cv2
import numpy as np
import mss
from PIL import Image
import pytesseract
import settings

pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_PATH

ALPHABET_WHITELIST = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
ROUND_WHITELIST = "0123456789-"

# macOS Retina displays return 2x pixels from mss.
# We detect the scale factor once at import time.
_sct = mss.mss()
_primary = _sct.monitors[1]  # primary monitor
_RETINA_SCALE = 1
try:
    from Quartz import CGDisplayScreenSize, CGMainDisplayID, CGDisplayPixelsWide
    _native_px = CGDisplayPixelsWide(CGMainDisplayID())
    if _native_px > _primary["width"]:
        _RETINA_SCALE = _native_px / _primary["width"]
except Exception:
    pass


def _grab(bbox: tuple) -> Image.Image:
    """Cross-platform screen grab that handles Retina scaling.
    bbox is (left, top, right, bottom) in logical (non-retina) coordinates."""
    monitor = {
        "left": bbox[0],
        "top": bbox[1],
        "width": bbox[2] - bbox[0],
        "height": bbox[3] - bbox[1],
    }
    screenshot = _sct.grab(monitor)
    img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
    # If Retina, the captured image is 2x the logical size — resize down
    if _RETINA_SCALE > 1:
        img = img.resize((monitor["width"], monitor["height"]), Image.LANCZOS)
    return img


def image_grayscale(image) -> Any:
    """Converts an image to grayscale so OCR has an easier time deciphering characters"""
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def image_thresholding(image) -> Any:
    """Applies thresholding to the image"""
    return cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]


def image_array(image) -> Any:
    """Turns the image into an array"""
    image = np.array(image)
    image = image[..., :3]
    return image


def image_resize(image, scale: int) -> Any:
    """Resizes the image using the scale passed in argument two"""
    (width, height) = (image.width * scale, image.height * scale)
    return image.resize((width, height))


def get_text(screenxy: tuple, scale: int, psm: int, whitelist: str = "") -> str:
    """Returns text from screen coordinates"""
    screenshot = _grab(screenxy)
    resize = image_resize(screenshot, scale)
    array = image_array(resize)
    grayscale = image_grayscale(array)
    thresholding = image_thresholding(grayscale)
    return pytesseract.image_to_string(
        thresholding, config=f'--psm {psm} -c tessedit_char_whitelist={whitelist}'
    ).strip()


def get_text_from_image(image, whitelist: str = "") -> str:
    """Takes an image and returns the text"""
    resize = image_resize(image, 3)
    array = image_array(resize)
    grayscale = image_grayscale(array)
    thresholding = image_thresholding(grayscale)
    return pytesseract.image_to_string(
        thresholding, config=f'--psm 7 -c tessedit_char_whitelist={whitelist}'
    ).strip()
