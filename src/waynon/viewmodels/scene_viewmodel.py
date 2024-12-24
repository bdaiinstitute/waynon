import trio
import esper

from imgui_bundle import imgui
from imgui_bundle import icons_fontawesome_6 as icons

from waynon.utils.utils import COLORS
from waynon.components.tree_utils import *
from waynon.components.scene_utils import get_root_id, get_world_id, get_collector_id
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
        flags = imgui.TreeNodeFlags_.open_on_arrow 
        if is_leaf:
            flags |= imgui.TreeNodeFlags_.leaf
        selected = self.selected_entity_id == entity_id
        if selected:
            flags |= imgui.TreeNodeFlags_.selected

        if entity_id == get_root_id():
            for child in node.children:
                self.traverse_tree(child.entity_id)
        else:
            # opened, clicked = tree_node(f"{node.name}##{node.entity_id}", flags)
            # if clicked:
            #     self.selected_entity_id = entity_id
            #     esper.dispatch_event("property", entity_id)
            # if opened:
            valid = node.valid()
            if not valid:
                imgui.push_style_color(imgui.Col_.text, COLORS["RED"])
            opened = imgui.tree_node_ex(f"{node.name}##{node.entity_id}", flags)
            if not valid:
                imgui.pop_style_color()
            if opened:
                if imgui.is_item_clicked(0):
                    self.selected_entity_id = entity_id
                    esper.dispatch_event("property", entity_id)
                self.render_node(entity_id)
                for child in node.children:
                    self.traverse_tree(child.entity_id)
                imgui.tree_pop()
            if not opened and imgui.is_item_clicked(0):
                self.selected_entity_id = entity_id
                esper.dispatch_event("property", entity_id)

    def draw(self):
        imgui.begin(f"Scene")
        self.traverse_tree(get_world_id())
        imgui.end()
        imgui.begin("Calibrator")
        self.traverse_tree(get_collector_id())
        imgui.end()
        # if clicked on empty space
        # if imgui.is_window_hovered() and imgui.is_mouse_clicked(0):
        #     self.selected_entity_id = -1
        #     esper.dispatch_event("property", -1)
        #     esper.dispatch_event("modify_transform", -1)

def get_sorted_components(entity_id):
    components: list[Component] = list(esper.components_for_entity(entity_id))
    components.sort(key=lambda x: x.property_order())
    return components   


# def tree_node(label: str, flags: imgui.TreeNodeFlags_ = 0):
#     g = imgui.get_current_context()
#     window = g.current_window
#     id = window.get_id(label)
#     pos = window.dc.cursor_pos
#     bb = imgui.internal.ImRect(pos, imgui.ImVec2(pos.x + imgui.get_content_region_avail().x, pos.y + g.font_size + g.style.frame_padding.y*2))
#     opened = imgui.internal.tree_node_get_open(id)
#     # opened = imgui.internal.tree_node_behavior(id, flags, label)
#     hovered = False
#     held = False
#     clicked, hovered, held = imgui.internal.button_behavior(bb, id, hovered, held)
#     double_clicked = False
#     if hovered and g.io.mouse_clicked_count[0] == 2:
#         double_clicked = True

#     selected = flags & imgui.TreeNodeFlags_.selected
#     if double_clicked:
#         window.dc.state_storage.set_int(id, 0 if opened else 1)
#     if hovered or held:
#         window.draw_list.add_rect_filled(bb.min, bb.max, imgui.get_color_u32(imgui.Col_.header_active if held else imgui.Col_.header_hovered))
#     if selected:
#         window.draw_list.add_rect_filled(bb.min, bb.max, imgui.get_color_u32(imgui.Col_.header_active))
    
#     is_leaf = flags & imgui.TreeNodeFlags_.leaf
    
#     if is_leaf:
#         label = f"  {label}"
#     else:
#         icon = icons.ICON_FA_CARET_DOWN if opened else icons.ICON_FA_CARET_RIGHT
#         label = f"{icon} {label}"
#     imgui.internal.render_text(imgui.ImVec2(pos.x + g.style.item_inner_spacing.x, pos.y + g.style.frame_padding.y), label)
#     imgui.internal.item_size(bb, g.style.frame_padding.y)
#     imgui.internal.item_add(bb, id)
#     if opened:
#         imgui.tree_push(label)

#     return opened, clicked