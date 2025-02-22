import os

from utils.image_utils import resize_image, change_orientation
from plugins.plugin_registry import get_plugin_instance
from PIL import Image
from enum import Enum

import importlib

# Define the six colors supported by Waveshare E Ink
WAVESHARE_PALETTE = [
    (0, 0, 0),        # Black
    (255, 255, 255),  # White
    (255, 255, 0),    # Yellow
    (255, 0, 0),      # Red
    (0, 0, 255),      # Blue
    (0, 255, 0),      # Green
]

class DisplayManufactureType(Enum):
    InkyImpression = 1
    Waveshare = 2

def quantize_image(image):
    """
    Converts an image to the 6-color palette supported by Waveshare E Ink
    using dithering.
    """
    # Convert image to RGB if not already
    image = image.convert("RGB")

    # Create a palette image with only the 6 supported colors
    palette_image = Image.new("P", (1, 1))
    palette = []
    for color in WAVESHARE_PALETTE:
        palette.extend(color)  # Flatten RGB tuples
    palette_image.putpalette(palette + [0] * (256 - len(WAVESHARE_PALETTE)) * 3)

    # Convert the image using the custom palette with dithering
    return image.quantize(palette=palette_image, dither=Image.Dither.FLOYDSTEINBERG)

class DisplayManager:
    def __init__(self, device_config):
        """Manages the display and rendering of images."""
        self.device_config = device_config

    def init_module(self):
        device_type = self.device_config.get_config("deviceType")

        if self.display_type is None or self.display_type != device_type:
            self.display_type = device_type
            self.display_module = None
            self.display_instance = None

        if self.display_module is None:
            # Dynamically import the module
            if not (bool(self.display_type and self.display_type.strip()) and importlib.util.find_spec(self.display_type) is not None):
                return False

            self.display_module = importlib.import_module(self.display_type)

        if self.display_module is None:
            return False

        self.display_manufacture_type = DisplayManufactureType.Waveshare if hasattr(self.display_module, "EPD") else DisplayManufactureType.InkyImpression

        if self.display_manufacture_type == DisplayManufactureType.Waveshare:
            if self.display_instance is None:
                self.display_instance = self.display_module.EPD()

            if hasattr(self.display_instance, "init"):
                self.display_instance.init()
            else:
                self.display_instance.Init()

        elif self.display_instance is None:
            self.display_instance = self.display_module.auto()
            self.display_instance.set_border(self.inky_display.BLACK)

        # store display resolution in device config
        self.device_config.update_value("resolution", [int(self.display_instance.width), int(self.display_instance.height)])

        return True

    def display_image(self, image, image_settings=[]):
        """Displays the image provided, applying the image_settings."""
        if not image:
            raise ValueError(f"No image provided.")

        if not self.init_module():
            return

        # Save the image
        image.save(self.device_config.current_image_file)

        # Resize and adjust orientation
        image = change_orientation(image, self.device_config.get_config("orientation"))
        image = resize_image(image, self.device_config.get_resolution(), image_settings)

        # Display the image on the Inky display
        if self.display_manufacture_type == DisplayManufactureType.Waveshare:
            # Convert the image to the supported colors using dithering
            image = quantize_image(image)
            self.display_instance.display(self.display_instance.getbuffer(image))
            self.display_instance.sleep()
        else:
            self.display_instance.set_image(image)
            self.display_instance.show()