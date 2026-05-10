# ------------------------------------------------------Imports---------------------------------------------------------
from PIL import Image, ImageTk
# ------------------------------------------------- Image Resizer ------------------------------------------------------
class ImageResizer:
    def __init__(self, image_location, image_wd, flipper=False):
        self.imager = Image.open(image_location)
        if flipper:
            self.imager = self.imager.transpose(Image.FLIP_LEFT_RIGHT)
        aspect_ratio = self.imager.height / self.imager.width
        width = image_wd
        self.imager = self.imager.resize((width, int(width * aspect_ratio)))
        self.image = ImageTk.PhotoImage(self.imager)