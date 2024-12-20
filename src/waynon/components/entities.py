from typing import Optional 

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

class Pose(Component):
    q: list[float] = [0.0, -0.783, 0.0, -2.362, 0.0, 1.573, 0.776]

class Draggable(Component):
    type: str