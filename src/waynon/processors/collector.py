from PIL import Image
import esper
import trio

from waynon.utils.utils import DATA_PATH
from waynon.components.simple import Pose
from waynon.components.pose_group import PoseGroup
from waynon.components.tree_utils import *
from waynon.components.node import Node
from waynon.components.robot import RobotSettings
from waynon.components.camera import Camera
from waynon.components.collector import CollectorData, MeasurementGroup, DataNode
from waynon.components.raw_measurement import RawMeasurement

class Collector:
    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = Collector()
        return cls._instance    
    
    def can_run(self, data: CollectorData):
        robot = esper.component_for_entity(data.robot_id, RobotSettings)
        ready_to_move = robot.get_manager().ready_to_move()
        cameras = [(i,c) for (i,c) in esper.get_component(Camera) if i not in data.camera_blacklist]
        all_cameras_running = all([c.running() for i,c in cameras])
        return ready_to_move and all_cameras_running
    
    # def detect_all_markers(img, marker_dict = aruco.DICT_4X4_50):
    #     aruco_dict = aruco.getPredefinedDictionary(marker_dict)
    #     parameters = aruco.DetectorParameters()
    #     detector = aruco.ArucoDetector(aruco_dict, parameters)
    #     marker_pixels, marker_ids, _ = detector.detectMarkers(img)
    #     return detector, marker_pixels, marker_ids

    # async def detect_arcuo_on_measurement(self, measurement_id: int):
    #     import cv2.aruco as aruco
    #     assert esper.entity_exists(measurement_id) and esper.has_component(measurement_id, RawMeasurement)
    #     data = esper.component_for_entity(measurement_id, RawMeasurement)




    async def collect(self, collector_id: int):
        from waynon.components.scene_utils import create_raw_measurement
        assert esper.entity_exists(collector_id) and esper.has_component(collector_id, CollectorData)
        data = esper.component_for_entity(collector_id, CollectorData)
        robot_id = data.robot_id
        assert esper.entity_exists(robot_id)

        robot_component = esper.component_for_entity(robot_id, RobotSettings)

        cameras: list[tuple[int, Camera]] =  []
        for entity, c in esper.get_component(Camera):
            if entity in data.camera_blacklist:
                continue
            cameras.append((entity, c))

        robot_manager = robot_component.get_manager()

        pose_group_ids = find_descendants_with_component(robot_id, PoseGroup)
        pose_group_ids = [p for p in pose_group_ids if p not in data.group_blacklist]

        data_node_id = find_child_with_component(collector_id, DataNode)
        if not data_node_id:
            data_node_id, _ = create_entity("Data", collector_id, DataNode())
        data_node = esper.component_for_entity(data_node_id, Node)

        for i, pose_group_id in enumerate(pose_group_ids):
            group_node = esper.component_for_entity(pose_group_id, Node)
            
            measurement_group_id = None
            for child_node in data_node.children:
                if child_node.name == group_node.name:
                    measurement_group_id = child_node.entity_id
                    delete_entity(measurement_group_id)
                    break

            measurement_group_id, _ = create_entity(group_node.name, data_node_id, MeasurementGroup())

            # make directories
            group_path = DATA_PATH / f"{group_node.name}"
            group_path.mkdir(exist_ok=True)
            image_dir = group_path / "images"
            image_dir.mkdir(exist_ok=True)

            pose_ids = find_descendants_with_component(pose_group_id, Pose)

            poses = get_components(pose_ids, Pose)
            for pose_id, pose in zip(pose_ids, poses):
                q = pose.q
                print(f"Moving to {q}")
                await robot_manager.move_to(q)
                await trio.sleep(0.2)
                q = robot_manager.q.tolist()
                for k, (cam_id, cam) in enumerate(cameras):
                    # each one of these is one measurement
                    image = cam.get_image_u()
                    print(f"Saving image for {cam.serial}")
                    image_name = f"{cam.serial}_{pose_id}.png"
                    image_path = image_dir / image_name
                    
                    Image.fromarray(image).save(image_path)
                    cam_node = esper.component_for_entity(cam_id, Node)
                    measurement_name = f"{cam_node.name} {pose_id}"
                    create_raw_measurement(measurement_name,
                                           measurement_group_id,
                                           RawMeasurement(
                                                  joint_values=q,
                                                  camera_serial=cam.serial,
                                                  image_path=str(image_path)
                                           ))
        