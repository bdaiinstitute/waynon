import numpy as np
import esper

import marsoom.texture
import marsoom

from imgui_bundle import imgui

from waynon.components.simple import Component
from waynon.processors.realsense_manager import RealsenseManager

class PinholeCamera(Component):
    # intrinsics
    fl_x: float = 500.0
    fl_y: float = 500.0
    cx: float = 640.0
    cy: float = 360.0

    # resolution
    width: int = 1280
    height: int = 720

    def get_texture(self):
        return self._texture
    
    def get_image_f(self):
        """Get the image as float32 between 0 and 1"""
        return self._image_f
    
    def get_image_u(self):
        """Get the image as uint8 between 0 and 255"""
        return self._image_u
    
    def update_image(self, image: np.ndarray):
        assert image.dtype == np.uint8, f"Image must be uint8, got {image.dtype}"
        # if self._image_u == image:
        #     return
        self._image_u = image
        image_float = image / 255.0
        image_float = image_float.astype("float32")
        self._image_f = image_float
        self._texture.copy_from_host(image_float)

    def model_post_init(self, __context):
        self._texture = marsoom.texture.Texture(1280, 720, 3)
        self._image_f = None
        self._image_u = None
        return super().model_post_init(__context)
    
    def draw_property(self, nursery, e:int):
        imgui.separator_text("Pinhole Camera")
        imgui.text(f"Resolution: {self.width}x{self.height}")
        imgui.text("Intrinsics:")
        imgui.text(f"fl_x: {self.fl_x}")
        imgui.text(f"fl_y: {self.fl_y}")
        imgui.text(f"cx: {self.cx}")
        imgui.text(f"cy: {self.cy}")

    def on_selected(self, nursery, entity_id, just_selected):
        if just_selected:
            esper.dispatch_event("image_viewer", entity_id)
        
    def property_order(self):
        return 200


class DepthCamera(Component):
    width: int = 1280
    height: int = 720   

    def model_post_init(self, __context):
        self._texture = marsoom.texture.Texture(1280, 720, 3)
        self._depth_image = None
    
    def draw_property(self, nursery, entity_id):
        imgui.separator_text("Depth Camera")
        imgui.text(f"Resolution: {self.width}x{self.height}")
    
    def property_order(self):
        return 300


