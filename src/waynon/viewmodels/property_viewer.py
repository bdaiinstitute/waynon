# Copyright (c) 2025 Robotics and AI Institute LLC dba RAI Institute. All rights reserved.

import esper
import trio
from imgui_bundle import imgui

from waynon.components.component import Component
from waynon.components.scene_utils import get_first_selected_entity


class PropertyViewModel:
    def __init__(self, nursery: trio.Nursery):
        self.selected_entity = -1
        self.nursery = nursery
        esper.set_handler("property", self._on_entity_selected)

    def draw(self):
        # get first selected entity
        self.selected_entity = get_first_selected_entity()

        imgui.begin("Properties")
        if not self.selected_entity:
            imgui.text("Select an entity")
        else:
            e = self.selected_entity
            _dispatch_draw(e, self.nursery)
        imgui.end()

    def _on_entity_selected(self, entity_id):
        self.selected_entity = entity_id


def _dispatch_draw(entitiy_id: int, nursery: trio.Nursery):
    components: list[Component] = list(esper.components_for_entity(entitiy_id))
    components.sort(key=lambda x: x.property_order())
    for component in components:
        component.draw_property(nursery, entitiy_id)
