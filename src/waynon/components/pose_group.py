from typing import Optional 

import esper
from imgui_bundle import imgui

from waynon.components.tree_utils import find_nearest_ancestor_with_component, delete_entity
from waynon.components.component import Component
from waynon.components.node import Node
from waynon.components.robot import Franka

class PoseGroup(Component):
    color: list[float] = [1.0, 1.0, 1.0]


    def get_robot(self, entity_id):
        robot_id = find_nearest_ancestor_with_component(entity_id, Franka)
        if robot_id is None:
            print("No robot found")
            return
        return esper.component_for_entity(robot_id, Franka).get_manager()

    def draw_property(self, nursery, e):
        if esper.has_component(e, PoseGroup):
            imgui.separator()
            group = esper.component_for_entity(e, PoseGroup)
            flag = imgui.ColorEditFlags_.no_inputs
            _, group.color = imgui.color_edit3(f"##color", group.color, flags=flag) 
            imgui.text_wrapped("Press 'circle' on the robot to add a pose and 'cross' to delete the last pose added in this group.")
    
    def draw_context(self, nursery, entity_id):
        if imgui.menu_item_simple("Capture robot pose"):
            from waynon.components.scene_utils import create_motion
            robot = self.get_robot(entity_id)
            if robot:
                create_motion("q", entity_id, robot.q)
        
    def on_selected(self, nursery, entity_id, just_selected):
        from waynon.components.scene_utils import create_motion
        node = esper.component_for_entity(entity_id, Node)
        robot_id = find_nearest_ancestor_with_component(entity_id, Franka)
        if robot_id is None:
            print("No robot found")
            return
        robot = esper.component_for_entity(robot_id, Franka).get_manager()
        if robot.is_button_pressed("circle"):
            create_motion("q", entity_id, robot.q)
        if robot.is_button_pressed("cross"):
            print("deleting")
            if node.children:
                child_id = node.children[-1].entity_id
                delete_entity(child_id)