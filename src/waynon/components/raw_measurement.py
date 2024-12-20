from PIL import Image
import esper
import trio

from imgui_bundle import imgui

from .tree_utils import *
from .component import Component
from .node import Node
from .pose_group import PoseGroup
from .camera import Camera

class RawMeasurement(Component):
    joint_values: list[float]
    camera_serial: str
    image_path: str
    enabled: bool = True


    def on_selected(self, nursery, entity_id):
        esper.dispatch_event("image_viewer", entity_id)

    def property_order(self):
        return 100

    def draw_property(self, nursery, entity_id):
        imgui.separator()
        imgui.text(f"Joint Values: {self.joint_values}")
        imgui.text(f"Camera Serial: {self.camera_serial}")
        imgui.text(f"Image Path: {self.image_path}")
        _, self.enabled = imgui.checkbox("Enabled", self.enabled)
