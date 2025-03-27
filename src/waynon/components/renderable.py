# Copyright (c) 2025 Boston Dynamics AI Institute LLC. All rights reserved.

from PIL import Image
import marsoom.camera_wireframe
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
from .camera import PinholeCamera
from .measurement import Measurement
from .transform import Transform

from waynon.utils.aruco_textures import ARUCO_TEXTURES
from waynon.utils.utils import COLORS


class Drawable:
    def draw(self):
        raise NotImplementedError("draw method not implemented")

    def set_X_WT(self, X_WT: np.ndarray):
        raise NotImplementedError("set_X_WT method not implemented")

class Mesh(Component, Drawable):

    mesh_path: str
    color: tuple[float, float, float, float] = (0.0, 1.0, 0.0, 1.0)
    visible: bool = True

    def model_post_init(self, __context):
        self._batch = pyglet.graphics.Batch()
        self._model = pyglet.resource.model(self.mesh_path, batch=self._batch)
        try:
            self._model.groups[0].color = self.color
        except:
            pass
    
    def set_X_WT(self, X_WT: np.ndarray):
        self._model.matrix = pyglet.math.Mat4(X_WT.T.flatten().tolist())
    
    def set_color(self, color: tuple[float, float, float, float]):
        if self.color == color:
            return
        self.color = color
        try:
            self._model.groups[0].color = color
        except:
            print(f"Wanted to set color {color} but group does not support it")
    
    def draw(self):
        if self.visible:
            self._batch.draw()
        
    def draw_property(self, nursery, entity_id):
        imgui.push_id(entity_id)
        imgui.separator_text("Mesh")
        _, self.visible = imgui.checkbox("Visible", self.visible)
        imgui.pop_id()
    
    def property_order(self):
        return 500
        

class ImageQuad(Component, Drawable):
    texture_id: int = 0
    top_left: tuple[float, float, float]
    top_right: tuple[float, float, float]
    bot_right: tuple[float, float, float]
    bot_left: tuple[float, float, float]

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
        self._batch.draw()

class ArucoDrawable(Component, Drawable):
    marker_size: float = 0.01
    marker_id: int = 1
    marker_dict: int = 0

    def model_post_init(self, __context):
        marker_points = get_single_marker_points(self.marker_size)
        top_left = tuple(marker_points[0].tolist())
        top_right = tuple(marker_points[1].tolist())
        bot_right = tuple(marker_points[2].tolist())    
        bot_left = tuple(marker_points[3].tolist())
        self._batch = pyglet.graphics.Batch()
        self._texture_id = ARUCO_TEXTURES.get_texture(self.marker_id, self.marker_dict).id
        self._model = marsoom.image_quad.ImageQuad(
            self._texture_id,
            top_left, 
            top_right, 
            bot_right, 
            bot_left,
            batch=self._batch
            )
    
    def set_marker_size(self, marker_size: float):
        if self.marker_size == marker_size:
            return
        self.marker_size = marker_size
        marker_points = get_single_marker_points(self.marker_size)
        top_left = tuple(marker_points[0].tolist())
        top_right = tuple(marker_points[1].tolist())
        bot_right = tuple(marker_points[2].tolist())    
        bot_left = tuple(marker_points[3].tolist())
        self._model.update(
            top_left=top_left,
            top_right=top_right,
            bot_right=bot_right,
            bot_left=bot_left
        )
    
    def set_marker_id(self, marker_id: int):
        if self.marker_id == marker_id:
            return
        self.marker_id = marker_id
        self._texture_id = ARUCO_TEXTURES.get_texture(marker_id, self.marker_dict).id
        self._model.tex_id = self._texture_id
    
    def set_marker_dict(self, marker_dict: int):
        if self.marker_dict == marker_dict:
            return
        self.marker_dict = marker_dict
        self._texture_id = ARUCO_TEXTURES.get_texture(self.marker_id, marker_dict).id
        self._model.tex_id = self._texture_id

    def set_X_WT(self, X_WT: np.ndarray):
        self._model.matrix = pyglet.math.Mat4(X_WT.T.flatten().tolist())
    
    def draw(self):
        self._batch.draw()


def get_single_marker_points(marker_size: float) -> np.ndarray:
    marker_points = np.array([[-marker_size / 2, marker_size / 2, 0],
                              [marker_size / 2, marker_size / 2, 0],
                              [marker_size / 2, -marker_size / 2, 0],
                              [-marker_size / 2, -marker_size / 2, 0]], dtype=np.float64)
    return marker_points


