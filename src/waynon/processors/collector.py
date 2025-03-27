# Copyright (c) 2025 Boston Dynamics AI Institute LLC. All rights reserved.

from typing import Tuple
import numpy as np

from PIL import Image
import esper
import trio

from waynon.components.simple import Pose, Deletable
from waynon.components.pose_group import PoseGroup
from waynon.components.tree_utils import *
from waynon.components.scene_utils import get_world_id, is_dynamic
from waynon.components.node import Node
from waynon.components.robot import Robot
from waynon.components.camera import PinholeCamera
from waynon.components.collector import CollectorData, MeasurementGroup, DataNode
from waynon.components.measurement import Measurement
from waynon.components.image_measurement import ImageMeasurement
from waynon.components.joint_measurement import JointMeasurement
from waynon.components.aruco_measurement import ArucoMeasurement
from waynon.components.transform import Transform
from waynon.solvers.factor_graph import *

class Collector:
    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = Collector()
        return cls._instance    

    
    def can_run(self, data: CollectorData):
        # robot = esper.component_for_entity(data.robot_id, Franka)
        # ready_to_move = robot.get_manager().ready_to_move()
        cameras = [(i,c) for (i,c) in esper.get_component(PinholeCamera) if i not in data.camera_blacklist]
        return True
    

    async def run_detectors(self, collector_id: int):
        from waynon.components.scene_utils import get_detectors
        from waynon.components.simple import Detector

        print("Running detectors")

        detectors_ids = get_detectors(collector_id, predicate=lambda id, c: c.enabled)
        print(detectors_ids)

        # get data node
        data_node_id = find_child_with_component(collector_id, DataNode)
        measurement_group_ids = find_children_with_component(data_node_id, MeasurementGroup)

        
        for measurement_group_id in measurement_group_ids:
            measurement_ids = find_children_with_component(measurement_group_id, Measurement)
            for measurement_id in measurement_ids:
                for detector_id in detectors_ids:
                    detector = component_for_entity_with_instance(detector_id, Detector)
                    await detector.get_processor().run(detector_id, measurement_id)
                    await trio.sleep(0.0)
                await trio.sleep(0.0)
            await trio.sleep(0.0)

    async def collect(self, collector_id: int):
        from waynon.components.scene_utils import create_measurement
        from waynon.components.scene_utils import DATA_PATH

        assert esper.entity_exists(collector_id) and esper.has_component(collector_id, CollectorData)
        data = esper.component_for_entity(collector_id, CollectorData)


        cameras: list[tuple[int, PinholeCamera]] =  []
        for entity, c in esper.get_component(PinholeCamera):
            if entity in data.camera_blacklist:
                continue
            if c.get_image_u() is None:
                print(f"Camera {entity} has no image")
                return
            cameras.append((entity, c))

        pose_group_ids = find_descendants_with_component(get_world_id(), PoseGroup)
        pose_group_ids = [p for p in pose_group_ids if p not in data.group_blacklist]

        data_node_id = find_child_with_component(collector_id, DataNode)
        if not data_node_id:
            data_node_id, _ = create_entity("Data", collector_id, DataNode())
        data_node = esper.component_for_entity(data_node_id, Node)

        for i, pose_group_id in enumerate(pose_group_ids):
            group_node = esper.component_for_entity(pose_group_id, Node)
            
            # measurement_group_id = None
            for child_node in data_node.children:
                if child_node.name == group_node.name:
                    measurement_group_id = child_node.entity_id
                    delete_entity(measurement_group_id)
                    break

            measurement_group_id, _ = create_entity(group_node.name, data_node_id, MeasurementGroup(), Deletable())

            # make directories
            group_path = DATA_PATH / f"{group_node.name}"
            group_path.mkdir(exist_ok=True)
            image_dir = group_path / "images"
            image_dir.mkdir(exist_ok=True)

            pose_ids = find_descendants_with_component(pose_group_id, Pose)

            poses = get_components(pose_ids, Pose)
            robot_id = find_nearest_ancestor_with_component(pose_group_id, Robot)
            assert robot_id is not None
            robot_manager = esper.component_for_entity(robot_id, Robot).get_manager()
            if robot_manager and not robot_manager.ready_to_move():
                print("Robot not ready to move")
                return

            for pose_id, pose in zip(pose_ids, poses):
                q = pose.q
                print(f"Moving to {q}")
                await robot_manager.move_to(q)
                await trio.sleep(0.3)
                q = robot_manager.read_q().tolist()
                for k, (cam_id, cam) in enumerate(cameras):
                    # each one of these is one measurement
                    camera_node = get_node(cam_id)
                    image = cam.get_image_u()
                    print(f"Saving image for {cam_id}")
                    image_name = f"{camera_node.name}_{pose_id}.png"
                    image_path = image_dir / image_name
                    image = Image.fromarray(image)
                    await trio.to_thread.run_sync(
                        image.save, image_path # This takes a while
                    )
                    measurement_name = f"{camera_node.name} {pose_id}"

                    joint_measurement = JointMeasurement(robot_id=robot_id, joint_values=q)
                    image_measurement = ImageMeasurement(
                        camera_id=cam_id, 
                        image_path=f"{group_node.name}/images/{image_name}"
                        )

                    create_measurement(measurement_name,
                                    measurement_group_id,
                                    joint_measurement,
                                    image_measurement)
                    await trio.sleep(0.0) # give back control to the event loop

