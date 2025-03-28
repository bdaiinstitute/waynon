# Copyright (c) 2025 Boston Dynamics AI Institute LLC. All rights reserved.

from pickletools import optimize
from typing import Tuple

import esper
import numpy as np
import symforce
symforce.set_epsilon_to_symbol()
import sym
import sym.ops
import symforce.opt
import symforce.opt.factor
import symforce.opt.optimizer
import symforce.symbolic as sf
from symforce.opt.factor import Factor
from symforce.opt.noise_models import DiagonalNoiseModel
from symforce.opt.optimizer import Optimizer
from symforce.values import Values

from waynon.components.scene_utils import (get_world_id, is_dynamic,
                                           rotate_around_x)
from waynon.components.tree_utils import *

symforce.set_log_level("WARNING")


def to_sym_pose(X: np.ndarray, compiled=False):
    from scipy.spatial.transform import Rotation as R

    q = R.from_matrix(X[:3, :3]).as_quat()
    t = X[:3, 3]
    if not compiled:
        return sf.Pose3.from_storage([*q, *t])
    else:
        return sym.Pose3.from_storage([*q, *t])


def from_sym_pose(pose: sf.Pose3):
    from scipy.spatial.transform import Rotation as R

    q = pose.R.to_storage()
    t = pose.t
    r = R.from_quat(q)
    X = np.eye(4)
    X[:3, :3] = r.as_matrix()
    X[:3, 3] = t
    return X


def eye_to_hand_residual(
    point2D: sf.V2,
    p_MP_M: sf.V3,
    K: sf.LinearCameraCal,
    X_BE: sf.Pose3,  # robot
    X_EM: sf.Pose3,  # marker
    X_BC: sf.Pose3,  # camera opencv convention
    epsilon: sf.Scalar,
) -> sf.V2:
    camera = sf.PosedCamera(pose=X_BC, calibration=K)

    p_MP_B = X_BE * X_EM * p_MP_M
    pixel, valid = camera.pixel_from_global_point(p_MP_B, epsilon=epsilon)
    if not valid:
        return None
    error = pixel - point2D
    return error


