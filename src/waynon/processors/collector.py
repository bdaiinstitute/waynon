from typing import Tuple
import numpy as np

from PIL import Image
import esper
import trio

from waynon.utils.utils import DATA_PATH
from waynon.components.simple import Pose
from waynon.components.pose_group import PoseGroup
from waynon.components.tree_utils import *
from waynon.components.scene_utils import get_world_id, is_dynamic
from waynon.components.node import Node
from waynon.components.robot import Franka
from waynon.components.camera import Camera
from waynon.components.collector import CollectorData, MeasurementGroup, DataNode
from waynon.components.measurement import Measurement
from waynon.components.image_measurement import ImageMeasurement
from waynon.components.joint_measurement import JointMeasurement
from waynon.components.aruco_detector import ArucoMeasurement
from waynon.components.transform import Transform
from waynon.solvers.factor_graph import *

import symforce
symforce.set_epsilon_to_symbol()
from symforce.values import Values
import symforce.symbolic as sf
from symforce.opt.factor import Factor
from symforce.opt.optimizer import Optimizer
from symforce.opt.noise_models import DiagonalNoiseModel
import sym



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
        cameras = [(i,c) for (i,c) in esper.get_component(Camera) if i not in data.camera_blacklist]
        all_cameras_running = all([c.running() for i,c in cameras])
        return all_cameras_running
    

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

    async def collect(self, collector_id: int):
        from waynon.components.scene_utils import create_measurement

        assert esper.entity_exists(collector_id) and esper.has_component(collector_id, CollectorData)
        data = esper.component_for_entity(collector_id, CollectorData)


        cameras: list[tuple[int, Camera]] =  []
        for entity, c in esper.get_component(Camera):
            if entity in data.camera_blacklist:
                continue
            cameras.append((entity, c))

        pose_group_ids = find_descendants_with_component(get_world_id(), PoseGroup)
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
            robot_id = find_nearest_ancestor_with_component(pose_group_id, Franka)
            assert robot_id is not None
            robot_manager = esper.component_for_entity(robot_id, Franka).get_manager()

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

                    joint_measurement = JointMeasurement(robot_id=robot_id, joint_values=q)
                    image_measurement = ImageMeasurement(camera_id=cam_id, image_path=str(image_path))

                    create_measurement(measurement_name,
                                    measurement_group_id,
                                    joint_measurement,
                                    image_measurement)

    async def calibrate(self):
        from symforce.opt.optimizer import Optimizer
        from symforce.opt.factor import Factor

        initial_values = {}

        # stationary_camera_keys = [f"X_BC_{serial}" for serial in serials if cameras[serial]["mount"] == "static"]
        # mounted_cameras_key = [f"X_EC_{serial}" for serial in serials if cameras[serial]["mount"] != "static"]
        # static_marker_keys = [f"X_BM_{marker.idx}" for marker in STATIC_BOARD_IDS]
        # mounted_marker_keys = [f"X_EM_{marker.idx}" for marker in HAND_MARKER_IDS]

        # optimizer = Optimizer(
        #     factors=[*eye_to_hand_factors, *eye_in_hand_factors, *marker_factors],
        #     # factors=[*eye_to_hand_factors],
        #     optimized_keys=[*stationary_camera_keys, *mounted_cameras_key, *mounted_marker_keys, *static_marker_keys],
        #     # optimized_keys=[*stationary_camera_keys, *mounted_marker_keys],
        #     debug_stats=True,
        #     params=Optimizer.Params(
        #         verbose=True,
        #         iterations=250,
        #         early_exit_min_reduction=1e-10,
        #         enable_bold_updates=True,
        #         )
        # )

        for entity, aruco_measurement in esper.get_component(ArucoMeasurement):
            # go up the graph to find holding measurement
            measurement_id = find_nearest_ancestor_with_component(entity, Measurement)
            assert measurement_id is not None

            if aruco_measurement.valid():
                print(f"Skipping measurement {entity}: {aruco_measurement.valid()}")
                continue

            marker = aruco_measurement.get_marker()
            camera = aruco_measurement.get_camera()

            if is_dynamic(marker) and not is_dynamic(camera):
                # Get the robot this marker is attached to
                robot_id = find_nearest_ancestor_with_component(marker, Franka)

                # Check we have a joint measurement associated with this robot
                joint_measurement_id = find_child_with_component(measurement_id, JointMeasurement, predicate=lambda id, c: c.robot_id == robot_id)
                if joint_measurement_id is None:
                    print(f"No joint measurement found for {marker} attached to {robot_id}")
                    continue

                for i in range(4):
                    # For every corner
                    pass
                
                camera_transform = esper.component_for_entity(camera, Transform)
                X_WC = camera_transform.get_X_WT()

                camera = sf.PosedCamera(pose=to_sym_pose(X_WC, compiled=True), calibration=intrinsics)
                # serial = m0["serial"]
                # point2D = sf.V2(m0["point2D"].tolist())
                # P_MP = sf.V3(m0["P_MP"].tolist())
                # marker_id = int(m0["marker_id"])
                # camera_mount = m0["mount"]
                # corner_index = m0["corner_index"]
                # capture_id = m0["capture_id"]
                # marker_mount = m0["marker_mount"]
            

                # initial_values[f"p2D_{i}"] = point2D
                # initial_values[f"P_MPs_{marker_id}_{corner_index}"] = P_MP
                # initial_values[f"X_BE_{capture_id}"] = to_sym_pose(m0["X_BE"])

                # factor = Factor(
                #     residual=eye_to_hand_residual,
                #     keys=[
                #         f"p2D_{i}", f"P_MPs_{marker_id}_{corner_index}", f"K_{serial}",f"X_BE_{capture_id}", f"X_EM_{marker_id}", f"X_BC_{serial}", "epsilon"
                #     ]
                # )
                # eye_to_hand_factors.append(factor)
                # measurements_used.append(m0)



            else:
                print(f"Calibration only implemented for dynamic markers and static cameras. (Marker={marker}, Camera={camera})")

        

