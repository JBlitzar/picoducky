# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "pillow",
# ]
# ///

from PIL import Image
from PIL.ImageGrab import grab, grabclipboard


grab().save("screenshot.png")

grabclipboard().save("clipboard_image.png")
