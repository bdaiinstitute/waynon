import esper
import trio
from imgui_bundle import icons_fontawesome_6 as icons
from imgui_bundle import imgui

from waynon.components.component import Component
from waynon.components.node import Node
from waynon.components.scene_utils import (deselect_all, get_collector_id,
                                           get_root_id, get_world_id,
                                           is_selected, make_selected)
from waynon.components.simple import Draggable, Nestable, Selected
from waynon.components.tree_utils import *
from waynon.utils.utils import COLORS


class SceneViewModel:
    def __init__(self, nursery: trio.Nursery):
        self.nursery = nursery
        self._create_visibility_list()

    def render_node(self, entity_id):
        imgui.push_id(entity_id)
        node = esper.component_for_entity(entity_id, Node)
        draggable = esper.has_component(entity_id, Draggable)
        nestable = esper.has_component(entity_id, Nestable)
        selected = esper.has_component(entity_id, Selected)
        ctrl = imgui.get_io().key_ctrl

        if draggable and not ctrl:
            drag_component = esper.component_for_entity(entity_id, Draggable)
            if imgui.begin_drag_drop_source():
                imgui.set_drag_drop_payload_py_id(drag_component.type, entity_id)
                imgui.end_drag_drop_source()
            if imgui.begin_drag_drop_target():
                payload = imgui.accept_drag_drop_payload_py_id(drag_component.type)
                if payload and esper.entity_exists(payload.data_id):
                    move_entity_over(
                        payload.data_id, target_entity_id=entity_id
                    )  # move payload to dest
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
                        parent_entity_to(
                            payload.data_id, entity_id
                        )  # move payload to dest
                    imgui.end_drag_drop_target()

        if imgui.begin_popup_context_item(f"##{entity_id}"):
            for component in get_sorted_components(entity_id):
                component.draw_context(self.nursery, entity_id)
            imgui.end_popup()

        imgui.pop_id()

    def traverse_tree(self, entity_id: int):

        node = esper.component_for_entity(entity_id, Node)
        is_leaf = not node.children
        selected = is_selected(entity_id)
        flags = (
            imgui.TreeNodeFlags_.open_on_arrow.value
            | imgui.TreeNodeFlags_.span_avail_width.value
        )
        if is_leaf:
            flags |= imgui.TreeNodeFlags_.leaf.value

        if selected:
            flags |= imgui.TreeNodeFlags_.selected.value

        self._add_id_to_visiblity_list(entity_id)
        imgui.set_next_item_selection_user_data(self._current_visibility_id())

        valid = node.valid()
        if not valid:
            imgui.push_style_color(imgui.Col_.text.value, COLORS["RED"])
        opened = imgui.tree_node_ex(f"{node.name}##Node_{node.entity_id}", flags)
        if not valid:
            imgui.pop_style_color()

        if selected:
            for component in esper.components_for_entity(entity_id):
                component.on_selected(
                    self.nursery,
                    entity_id,
                    just_selected=False,
                )

        if opened:
            self.render_node(entity_id)
            for child in node.children:
                self.traverse_tree(child.entity_id)
            imgui.tree_pop()

    def draw(self):
        self._just_selected = False
        imgui.begin(f"Scene")
        flags = imgui.MultiSelectFlags_.single_select.value
        select_io = imgui.begin_multi_select(flags=flags)
        self._apply_selection_requests(select_io)
        self._clear_visibility_list()
        self.traverse_tree(get_world_id())
        imgui.end_multi_select()
        self._apply_selection_requests(select_io)
        imgui.end()

        imgui.begin("Calibrator")
        select_io = imgui.begin_multi_select(flags=flags)
        self._apply_selection_requests(select_io)
        self._clear_visibility_list()
        self.traverse_tree(get_collector_id())
        imgui.end_multi_select()
        self._apply_selection_requests(select_io)
        imgui.end()
        # if clicked on empty space
        # if imgui.is_window_hovered() and imgui.is_mouse_clicked(0):
        #     self.selected_entity_id = -1
        #     esper.dispatch_event("property", -1)
        #     esper.dispatch_event("modify_transform", -1)

    def _apply_selection_requests(self, select_io: imgui.MultiSelectIO):
        for req in select_io.requests:
            if req.type == imgui.SelectionRequestType.set_all.value:
                if not req.selected:
                    deselect_all()
            elif req.type == imgui.SelectionRequestType.set_range.value:
                for i in range(
                    req.range_first_item, req.range_last_item + 1, req.range_direction
                ):
                    entity_id = self._visibility_list[i]
                    make_selected(entity_id)
                    for component in esper.components_for_entity(entity_id):
                        component.on_selected(self.nursery, entity_id, True)

    def _add_id_to_visiblity_list(self, id: int):
        if len(self._visibility_list) <= self._visibility_pointer:
            self._visibility_list.append(id)
        else:
            self._visibility_list[self._visibility_pointer] = id
        self._visibility_pointer += 1

    def _current_visibility_id(self) -> int:
        return self._visibility_pointer - 1

    def _create_visibility_list(self):
        self._visibility_list = []
        self._visibility_pointer = 0

    def _clear_visibility_list(self):
        self._visibility_pointer = 0


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
