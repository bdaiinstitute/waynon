from PIL import Image
import numpy as np

import esper
import trio

from imgui_bundle import imgui

import pyglet

from .tree_utils import *
from .component import Component
from .node import Node
from .pose_group import PoseGroup
from .camera import Camera
from .raw_measurement import RawMeasurement


class Mesh(Component):

    mesh_path: str

    def model_post_init(self, __context):
        self._batch = pyglet.graphics.Batch()
        self._model = pyglet.resource.model(self.mesh_path, batch=self._batch)

