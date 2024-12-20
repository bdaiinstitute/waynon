import esper
from typing import TypeVar
from .node import Node

T = TypeVar("T")

def find_child_with_component(entity_id, component_type) -> int | None:
    node = esper.component_for_entity(entity_id, Node)
    for child in node.descendants:
        if esper.has_component(child.entity_id, component_type):
            return child.entity_id
    return None

def find_children_with_component(entity_id, component_type) -> list[int]:
    node = esper.component_for_entity(entity_id, Node)
    children = []
    for child in node.children:
        if esper.has_component(child.entity_id, component_type):
            children.append(child.entity_id)
    return children

def find_descendants_with_component(entity_id, component_type) -> list[int]:
    node = esper.component_for_entity(entity_id, Node)
    children = []
    for child in node.descendants:
        if esper.has_component(child.entity_id, component_type):
            children.append(child.entity_id)
    return children

def find_nearest_ancestor_with_component(entity_id, component_type) -> int | None:
    node = esper.component_for_entity(entity_id, Node)
    for parent_node in node.ancestors:
        if esper.has_component(parent_node.entity_id, component_type):
            return parent_node.entity_id
    return None

def delete_entity(entity_id):
    node = esper.component_for_entity(entity_id, Node)
    node.parent = None
    for child_node in node.children:
        delete_entity(child_node.entity_id)
    esper.delete_entity(entity_id)

def get_components(entity_ids: list[int], component_type: T):
    components: list[T] = []
    for entity_id in entity_ids:
        assert esper.has_component(entity_id, component_type)
        components.append(esper.component_for_entity(entity_id, component_type))
    return components

def create_entity(name:str, parent_id:int, *components): 
    id = esper.create_entity(*components)
    node = Node(name=name, parent_entity_id=parent_id, entity_id=id)
    node.refresh()
    esper.add_component(id, node)
    return id, node
