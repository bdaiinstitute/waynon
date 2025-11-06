# Copyright (c) 2025 Robotics and AI Institute LLC dba RAI Institute. All rights reserved.

import numpy as np
import esper

from waynon.components.node import Node
from waynon.components.transform import Transform
from waynon.components.scene_utils import get_world_id

class TransformProcessor(esper.Processor):

    @staticmethod
    def refresh_transforms(node_id, X_WT = np.eye(4, dtype=np.float32), transform_parent_id = None, dirty = False):
        assert esper.has_component(node_id, Node), f"Entity {node_id} does not have a Node component"
        node = esper.component_for_entity(node_id, Node)
        if esper.has_component(node_id, Transform):
            transform = esper.component_for_entity(node_id, Transform)
            dirty = dirty or transform._dirty
            if dirty:
                X_WT = X_WT @ transform.get_X_PT()
                transform._X_WT = X_WT.flatten().tolist()
                transform._dirty = False
                if transform_parent_id is not None:
                    transform._parent_id = transform_parent_id
            X_WT = transform.get_X_WT()
            transform_parent_id = node_id

        for n in node.children:
            TransformProcessor.refresh_transforms(n.entity_id, X_WT, transform_parent_id, dirty)

    def process(self):        
        TransformProcessor.refresh_transforms(get_world_id())