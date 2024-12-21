from PIL import Image
import numpy as np

import esper
import trio

from imgui_bundle import imgui

from .tree_utils import *
from .component import Component
from .node import Node
from .pose_group import PoseGroup
from .camera import Camera
from .measurement import Measurement


class JointMeasurement(Component):
    robot_id: int
    joint_values: list[float]

    def property_order(self):
        return 100

    def draw_property(self, nursery, entity_id):
        imgui.separator()
        for i, j in enumerate(self.joint_values):
            imgui.text(f"Joint {i}: {j}")
    
    def default_name(self):
        return "Joints"
    
    def _fix_on_load(self, new_to_old_entity_ids):
        self.robot_id = new_to_old_entity_ids[self.robot_id]

