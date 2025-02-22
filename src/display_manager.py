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

class DisplayType(Enum):
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

        # Dynamically import the module
        if importlib.is_module_available(self.device_config.get_config("deviceType")):
            self.display_module =   importlib.import_module(self.device_config.get_config("deviceType"))
            # Initialize the module
            self.init_module()

            # store display resolution in device config
            device_config.update_value("resolution", [int(self.the_display.width), int(self.the_display.height)])

    def init_module(self):
        if self.display_module is None:
            return

        self.display_type = DisplayType.Waveshare if hasattr(self.display_module, "EPD") else DisplayType.InkyImpression

        if self.display_type == DisplayType.Waveshare:
            if self.the_display is None:
                self.the_display = self.display_module.EPD()

            if hasattr(self.the_display, "init"):
                self.the_display.init()
            else:
                self.the_display.Init()

        elif self.the_display is None:
            self.the_display = self.display_module.auto()
            self.the_display.set_border(self.inky_display.BLACK)

    def display_image(self, image, image_settings=[]):
        
        if self.display_module is None:
            return

        """Displays the image provided, applying the image_settings."""
        if not image:
            raise ValueError(f"No image provided.")

        self.init_module()

        # Save the image
        image.save(self.device_config.current_image_file)

        # Resize and adjust orientation
        image = change_orientation(image, self.device_config.get_config("orientation"))
        image = resize_image(image, self.device_config.get_resolution(), image_settings)

        # Display the image on the Inky display
        if self.display_type == DisplayType.Waveshare:
            # Convert the image to the supported colors using dithering
            image = quantize_image(image)
            self.the_display.display(self.the_display.getbuffer(image))
            self.the_display.sleep()
        else:
            self.the_display.set_image(image)
            self.the_display.show()