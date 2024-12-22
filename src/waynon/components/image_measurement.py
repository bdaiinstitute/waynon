from PIL import Image
import numpy as np

import esper
import trio

from imgui_bundle import imgui

from .tree_utils import *
from .component import Component
from .node import Node
from .pose_group import PoseGroup
from .camera import PinholeCamera
from .measurement import Measurement


class ImageMeasurement(Component):
    camera_id: int
    image_path: str

    def get_image_u(self):
        return np.array(Image.open(self.image_path))

    def on_selected(self, nursery, entity_id, just_selected):
        if just_selected:
            esper.dispatch_event("image_viewer", entity_id)

    def property_order(self):
        return 100
    
    def get_camera(self):
        if not esper.entity_exists(self.camera_id):
            return None
        return esper.component_for_entity(self.camera_id, PinholeCamera)
    
    def draw_property(self, nursery, entity_id):
        imgui.separator()
        camera = self.get_camera()
        if camera is not None:
            node = get_node(self.camera_id)
            imgui.text(f"Camera: {node.name}")

        imgui.text(f"Image Path: {self.image_path}")
    
    @staticmethod
    def default_name():
        return "Image"

    def _fix_on_load(self, new_to_old_entity_ids):
        self.camera_id = new_to_old_entity_ids.get(self.camera_id, self.camera_id)