class FactorGraphSolver:
    def __init__(self):
        self.factors = []

    async def run(self, factor_graph_id: int):
        from waynon.components.aruco_measurement import ArucoMeasurement
        from waynon.components.camera import PinholeCamera
        from waynon.components.factor_graph import FactorGraph
        from waynon.components.joint_measurement import JointMeasurement
        from waynon.components.measurement import Measurement
        from waynon.components.optimizable import Optimizable
        from waynon.components.robot import FrankaLink, Robot
        from waynon.components.transform import Transform

        assert esper.entity_exists(factor_graph_id)
        assert esper.has_component(factor_graph_id, FactorGraph)
        factor_graph = esper.component_for_entity(factor_graph_id, FactorGraph)

        initial_values = Values(epsilon=sf.numeric_epsilon)
        optimized_keys_to_entity_id = {}

        factors = []
        num_measurements = 0
        for aruco_measurement_id, aruco_measurement in esper.get_component(
            ArucoMeasurement
        ):
            # go up the graph to find holding measurement
            measurement_id = find_nearest_ancestor_with_component(
                aruco_measurement_id, Measurement
            )
            assert measurement_id is not None
            name = get_node(measurement_id).name
            # if name != "Left Camera 32" and name != "Left Camera 33":
            #     continue
            # if name != "Left Camera 32":
            #     continue

            valid = aruco_measurement.valid()
            if not valid:
                print(f"Skipping measurement {measurement_id}: {valid}")
                continue

            marker = aruco_measurement.get_marker()
            camera = aruco_measurement.get_camera()

            marker_entity_id = aruco_measurement.marker_entity_id
            camera_entity_id = aruco_measurement.camera_entity_id

            if is_dynamic(marker_entity_id) and not is_dynamic(camera_entity_id):
                # Get the robot this marker is attached to
                robot_id = find_nearest_ancestor_with_component(marker_entity_id, Robot)
                assert robot_id is not None

                robot = esper.component_for_entity(robot_id, Robot)

                # Check we have a joint measurement associated with this robot
                joint_measurement_id = find_child_with_component(
                    measurement_id,
                    JointMeasurement,
                    predicate=lambda id, c: c.robot_id == robot_id,
                )
                if joint_measurement_id is None:
                    print(
                        f"No joint measurement found for {marker} attached to {robot_id}"
                    )
                    continue

                joint_measurement = esper.component_for_entity(
                    joint_measurement_id, JointMeasurement
                )
                marker_transform = esper.component_for_entity(
                    marker_entity_id, Transform
                )
                camera_transform = esper.component_for_entity(
                    camera_entity_id, Transform
                )
                marker_optimizable = esper.component_for_entity(
                    marker_entity_id, Optimizable
                )
                camera_optimizable = esper.component_for_entity(
                    camera_entity_id, Optimizable
                )
                if not marker_optimizable.use_in_optimization:
                    print(f"Skipping measurements for Marker {marker}")
                    continue
                if not camera_optimizable.use_in_optimization:
                    print(f"Skipping measurements for Camera {camera}")
                    continue

                # "epsilon" some symforce thing
                epsilon_key = "epsilon"

                # Marker Pose (SE3) and initial guess (Optimized)
                marker_pose_key = f"O1_X_PM_{marker_entity_id}"
                initial_values[marker_pose_key] = to_sym_pose(
                    marker_transform.get_X_PT()
                )
                if marker_optimizable.optimize:
                    optimized_keys_to_entity_id[marker_pose_key] = (
                        marker_entity_id  # look up for later to get the results back
                    )

                # Camera Intrinsics (LinearCameraCal) and initial guess
                camera_intinsics_key = f"K_{camera_entity_id}"
                fl_x, fl_y = camera.fl_x, camera.fl_y
                cx, cy = camera.cx, camera.cy
                initial_values[camera_intinsics_key] = sf.LinearCameraCal(
                    focal_length=(fl_x, fl_y), principal_point=(cx, cy)
                )

                # Camera Pose (SE3) (Optimized)
                camera_pose_key = f"O0_X_WC_{camera_entity_id}"
                if camera_pose_key not in initial_values:
                    X_PT = camera_transform.get_X_PT().copy()
                    X_PT = rotate_around_x(X_PT)
                    initial_values[camera_pose_key] = to_sym_pose(X_PT)
                if camera_optimizable.optimize:
                    optimized_keys_to_entity_id[camera_pose_key] = camera_entity_id

                # Robot Pose
                # todo get link name to support putting marker on arbitrary link
                link_id = find_nearest_ancestor_with_component(
                    marker_entity_id, FrankaLink
                )
                if link_id is None:
                    print(f"No link found for {marker}.. This should not happen")
                    continue
                link = esper.component_for_entity(link_id, FrankaLink)
                link_key = link.link_name
                robot_pose_key = f"X_W{link_key}_{joint_measurement_id}"
                q = joint_measurement.joint_values
                X_WR = robot.get_manager().fk(q)[link_key]
                initial_values[robot_pose_key] = to_sym_pose(X_WR)

                # Now do every corner
                p_MC = marker.get_P_MC()
                for i in range(4):
                    num_measurements += 1
                    # Marker Point (3D)
                    marker_3D_point_key = f"p_MP_{i}_{marker_entity_id}"
                    initial_values[marker_3D_point_key] = sf.V3(p_MC[i].tolist())

                    # Pixel Measurment (2D)
                    pixel_measurement_key = (
                        f"pixel_{measurement_id}_{aruco_measurement_id}_{i}"
                    )
                    point = aruco_measurement.pixels[i]
                    initial_values[pixel_measurement_key] = sf.V2(point)

                    factor = Factor(
                        residual=eye_to_hand_residual,
                        keys=[
                            pixel_measurement_key,
                            marker_3D_point_key,
                            camera_intinsics_key,
                            robot_pose_key,
                            marker_pose_key,
                            camera_pose_key,
                            epsilon_key,
                        ],
                    )
                    factors.append(factor)

            else:
                print(
                    f"Calibration only implemented for dynamic markers and static cameras. (Marker={marker}, Camera={camera})"
                )

        if len(factors) == 0:
            print("No factors found")
            return
        
        optimized_keys = list(optimized_keys_to_entity_id.keys())
        optimized_keys.sort() # ORDER MATTERS FOR SOME REASON. DO NOT REMOVE!!!!!!!!!!
        print(optimized_keys)

        optimizer = Optimizer(
            factors=[*factors],
            optimized_keys=optimized_keys,
            debug_stats=True,
            params=Optimizer.Params(
                verbose=factor_graph.verbose,
                iterations=factor_graph.iterations,
                early_exit_min_reduction=1e-10,
                initial_lambda=factor_graph.initial_lambda,
                enable_bold_updates=factor_graph.enable_bold_updates,
            ),
        )

        result = optimizer.optimize(initial_values)
        print(result.status, result.error() / num_measurements)

        # dot_file = symforce.opt.factor.visualize_factors(factors, "factor_graph.dot")

        if result.status == Optimizer.Status.SUCCESS:
            optimized_values = result.optimized_values
            for key, entity_id in optimized_keys_to_entity_id.items():
                pose = from_sym_pose(optimized_values[key])
                if esper.has_component(entity_id, PinholeCamera):
                    pose = rotate_around_x(pose)
                transform = esper.component_for_entity(entity_id, Transform)
                transform.set_X_PT(pose)
        else:
            print("Optimization failed")


FACTOR_GRAPH_SOLVER = FactorGraphSolver()
