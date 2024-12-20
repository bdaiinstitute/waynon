from pathlib import Path
import json

from anytree import RenderTree
import esper


from .node import Node
from .simple import Root, World, Visiblity, OptimizedPose, PoseFolder, Pose, Draggable, Deletable, Detectors
from .pose_group import PoseGroup
from .robot import RobotSettings
from .collector import CollectorData, DataNode, MeasurementGroup
from .raw_measurement import RawMeasurement
from .camera import Camera
from .aruco_detector import ArucoDetector
from .transform import Transform
from .aruco_detector import ArucoDetector
from .tree_utils import create_entity

def create_camera(name:str, parent_id:int):
    return create_entity(name, parent_id, Transform(), Camera(), Deletable())

def create_collector(parent_id: int, robot_id: int):
    id, node = create_entity("Collector", parent_id, CollectorData(robot_id=robot_id))
    create_entity("Data", id, DataNode())
    return id, node


def refresh_transforms():
    Transform.refresh_transforms(get_world_id())

def create_robot(name:str, parent_id:int=None):
    rid, node = create_entity(name, parent_id, Transform(modifiable=False), RobotSettings())
    id, _ = create_entity("Poses", rid, PoseFolder())
    create_posegroup("left", id)
    create_posegroup("right", id)
    id, _ = create_posegroup("top", id)
    create_motion("q1", id, [0, 0, 0, 0, 0, 0, 0])
    create_motion("q2", id, [0, 0, 0, 0, 0, 0, 0])
    create_motion("q3", id, [0, 0, 0, 0, 0, 0, 0])
    return rid, node

def create_posegroup(name:str, parent_id:int):
    return create_entity(name, parent_id, PoseGroup(), Draggable(type="posegroup"), Deletable())

def create_motion(name:str, parent_id:int, q):
    return create_entity(name, parent_id, Pose(q=q), Draggable(type="pose"), Deletable())

def create_frame(name:str, parent_id:int, modifiable=True):
    return create_entity(name, parent_id, Transform(modifiable=modifiable))

def create_raw_measurement(name:str, parent_id:int, measurement: RawMeasurement):
    return create_entity(name, parent_id, measurement, Deletable())

def create_aruco_detector(name:str, parent_id: int):
    return create_entity(name, parent_id, ArucoDetector(), Deletable())

def create_world():
    root_id = get_root_id()
    id, node= create_entity("World", root_id, World(), Transform(modifiable=False))
    return id, node

def create_root():
    return create_entity("root", None, Root())

def create_empty_scene():
    root_id, _ = create_root()
    world_id, _ = create_world()
    robot_id, _ = create_robot("robot", world_id)
    create_camera("camera", world_id)
    create_collector(root_id, robot_id)

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

    for entity, component in esper.get_component(Node):
        old_parent_id = component.parent_entity_id
        if old_parent_id is not None:
            assert old_parent_id in old_id_to_new_id, f"Old parent id {old_parent_id} not found"
            component.parent_entity_id = old_id_to_new_id[old_parent_id]

    for entity, component in esper.get_component(Node):
        component.refresh()


def print_tree():
    root_node = get_root_node()
    for pre, _, node in RenderTree(root_node):
        id = node.entity_id
        components = esper.components_for_entity(id)
        print("%s%s" % (pre, components))