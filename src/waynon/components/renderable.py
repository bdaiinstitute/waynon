from PIL import Image
import marsoom.image_quad
import numpy as np

import esper
import trio

from imgui_bundle import imgui

import pyglet

import marsoom

from .tree_utils import *
from .component import Component
from .node import Node
from .pose_group import PoseGroup
from .camera import Camera
from .measurement import Measurement


class Drawable:
    def draw(self):
        raise NotImplementedError("draw method not implemented")

    def set_X_WT(self, X_WT: np.ndarray):
        raise NotImplementedError("set_X_WT method not implemented")

class Mesh(Component, Drawable):

    mesh_path: str

    def model_post_init(self, __context):
        self._batch = pyglet.graphics.Batch()
        self._model = pyglet.resource.model(self.mesh_path, batch=self._batch)
    
    def set_X_WT(self, X_WT: np.ndarray):
        self._model.matrix = pyglet.math.Mat4(X_WT.T.flatten().tolist())
    
    def draw(self):
        self._batch.draw()

class ImageQuad(Component, Drawable):
    texture_id: int = 0
    top_left: tuple[float, float, float]
    top_right: tuple[float, float, float]
    bot_right: tuple[float, float, float]
    bot_left: tuple[float, float, float]

    @staticmethod
    def create_aruco_quad(marker_size: float) -> 'ImageQuad':
        marker_points = get_single_marker_points(marker_size)
        top_left = tuple(marker_points[0].tolist())
        top_right = tuple(marker_points[1].tolist())
        bot_right = tuple(marker_points[2].tolist())    
        bot_left = tuple(marker_points[3].tolist())
        return ImageQuad(top_left=top_left, top_right=top_right, bot_right=bot_right, bot_left=bot_left)
    
    def model_post_init(self, __context):
        self._batch = pyglet.graphics.Batch()
        self._model = marsoom.image_quad.ImageQuad(
            self.texture_id, 
            self.top_left, 
            self.top_right, 
            self.bot_right, 
            self.bot_left,
            batch=self._batch
            )
    
    def set_texture(self, texture_id):
        self._model.tex_id = texture_id
    
    def set_X_WT(self, X_WT: np.ndarray):
        self._model.matrix = pyglet.math.Mat4(X_WT.T.flatten().tolist())
    
    def draw(self):
        self._model.draw()


def get_single_marker_points(marker_size: float) -> np.ndarray:
    marker_points = np.array([[-marker_size / 2, marker_size / 2, 0],
                              [marker_size / 2, marker_size / 2, 0],
                              [marker_size / 2, -marker_size / 2, 0],
                              [-marker_size / 2, -marker_size / 2, 0]], dtype=np.float64)
    return marker_points
