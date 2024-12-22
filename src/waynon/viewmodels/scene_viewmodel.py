import trio
import esper

from imgui_bundle import imgui

from waynon.components.tree_utils import *
from waynon.components.scene_utils import get_root_id
from waynon.components.component import Component
from waynon.components.node import Node
from waynon.components.simple import Draggable, Nestable

class SceneViewModel:
    def __init__(self, nursery: trio.Nursery):
        self.nursery = nursery  
        self.save_file_dialog = None
        self.new_camera_name = ""
        self._space_from_end = 23
        self.selected_camera_ind = 0
        self.selected_entity_id = -1
        self.previous_selected_entity_id = -1

    def render_node(self, entity_id):
        imgui.push_id(entity_id)
        node = esper.component_for_entity(entity_id, Node)
        draggable = esper.has_component(entity_id, Draggable)
        nestable = esper.has_component(entity_id, Nestable)
        selected = self.selected_entity_id == entity_id
        ctrl = imgui.get_io().key_ctrl
        if draggable and not ctrl:
            drag_component = esper.component_for_entity(entity_id, Draggable)
            if imgui.begin_drag_drop_source():
                imgui.set_drag_drop_payload_py_id(drag_component.type, entity_id)
                imgui.end_drag_drop_source()
            if imgui.begin_drag_drop_target():
                payload = imgui.accept_drag_drop_payload_py_id(drag_component.type)
                if payload and esper.entity_exists(payload.data_id):
                    move_entity_over(payload.data_id, target_entity_id=entity_id) # move payload to dest
                imgui.end_drag_drop_target()
        
        if nestable and ctrl:
            nest_component = esper.component_for_entity(entity_id, Nestable)
            if nest_component.source:
                if imgui.begin_drag_drop_source():
                    imgui.set_drag_drop_payload_py_id(nest_component.type, entity_id)
                    imgui.end_drag_drop_source()
            if nest_component.target:
                if imgui.begin_drag_drop_target():
                    payload = imgui.accept_drag_drop_payload_py_id(nest_component.type)
                    if payload and esper.entity_exists(payload.data_id):
                        parent_entity_to(payload.data_id, entity_id) # move payload to dest
                    imgui.end_drag_drop_target()

        if imgui.begin_popup_context_item(f"##{entity_id}"):
            for component in get_sorted_components(entity_id):
                component.draw_context(self.nursery, entity_id)
            imgui.end_popup()
        
        if selected:
            selected_positive_edge = selected and self.previous_selected_entity_id != self.selected_entity_id
            for component in get_sorted_components(entity_id):
                component.on_selected(self.nursery, entity_id, just_selected=selected_positive_edge)

        self.previous_selected_entity_id = self.selected_entity_id
        
        imgui.pop_id()
    
    def traverse_tree(self, entity_id = None):
        if entity_id is None:
            entity_id = get_root_id()
        node = esper.component_for_entity(entity_id, Node)
        is_leaf = not node.children
        flags = imgui.TreeNodeFlags_.open_on_arrow | imgui.TreeNodeFlags_.default_open
        if is_leaf:
            flags |= imgui.TreeNodeFlags_.leaf
        selected = self.selected_entity_id == entity_id
        if selected:
            flags |= imgui.TreeNodeFlags_.selected

        if entity_id == get_root_id():
            for child in node.children:
                self.traverse_tree(child.entity_id)
        else:
            if imgui.tree_node_ex(f"{node.name}##{node.entity_id}", flags):
                if imgui.is_item_clicked():
                    self.selected_entity_id = entity_id
                    esper.dispatch_event("property", entity_id)

                self.render_node(entity_id)
                for child in node.children:
                    self.traverse_tree(child.entity_id)
                imgui.tree_pop()

    def draw(self):
        imgui.begin("Scene")
        self.traverse_tree()
        # if clicked on empty space
        if imgui.is_window_hovered() and imgui.is_mouse_clicked(0):
            self.selected_entity_id = -1
            esper.dispatch_event("property", -1)
            esper.dispatch_event("modify_transform", -1)
        imgui.end()

def get_sorted_components(entity_id):
    components: list[Component] = list(esper.components_for_entity(entity_id))
    components.sort(key=lambda x: x.property_order())
    return components   