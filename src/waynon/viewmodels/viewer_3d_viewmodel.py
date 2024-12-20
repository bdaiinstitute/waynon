import trio
import pyglet
import esper
from imgui_bundle import imgui


import marsoom
from marsoom import guizmo

from waynon.components.robot import RobotSettings
from waynon.components.transform import Transform
from waynon.utils.draw_utils import draw_axis, draw_robot

class Viewer3DViewModel:
    def __init__(self, nursery: trio.Nursery, window: marsoom.Window):
        self.nursery = nursery  
        self.window = window
        self.batch = pyglet.graphics.Batch()
        self.guizmo_operation = guizmo.OPERATION.translate
        self.guizmo_frame = guizmo.MODE.local   
        self.viewer_3d = self.window.create_3D_viewer()
    
    def draw(self):
        self.handle_keys()
        imgui.begin("3D Viewer")
        with self.viewer_3d.draw(in_imgui_window=True) as ctx:
            self._draw_robots()
            self._draw_transforms()
        # self._draw_modifiable_transforms()

        if imgui.is_window_focused() and not guizmo.is_using_any():
            self.viewer_3d.process_nav()
        imgui.end()
        self.tick_robots()

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

    def _draw_transforms(self):
        for entity, transform in esper.get_component(Transform):
            if transform.visible:
                draw_axis(transform.get_X_WT())

    def handle_keys(self):
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

    def tick_robots(self):
        pass
        # for entity, robot in esper.get_component(RobotSettings):
        #     robot.get_manager().tick()


    def _draw_robots(self):
        pass
        # for entity, robot in esper.get_component(RobotSettings):
        #     draw_robot(robot.get_manager().q)
