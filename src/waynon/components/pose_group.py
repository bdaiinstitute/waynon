from typing import Optional 
import trio

import esper
from imgui_bundle import imgui

from waynon.components.tree_utils import find_nearest_ancestor_with_component, delete_entity, find_children_with_component
from waynon.components.component import Component
from waynon.components.node import Node
from waynon.components.robot import Robot, FrankaManager
from waynon.utils.utils import COLORS
from waynon.components.simple import Pose

class PoseGroup(Component):
    color: list[float] = [1.0, 1.0, 1.0]


    def model_post_init(self, __context):
        self._cancel_context = trio.CancelScope()
        self._moving = False
        self._progress = 0
        self._total= 0


    def get_robot_manager(self, entity_id):
        robot_id = find_nearest_ancestor_with_component(entity_id, Robot)
        if robot_id is None:
            print("No robot found")
            return
        return esper.component_for_entity(robot_id, Robot).get_manager()
    
    def get_poses(self, entity_id):
        qs = []
        pose_ids = find_children_with_component(entity_id, Pose)
        for pose_id in pose_ids:
            pose = esper.component_for_entity(pose_id, Pose)
            qs.append(pose.q)
        return qs
    
    async def cycle(self, entity_id):
        self._cancel_context.cancel()   
        self._cancel_context = trio.CancelScope()

        qs = self.get_poses(entity_id)
        self._total = len(qs)
        with self._cancel_context:
            self._moving = True
            robot_manager = self.get_robot_manager(entity_id)
            if robot_manager is None:
                print("No robot manager attached")
                return
            for i, q in enumerate(qs):
                self._progress = i
                await robot_manager.move_to(q)

        self._moving = False


    def draw_property(self, nursery, e):
        assert esper.has_component(e, PoseGroup)
        imgui.separator_text("Pose Group")
        group = esper.component_for_entity(e, PoseGroup)
        # flag = imgui.ColorEditFlags_.no_inputs
        # _, group.color = imgui.color_edit3(f"##color", group.color, flags=flag) 
        imgui.text_wrapped("Press 'circle' on the robot to add a pose and 'cross' to delete the last pose added in this group.")
        imgui.spacing()
        robot = self.get_robot_manager(e)

        disabled = not robot.ready_to_move()
        if not self._moving:
            imgui.begin_disabled(disabled)
            imgui.push_style_color(imgui.Col_.button, COLORS["BLUE"])
            if imgui.button("Cycle", (imgui.get_content_region_avail().x, 40)):
                nursery.start_soon(self.cycle, e)
            if disabled:
                imgui.set_item_tooltip("Robot is not ready to move")
            imgui.pop_style_color()
            imgui.end_disabled()
        else:
            imgui.push_style_color(imgui.Col_.button, COLORS["RED"])
            if imgui.button("Stop", (imgui.get_content_region_avail().x, 20)):
                self._cancel_context.cancel()
            imgui.pop_style_color()
            imgui.progress_bar(self._progress / self._total, (imgui.get_content_region_avail().x, 40))

        

    
    def draw_context(self, nursery, entity_id):
        if imgui.menu_item_simple("Capture robot pose"):
            from waynon.components.scene_utils import create_motion
            robot = self.get_robot_manager(entity_id)
            if robot:
                create_motion(entity_id, robot.read_q())
        
    def on_selected(self, nursery, entity_id, just_selected):
        from waynon.components.scene_utils import create_motion
        node = esper.component_for_entity(entity_id, Node)
        robot_id = find_nearest_ancestor_with_component(entity_id, Robot)
        if robot_id is None:
            print("No robot found")
            return
        robot_manager = esper.component_for_entity(robot_id, Robot).get_manager()
        if robot_manager and isinstance(robot_manager, FrankaManager):
            if robot_manager.is_button_pressed("circle"):
                create_motion(entity_id, robot_manager.read_q())
            if robot_manager.is_button_pressed("cross"):
                if node.children:
                    child_id = node.children[-1].entity_id
                    delete_entity(child_id)
    
    @staticmethod
    def default_name():
        return "Pose Group"