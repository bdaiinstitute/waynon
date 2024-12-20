from typing import Optional 

import esper
from imgui_bundle import imgui

from waynon.components.component import Component
from waynon.components.tree_utils import find_nearest_ancestor_with_component
from waynon.detectors.measurement_processor import MeasurementProcessor


class Root(Component):
    pass

class World(Component):
    def draw_context(self, nursery, entity_id):
        from waynon.components.scene_utils import create_camera, create_aruco_marker, create_robot
        if imgui.menu_item_simple("Add Robot"):
            create_robot("Robot", entity_id)
        if imgui.menu_item_simple("Add Camera"):
            create_camera("Camera", entity_id)
        if imgui.menu_item_simple("Add Marker"):
            create_aruco_marker("Marker", entity_id)

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
        from waynon.components.robot import Franka
        robot_id = find_nearest_ancestor_with_component(entity_id, Franka)
        if robot_id is None:
            print("No robot found")
            return None
        return esper.component_for_entity(robot_id, Franka).get_manager()

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

class Nestable(Component):
    type: str
    source: int = True
    target: int = True

class Detectors(Component):
    pass

class Detector(Component):
    enabled: bool = True

    def get_processor(self) -> MeasurementProcessor:
        raise NotImplementedError("get_processor must be implemented by subclass")

    def property_order(self):
        return 100

    def draw_property(self, nursery, entity_id):
        imgui.separator()
        _, self.enabled = imgui.checkbox("Enabled", self.enabled)