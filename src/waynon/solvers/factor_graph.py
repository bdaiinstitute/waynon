from typing import Tuple
import numpy as np
import symforce
symforce.set_epsilon_to_symbol()
from symforce.values import Values
import symforce.symbolic as sf
from symforce.opt.factor import Factor
from symforce.opt.optimizer import Optimizer
from symforce.opt.noise_models import DiagonalNoiseModel
import sym

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
    point2D: Tuple[float, float],
    p_MP_M: sf.V3, 
    K: sf.LinearCameraCal,
    X_BE: sf.Pose3,
    X_EM: sf.Pose3,
    X_BC: sf.Pose3,
    epsilon: sf.Scalar
) -> sf.V2:
    camera = sf.PosedCamera(
        pose=X_BC,
        calibration=K
    )
    p_MP_B = X_BE * X_EM * p_MP_M
    pixel, valid = camera.pixel_from_global_point(p_MP_B, epsilon=epsilon)
    error = pixel - point2D
    return error