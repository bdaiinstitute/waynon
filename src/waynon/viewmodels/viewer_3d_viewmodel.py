import numpy as np
import trio
import pyglet
import esper
from imgui_bundle import imgui


import marsoom
from marsoom import guizmo

from waynon.components.robot import Franka
from waynon.components.transform import Transform
from waynon.components.renderable import Mesh, ImageQuad, CameraWireframe, ArucoDrawable, StructuredPointCloud
from waynon.components.aruco_marker import ArucoMarker
from waynon.utils.draw_utils import draw_axis, draw_robot

class Viewer3DViewModel:
    def __init__(self, nursery: trio.Nursery, window: marsoom.Window):
        self.nursery = nursery  
        self.window = window
        self.batch = pyglet.graphics.Batch()
        self.grid = marsoom.Grid(batch=self.batch)
        self.guizmo_operation = guizmo.OPERATION.translate
        self.guizmo_frame = guizmo.MODE.local   
        self.viewer_3d = self.window.create_3D_viewer()
        self.modifiable_transform = None
        self._draw_callbacks = []

        esper.set_handler("modify_transform", self._handle_transform_selected)
        esper.set_handler("go_to_view", self._go_to_view)
        esper.set_handler("3d_draw_callback", self._add_draw_callback)

    def draw(self):
        self._handle_keys()
        self.draw_controls()
        imgui.begin("3D Viewer")
        with self.viewer_3d.draw(in_imgui_window=True) as ctx:
            self.batch.draw()
            self._draw_everything()
            for entity_id, callback in self._draw_callbacks:
                callback()
        self._draw_callbacks = []
        self._draw_guizmo()

        if imgui.is_window_focused() and not guizmo.is_using_any():
            self.viewer_3d.process_nav()
        imgui.end()
    
    def draw_controls(self):
        imgui.begin("3D Controls")
        v = self.viewer_3d
        if imgui.button("Reset View"):
            v.reset_view()
        if imgui.button("Top View"):
            v.top_view()
        if imgui.button("Left View"):
            v.left_view()
        if imgui.button("Front View"):
            v.front_view()
        
        _, v.screen_center_x = imgui.slider_float("Center X", v.screen_center_x, 0, 1)
        _, v.screen_center_y = imgui.slider_float("Center Y", v.screen_center_y, 0, 1)
        _, v.fl_x = imgui.slider_float("Focal Length X", v.fl_x, 0, 1000)
        _, v.fl_y = imgui.slider_float("Focal Length Y", v.fl_y, 0, 1000)
        
        imgui.end()

    def toggle_guizmo_frame(self):
        if self.guizmo_frame == guizmo.MODE.local:
            self.guizmo_frame = guizmo.MODE.world
        else:
            self.guizmo_frame = guizmo.MODE.local
    
    def _add_draw_callback(self, entity_id, callback):
        self._draw_callbacks.append((entity_id, callback))
    
    def _handle_transform_selected(self, entity_id):
        if not esper.entity_exists(entity_id):
            self.modifiable_transform = None
            return
        assert esper.has_component(entity_id, Transform)
        transform = esper.component_for_entity(entity_id, Transform)
        self.modifiable_transform = transform
    
    def _go_to_view(self, view):
        X_WV, fl_x, fl_y, cx, cy, width, height = view
        self.viewer_3d.go_to_view(X_WV, fl_x, fl_y, cx, cy, width, height)
    
    def _draw_guizmo(self):
        if self.modifiable_transform is not None:
            guizmo.set_id(0)
            if not self.modifiable_transform._dirty:
                X_WT = self.modifiable_transform.get_X_WT()
                X_WT = self.viewer_3d.manipulate(X_WT, self.guizmo_operation, self.guizmo_frame)
                self.modifiable_transform.set_X_WT(X_WT)

    def _draw_everything(self):
        for entity, (transform, drawable) in esper.get_components(Transform, Mesh):
            drawable.draw()
        for entity, (transform, drawable) in esper.get_components(Transform, ImageQuad):
            drawable.draw()
        for entity, (transform, drawable) in esper.get_components(Transform, ArucoDrawable):
            drawable.draw()
        for entity, (transform, drawable) in esper.get_components(Transform, CameraWireframe):
            drawable.draw()
        for entity, (transform, drawable) in esper.get_components(Transform, StructuredPointCloud):
            if drawable.show_pointcloud:
                pyglet.gl.glPointSize(3)
                drawable.draw()

    def _draw_transforms(self):
        for entity, transform in esper.get_component(Transform):
            if transform.visible:
                draw_axis(transform.get_X_WT())

    def _handle_keys(self):
        io = imgui.get_io()

        if imgui.is_key_pressed(imgui.Key._1):
            self.viewer_3d.reset_view()
        if imgui.is_key_pressed(imgui.Key._2):
            self.viewer_3d.top_view()
        if imgui.is_key_pressed(imgui.Key._3):
            self.viewer_3d.left_view()
        if imgui.is_key_pressed(imgui.Key._4):
            self.viewer_3d.front_view()

        if imgui.is_key_pressed(imgui.Key.g):
            if self.guizmo_operation == guizmo.OPERATION.translate:
                self.toggle_guizmo_frame()
            else:
                self.guizmo_operation = guizmo.OPERATION.translate

        if imgui.is_key_pressed(imgui.Key.r):
            if self.guizmo_operation == guizmo.OPERATION.rotate:
                self.toggle_guizmo_frame()
            else:
                self.guizmo_operation = guizmo.OPERATION.rotate


    # def _draw_robots(self):
    #     for entity, robot in esper.get_component(Franka):
    #         draw_robot(robot.get_manager().read_q())
