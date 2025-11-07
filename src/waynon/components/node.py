# Copyright (c) 2025 Robotics and AI Institute LLC dba RAI Institute. All rights reserved.

from dataclasses import dataclass
from typing import Optional 
import esper
from anytree import NodeMixin

from imgui_bundle import imgui

from waynon.components.component import Component   


    


class Node(Component, NodeMixin):
    name: str = ""
    parent_entity_id: Optional[int] = None
    entity_id: Optional[int] = None
    opened: bool = False

    def model_post_init(self, __context):
        return super().model_post_init(__context)

    @property
    def parent_id(self):
        return self.parent_entity_id
    
    @parent_id.setter
    def parent_id(self, value):
        self.parent_entity_id = value
        self.refresh()
    
    def refresh(self):
        if self.parent_entity_id is not None:
            self.parent = esper.component_for_entity(self.parent_entity_id, Node)
    
    def draw_property(self, nursery, entity_id:int):
        imgui.separator_text("Node")
        _, self.name = imgui.input_text("Name", self.name)
    
    def property_order(self):
        return 0
    
    
    def _fix_on_load(self, old_to_new):
        if self.parent_entity_id in old_to_new:
            self.parent_entity_id = old_to_new[self.parent_entity_id]

