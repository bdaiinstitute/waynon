# Copyright (c) 2025 Boston Dynamics AI Institute LLC. All rights reserved.

import logging
import esper
from typing import TYPE_CHECKING
from waynon.utils.utils import COLORS
from waynon.components.node import Node
from waynon.components.renderable import Mesh
from waynon.components.robot import Franka, FrankaLink, Robot
from waynon.components.transform import Transform

if TYPE_CHECKING:
    from waynon.components.robot import Franka, Robot

logger = logging.getLogger(__name__)


class RobotProcessor(esper.Processor):
    def process(self):
        
        listcomp = esper.get_components(Robot, Franka)
        for entity, (robot, franka) in listcomp:
            manager = franka.get_manager()
            robot.set_manager(manager)
            manager.tick()

        listcomp2 = esper.get_components(
            Node, FrankaLink, Transform, Mesh
        )

        for entity, (node, link, transform, mesh) in listcomp2:
            robot_manager = esper.component_for_entity(
                link.robot_id, Robot
            ).get_manager()
            X_BL = robot_manager.last_transforms[link.link_name]  # All relative to base
            transform.set_X_PT(X_BL)
            if robot_manager.ready_to_move():
                mesh.set_color(COLORS["GREEN"])
            else:
                mesh.set_color(COLORS["RED"])
