import os
from inky.auto import auto
from utils.image_utils import resize_image, change_orientation, apply_image_enhancement
from plugins.plugin_registry import get_plugin_instance
import importlib
from PIL import Image, ImageEnhance
from enum import Enum

class DisplayManufactureType(Enum):
    InkyImpression = 1
    Waveshare = 2

class DisplayManager:
    def __init__(self, device_config):
        """Manages the display and rendering of images."""
        self.device_config = device_config

        self.display_type = None
        self.display_module = None
        self.display_instance = None
        self.display_manufacture_type = None

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
            self.display_instance.set_border(self.display_instance.BLACK)

        # store display resolution in device config
        self.device_config.update_value("resolution", [int(self.display_instance.width), int(self.display_instance.height)], write=True)

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
        image = change_orientation(image, self.device_config.get_config("orientation"), self.device_config.get_config("inverted_image"))
        image = resize_image(image, self.device_config.get_resolution(), image_settings)
        image = apply_image_enhancement(image, self.device_config.get_config("image_settings"))

        # Display the image on the Inky display

        if self.display_manufacture_type == DisplayManufactureType.Waveshare:
            # Convert to web-safe palette with dithering
            image = image.convert('RGB').convert('P', palette=Image.ADAPTIVE, dither=Image.FLOYDSTEINBERG)

            self.display_instance.display(self.display_instance.getbuffer(image))
            self.display_instance.sleep()
        else:
            self.display_instance.set_image(image)
            self.display_instance.show()