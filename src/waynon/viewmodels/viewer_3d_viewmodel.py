import trio
import pyglet
import esper
from imgui_bundle import imgui


import marsoom
from marsoom import guizmo

from waynon.components.robot import Franka
from waynon.components.transform import Transform
from waynon.components.renderable import Mesh
from waynon.utils.draw_utils import draw_axis, draw_robot

class Viewer3DViewModel:
    def __init__(self, nursery: trio.Nursery, window: marsoom.Window):
        self.nursery = nursery  
        self.window = window
        self.batch = pyglet.graphics.Batch()
        self.guizmo_operation = guizmo.OPERATION.translate
        self.guizmo_frame = guizmo.MODE.local   
        self.viewer_3d = self.window.create_3D_viewer()
        self.modifiable_transform = None

        esper.set_handler("modify_transform", self._handle_transform_selected)

    
    def draw(self):
        self._handle_keys()
        imgui.begin("3D Viewer")
        with self.viewer_3d.draw(in_imgui_window=True) as ctx:
            self._draw_transforms()
            self._draw_meshes()
        self._draw_guizmo()

        if imgui.is_window_focused() and not guizmo.is_using_any():
            self.viewer_3d.process_nav()
        imgui.end()

    # def _draw_modifiable_transforms(self):
    #     for entity, transform in esper.get_component(Transform):
    #         if entity == self.scene_view_model.selected_entity_id and transform.modifiable:
    #             guizmo.set_id(entity)
    #             X_WT = transform.get_X_WT()
    #             X_WT = self.viewer_3d.manipulate(X_WT, self.guizmo_operation, self.guizmo_frame)
    #             transform.set_X_WT(X_WT)
    def toggle_guizmo_frame(self):
        if self.guizmo_frame == guizmo.MODE.local:
            self.guizmo_frame = guizmo.MODE.world
        else:
            self.guizmo_frame = guizmo.MODE.local
    
    def _handle_transform_selected(self, entity_id):
        if not esper.entity_exists(entity_id):
            self.modifiable_transform = None
            return
        assert esper.has_component(entity_id, Transform)
        transform = esper.component_for_entity(entity_id, Transform)
        self.modifiable_transform = transform
    
    def _draw_guizmo(self):
        if self.modifiable_transform is not None:
            guizmo.set_id(0)
            X_WT = self.modifiable_transform.get_X_WT()
            X_WT = self.viewer_3d.manipulate(X_WT, self.guizmo_operation, self.guizmo_frame)
            self.modifiable_transform.set_X_WT(X_WT)

    def _draw_meshes(self):
        for entity, (transform, mesh) in esper.get_components(Transform, Mesh):
            mesh._batch.draw()


    def _draw_transforms(self):
        for entity, transform in esper.get_component(Transform):
            if transform.visible:
                draw_axis(transform.get_X_WT())

    def _handle_keys(self):
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


    def _draw_robots(self):
        for entity, robot in esper.get_component(Franka):
            draw_robot(robot.get_manager().q)
