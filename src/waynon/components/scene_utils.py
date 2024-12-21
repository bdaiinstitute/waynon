from typing import Callable, Type
from pathlib import Path
import json

from anytree import RenderTree
import esper


from .node import Node
from .simple import Root, World, Visiblity, OptimizedPose, PoseFolder, Pose, Draggable, Deletable, Detectors, Detector, Nestable
from .aruco_marker import ArucoMarker
from .pose_group import PoseGroup
from .robot import Franka, FrankaLink
from .collector import CollectorData, DataNode, MeasurementGroup
from .raw_measurement import RawMeasurement
from .image_measurement import ImageMeasurement
from .camera import Camera
from .aruco_detector import ArucoDetector, ArucoMeasurement
from .transform import Transform
from .tree_utils import *
from .renderable import Mesh, ImageQuad

def create_camera(name:str, parent_id:int):
    return create_entity(name, parent_id, 
                        Transform(), 
                        Camera(), 
                        Deletable(), 
                        Draggable(type="transform"),
                        Nestable(type="transform", target=False)
                        )

def create_aruco_marker(name:str, parent_id:int, marker: ArucoMarker = ArucoMarker()):
    return create_entity(name, parent_id, 
                        marker, 
                        Transform(), 
                        Deletable(), 
                        Draggable(type="transform"),
                        Nestable(type="transform", target=False),
                        ImageQuad.create_aruco_quad(marker.marker_length)
                        )
    
def create_collector(parent_id: int, robot_id: int):
    id, node = create_entity("Collector", parent_id, CollectorData(robot_id=robot_id))
    create_entity("Data", id, DataNode())
    return id, node

def create_robot(name:str, parent_id:int=None):
    rd, node = create_entity(name, parent_id, 
                              Transform(modifiable=False), 
                              Franka(), 
                              Deletable(), 
                              Draggable(type="transform"),
                              Nestable(type="transform", target=True, source=False)
                              )
    id, _ = create_entity("Poses", rd, PoseFolder())

    link_to_mesh_name = {
        "panda_link0": "link0",
        "panda_link1": "link1",
        "panda_link2": "link2",
        "panda_link3": "link3",
        "panda_link4": "link4",
        "panda_link5": "link5",
        "panda_link6": "link6",
        "panda_link7": "link7",
        "panda_hand": "hand",
        "panda_leftfinger": "finger",
        "panda_rightfinger": "finger"
    }

    def link_components(name):
        mesh_path = f"robots/panda/meshes/{link_to_mesh_name[name]}.stl"
        return [Transform(modifiable=False), 
                Nestable(type="transform", target=True, source=False), 
                Mesh(mesh_path=mesh_path),
                FrankaLink(robot_id=rd, link_name=name)]

    l0, _ = create_entity("L0", rd, *link_components("panda_link0")) 
    l1, _ = create_entity("L1", l0, *link_components("panda_link1")) 
    l2, _ = create_entity("L2", l1, *link_components("panda_link2")) 
    l3, _ = create_entity("L3", l2, *link_components("panda_link3")) 
    l4, _ = create_entity("L4", l3, *link_components("panda_link4")) 
    l5, _ = create_entity("L5", l4, *link_components("panda_link5")) 
    l6, _ = create_entity("L6", l5, *link_components("panda_link6")) 
    l7, _ = create_entity("L7", l6, *link_components("panda_link7")) 
    l8, _ = create_entity("Hand", l7, *link_components("panda_hand")) 
    return rd, node

def create_posegroup(name:str, parent_id:int):
    return create_entity(name, parent_id, 
                         PoseGroup(), 
                         Draggable(type="posegroup"), 
                         Deletable())

def create_motion(name:str, parent_id:int, q):
    return create_entity(name, parent_id, 
                         Pose(q=q), 
                         Draggable(type="pose"), 
                         Deletable())


def create_frame(name:str, parent_id:int, modifiable=True):
    return create_entity(name, parent_id, 
                         Transform(modifiable=modifiable))

def create_raw_measurement(name:str, parent_id:int, measurement: ImageMeasurement):
    return create_entity(name, parent_id, 
                        measurement, 
                        Deletable())

def create_aruco_detector(name:str, parent_id: int):
    return create_entity(name, parent_id, 
                        ArucoDetector(), 
                        Deletable())

def create_world():
    root_id = get_root_id()
    id, node= create_entity("World", root_id, 
                            World(), 
                            Transform(modifiable=False),
                            Nestable(type="transform", source=False)
                            )
    return id, node

def create_root():
    return create_entity("root", None, Root())

def create_empty_scene():
    root_id, _ = create_root()
    world_id, _ = create_world()
    # create_collector(root_id, robot_id)

def get_root_node():
    return esper.get_components(Root, Node)[0][1][1]

def get_root_id():
    return esper.get_components(Root)[0][0]

def get_world_id():
    return esper.get_components(World)[0][0]

def save_scene(path: Path = Path("default.json")):
    print(f"Saving to {path}")
    path = Path(path)
    res = {}
    for entity_id, components in esper._entities.items():
        res[entity_id] = {}
        for class_name, component in components.items():
            res[entity_id][class_name.__name__] = component.model_dump()
    
    with open(path, "w") as f:
        f.write(json.dumps(res, indent=4))

def load_scene(path: Path = Path("default.json")):
    print(f"Loading from {path}")
    if not path.exists():
        print(f"File {path} does not exist")
        return
    with open(path, "r") as f:
        res = json.load(f)
    esper.clear_database()
    esper.clear_cache()
    old_id_to_new_id = {}
    for entity_id, components in res.items():
        entity_id = int(entity_id)  
        entity = esper.create_entity()
        old_id_to_new_id[entity_id] = entity
        for class_name, component in components.items():
            class_name = globals()[class_name]
            component = class_name.model_validate(component)
            if isinstance(component, Node):
                component.entity_id = entity
            esper.add_component(entity, component)

    for entity, component_dict in esper._entities.items():
        for component_type, component in component_dict.items():
            component._fix_on_load(old_id_to_new_id)

    for entity, component in esper.get_component(Node):
        component.refresh()

def get_detectors(collector_id: int, predicate: Callable[[int, Detector], bool] | None = None):
    from waynon.components.simple import Detectors, Detector
    assert esper.has_component(collector_id, CollectorData)
    entity_id = find_child_with_component(collector_id, Detectors)
    if entity_id is None:
        return []

    node = get_node(entity_id)
    children = []
    for child in node.children:
        child_id = child.entity_id
        component= component_for_entity_with_instance(child_id, Detector)
        if predicate is None or predicate(child_id, component):
            children.append(child_id)
    return children



def print_tree():
    root_node = get_root_node()
    for pre, _, node in RenderTree(root_node):
        id = node.entity_id
        components = esper.components_for_entity(id)
        print("%s%s" % (pre, components))