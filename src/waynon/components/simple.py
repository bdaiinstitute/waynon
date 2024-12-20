from typing import Optional 

import esper
from imgui_bundle import imgui

from waynon.components.component import Component
from waynon.components.tree_utils import find_nearest_ancestor_with_component


class Root(Component):
    pass

class World(Component):
    def draw_context(self, nursery, entity_id):
        from waynon.components.scene_utils import create_camera
        if imgui.menu_item_simple("Add Camera"):
            create_camera("Camera", entity_id)

class Visiblity(Component):
    enabled: bool = True
    pass

class Deletable(Component):
    def draw_context(self, nursery, entity_id):
        from waynon.components.tree_utils import delete_entity
        if imgui.menu_item_simple("Delete"):
            delete_entity(entity_id)

class OptimizedPose(Component):
    optimize: bool = True
    optimized_pose: Optional[list[float]] = None

class PoseFolder(Component):
    def draw_context(self, nursery, entity_id):
        from waynon.components.scene_utils import create_posegroup
        if imgui.menu_item_simple("Add Group"):
            create_posegroup("group", entity_id)


class Pose(Component):
    q: list[float] = [0.0, -0.783, 0.0, -2.362, 0.0, 1.573, 0.776]


    def get_robot(self, entity_id):
        from waynon.components.robot import RobotSettings
        robot_id = find_nearest_ancestor_with_component(entity_id, RobotSettings)
        if robot_id is None:
            print("No robot found")
            return None
        return esper.component_for_entity(robot_id, RobotSettings).get_manager()

    def draw_context(self, nursery, entity_id):
        robot = self.get_robot(entity_id)
        if robot is not None:
            disabled = not robot.ready_to_move()
            imgui.begin_disabled(disabled)
            if imgui.menu_item_simple("Move To Pose"):
                nursery.start_soon(robot.move_to, self.q)
            imgui.end_disabled()


    def draw_property(self, nursery, e):
        if esper.has_component(e, Pose):
            imgui.separator()
            c = esper.component_for_entity(e, Pose)
            q = c.q
            for i, q_i in enumerate(q):
                imgui.text(f"q{i}: {q_i:.3f}")

class Draggable(Component):
    type: str

class Detectors(Component):
    pass