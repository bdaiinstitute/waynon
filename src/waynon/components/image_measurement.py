import esper
import numpy as np
import trio
from imgui_bundle import imgui
from PIL import Image

from .camera import PinholeCamera
from .component import Component
from .measurement import Measurement
from .node import Node
from .pose_group import PoseGroup
from .tree_utils import *


class ImageMeasurement(Component):
    camera_id: int
    image_path: str

    def get_image_u(self):
        from .scene_utils import DATA_PATH
        image_path = DATA_PATH / self.image_path
        return np.array(Image.open(image_path))

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