class CameraWireframe(Component, Drawable):
    fl_x: float = 1.0
    fl_y: float = 1.0
    cx: float = 0.0 
    cy: float = 0.0
    width: int = 1280
    height: int = 720
    z_offset: float = 0.1
    alpha: float = 1.0

    def draw_property(self, nursery, entity_id):
        # imgui.push_style_color(imgui.Col_.button, COLORS["BLUE"])
        imgui.separator_text("Camera Wireframe")
        imgui.spacing()
        if imgui.button("Go To View", (imgui.get_content_region_avail().x, 40)):
            transform = esper.component_for_entity(entity_id, Transform)
            X_WV = transform.get_X_WT()
            esper.dispatch_event("go_to_view", (X_WV, self.fl_x, self.fl_y, self.cx, self.cy, self.width, self.height))
        # imgui.pop_style_color()
        imgui.spacing()

        res, new_fl_x = imgui.slider_float("Focal Length X", self.fl_x, 0.0, 1000.0)
        if res:
            self.update_intrinsics(new_fl_x, self.fl_y, self.cx, self.cy, self.width, self.height)
        res, new_fl_y = imgui.slider_float("Focal Length Y", self.fl_y, 0.0, 1000.0)
        if res:
            self.update_intrinsics(self.fl_x, new_fl_y, self.cx, self.cy, self.width, self.height)
        res, new_cx = imgui.slider_float("Principal X", self.cx, 0.0, 1000.0)
        if res:
            self.update_intrinsics(self.fl_x, self.fl_y, new_cx, self.cy, self.width, self.height)
        res, new_cy = imgui.slider_float("Principal Y", self.cy, 0.0, 1000.0)
        if res:
            self.update_intrinsics(self.fl_x, self.fl_y, self.cx, new_cy, self.width, self.height)
        

        res, new_offset = imgui.slider_float("Z Offset", self.z_offset, 0.0, 1.0)
        if res:
            self.set_z_offset(new_offset)
        res, new_alpha = imgui.slider_float("Alpha", self.alpha, 0.0, 1.0)
        if res:
            self.set_alpha(new_alpha)
        
    
    def property_order(self):
        return 500

    def model_post_init(self, __context):
        self._batch = pyglet.graphics.Batch()
        self._model = marsoom.camera_wireframe.CameraWireframeWithImage(
            batch=self._batch, 
            z_offset=self.z_offset, 
            alpha=self.alpha, 
            width=self.width, 
            height=self.height,
            K=np.array([[self.fl_x, 0, self.cx],    
                        [0, self.fl_y, self.cy],
                        [0, 0, 1]], dtype=np.float32)
            )
        self.update_intrinsics(self.fl_x, self.fl_y, self.cx, self.cy, self.width, self.height, force=True)
    
    def set_z_offset(self, z_offset: float):
        if self.z_offset == z_offset:
            return
        self.z_offset = z_offset
        self._model.update_z_offset(z_offset)
    
    def set_alpha(self, alpha: float):
        if self.alpha == alpha:
            return
        self.alpha = alpha
        self._model.set_alpha(alpha)
    
    def set_texture_id(self, texture_id):
        self._model.set_texture_id(texture_id)

    def update_intrinsics(self, fl_x: float, fl_y: float, cx: float, cy: float, width: int, height: int, force:bool = False):
        if not force:
            if self.fl_x == fl_x and self.fl_y == fl_y and self.cx == cx and self.cy == cy and self.width == width and self.height == height:
                return

        self.fl_x = fl_x
        self.fl_y = fl_y
        self.cx = cx
        self.cy = cy
        self.width = width
        self.height = height

        K = np.array([[fl_x, 0, cx],
                      [0, fl_y, cy],
                      [0, 0, 1]], dtype=np.float32)
        self._model.update_K(K, width, height)
    
    def set_X_WT(self, X_WT: np.ndarray):
        self._model.matrix = pyglet.math.Mat4(X_WT.T.flatten().tolist())
    
    def draw(self):
        self._batch.draw()


class StructuredPointCloud(Component, Drawable):
    show_pointcloud: bool = False
    fl_x: float = 1.0
    fl_y: float = 1.0
    cx: float = 0.0
    cy: float = 0.0
    width: int = 1280
    height: int = 720

    def draw_property(self, nursery, entity_id):
        # imgui.push_style_color(imgui.Col_.button, COLORS["BLUE"])
        imgui.separator_text("Pointcloud")
        imgui.spacing()
        _, self.show_pointcloud = imgui.checkbox("Show", self.show_pointcloud)
        
    def property_order(self):
        return 500

    def model_post_init(self, __context):
        self._model = marsoom.StructuredPointCloud(
            1280, 720)
        self._identifier = -1   
    
    def set_texture_id(self, texture_id):
        if self._model.color_texture_id is None or self._model.color_texture_id != texture_id:
            self._model.color_texture_id = texture_id
    
    def update_depth(self, depth: np.ndarray, depth_scale: float, identifier: int = None):
        if identifier is not None:
            if self._identifier == identifier:
                return
            self._identifier = identifier
        self._model.depth_scale = depth_scale
        self._model.update_depth(depth)

    def update_intrinsics(self, fl_x: float, fl_y: float, cx: float, cy: float, width: int, height: int, force:bool = False):
        if not force:
            if self.fl_x == fl_x and self.fl_y == fl_y and self.cx == cx and self.cy == cy and self.width == width and self.height == height:
                return

        self.fl_x = fl_x
        self.fl_y = fl_y
        self.cx = cx
        self.cy = cy
        self.width = width
        self.height = height

        self._model.update_intrinsics(fl_x, fl_y, cx, cy)
    
    def set_X_WT(self, X_WT: np.ndarray):
        self._model.matrix = pyglet.math.Mat4(X_WT.T.flatten().tolist())
    
    def draw(self):
        self._model.draw()
