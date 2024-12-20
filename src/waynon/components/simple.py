from typing import Optional 

import esper
from imgui_bundle import imgui

from waynon.components.component import Component

class Root(Component):
    pass

class World(Component):
    pass

class Visiblity(Component):
    enabled: bool = True
    pass

class OptimizedPose(Component):
    optimize: bool = True
    optimized_pose: Optional[list[float]] = None

class PoseFolder(Component):
    pass

class PoseGroup(Component):
    color: list[float] = [1.0, 1.0, 1.0]
    def draw_property(self, nursery, e):
        if esper.has_component(e, PoseGroup):
            imgui.separator()
            group = esper.component_for_entity(e, PoseGroup)
            flag = imgui.ColorEditFlags_.no_inputs
            _, group.color = imgui.color_edit3(f"##color", group.color, flags=flag) 

class Pose(Component):
    q: list[float] = [0.0, -0.783, 0.0, -2.362, 0.0, 1.573, 0.776]

    def draw_property(self, nursery, e):
        if esper.has_component(e, Pose):
            imgui.separator()
            c = esper.component_for_entity(e, Pose)
            q = c.q
            for i, q_i in enumerate(q):
                imgui.text(f"q{i}: {q_i:.3f}")

class Draggable(Component):
    type: str