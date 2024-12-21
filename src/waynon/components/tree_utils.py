from collections.abc import Callable
import esper
from typing import TypeVar
from .node import Node

T = TypeVar("T")



def get_node(entity_id: int) -> Node:
    return esper.component_for_entity(entity_id, Node)

def find_child_with_component(entity_id, component_type: T, predicate: Callable[[int, T], bool] | None = None) -> int | None:
    node = get_node(entity_id)
    for child in node.children:
        if esper.has_component(child.entity_id, component_type):
            component = esper.component_for_entity(child.entity_id, component_type)
            if predicate is None or predicate(child.entity_id, component):
                return child.entity_id
    return None

def find_descendant_with_component(entity_id, component_type, predicate: Callable[[int, T], bool] | None = None) -> int | None:
    node = get_node(entity_id)
    for child in node.descendants:
        if esper.has_component(child.entity_id, component_type):
            component = esper.component_for_entity(child.entity_id, component)
            if predicate is None or predicate(child.entity_id, component):
                return child.entity_id
    return None

def find_children_with_component(entity_id, component_type: T, predicate: Callable[[int, T], bool] | None = None) -> list[int]:
    node = get_node(entity_id)
    children = []
    for child in node.children:
        if esper.has_component(child.entity_id, component_type):
            component = esper.component_for_entity(child.entity_id, component_type)
            if predicate is None or predicate(child.entity_id, component):
                children.append(child.entity_id)
    return children

def find_descendants_with_component(entity_id, component_type, predicate: Callable[[int, T], bool] | None = None) -> list[int]:
    node = get_node(entity_id)
    children = []
    for child in node.descendants:
        if esper.has_component(child.entity_id, component_type):
            component = esper.component_for_entity(child.entity_id, component_type)
            if predicate is None or predicate(child.entity_id, component):
                children.append(child.entity_id)
    return children

def find_nearest_ancestor_with_component(entity_id, component_type, predicate: Callable[[int, T], bool] = None) -> int | None:
    node = get_node(entity_id)
    for parent_node in node.ancestors:
        if esper.has_component(parent_node.entity_id, component_type):
            component = esper.component_for_entity(parent_node.entity_id, component_type)
            if predicate is None or predicate(parent_node.entity_id, component):
                return parent_node.entity_id
    return None

def delete_entity(entity_id, predicate: Callable[[int, Node], bool] = None):
    node = get_node(entity_id)
    node.parent = None
    for child_node in node.children:
        if predicate is None or predicate(child_node.entity_id, child_node):
            delete_entity(child_node.entity_id)
    esper.delete_entity(entity_id)

def delete_children(entity_id, predicate: Callable[[int, Node], bool] = None):
    node = get_node(entity_id)
    for child_node in node.children:
        delete_entity(child_node.entity_id, predicate)

def parent_entity_to(entity_id:int, parent_id:int):
    node = get_node(entity_id)
    node.parent_id = parent_id
    # make first child
    move_entity_over(entity_id, node.parent.children[0].entity_id)

def move_entity_over(moving_entity_id, target_entity_id):
    if moving_entity_id == target_entity_id:
        return
    moving_node = get_node(moving_entity_id)
    target_node = get_node(target_entity_id)
    # children are immutable, so we need to create a new list
    # if parents are different, we need to update both
    if moving_node.parent != target_node.parent:
        moving_node.parent_id = target_node.parent_id

    source_position_in_parent = moving_node.parent.children.index(moving_node)
    new_children = list(moving_node.parent.children)
    new_children.pop(source_position_in_parent)
    target_position_in_parent = target_node.parent.children.index(target_node)
    new_children.insert(target_position_in_parent, moving_node)
    moving_node.parent.children = tuple(new_children)

def get_components(entity_ids: list[int], component_type: T, predicate: Callable[[int, T], bool] = None):
    components: list[T] = []
    for entity_id in entity_ids:
        assert esper.has_component(entity_id, component_type)
        component = esper.component_for_entity(entity_id, component_type)
        if predicate is None or predicate(entity_id, component):
            components.append(component)
    return components

def create_entity(name:str, parent_id:int, *components): 
    id = esper.create_entity(*components)
    node = Node(name=name, parent_entity_id=parent_id, entity_id=id)
    node.refresh()
    esper.add_component(id, node)
    return id, node

def component_for_entity_with_instance(entity_id: int, component_type: T)-> T | None:
    components = esper.components_for_entity(entity_id)
    for component in components:
        if isinstance(component, component_type):
            return component
    return None

def try_component(entity_id: int, component_type: T) -> T | None:
    if not esper.entity_exists(entity_id):
        print(f"Warning: entity {entity_id} does not exist")
        return None
    if esper.has_component(entity_id, component_type):
        return esper.component_for_entity(entity_id, component_type)
    else:
        print(f"Warning: entity {entity_id} does not have component {component_type}")