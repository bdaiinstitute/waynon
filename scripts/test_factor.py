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
from symforce.opt.optimizer import Optimizer
from symforce.values import Values


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


initial_values = Values()
eps = sf.numeric_epsilon
initial_values["eps"] = eps


K = sf.LinearCameraCal(
    focal_length=(642.669921875, 642.002746582031), principal_point=(655.603942871094, 370.888061523438)
)
K_key = "K_24"
initial_values[K_key] = K


X_WC = np.array([
 [ 0.61144978,  0.49068147, -0.62077439,  0.95448536],
 [ 0.77159995, -0.54362649,  0.33030865,  0.00440494],
 [-0.17539307, -0.68095666, -0.7110101 ,  0.36777744],
 [ 0.        ,  0.        ,  0.        ,  1.        ]])

X_WC = to_sym_pose(X_WC)

# X_WC = sf.Pose3(
#     sf.Rot3(
#         sf.Quaternion(xyz=sf.V3(0.846475979283113, 0.372804850824109, -0.235141774331901), w=-0.29866922449886724)), 
#         t=sf.V3(1.954485356807709, 0.00440494064241648, 0.367777436971664))
camera_key = "X_WCamera_24"
initial_values[camera_key] = X_WC

X_PMarker_1 = np.array([
 [ 0.00205235,  0.0356311 ,  0.99936291,  0.01850315],
 [-0.99995352,  0.00947177,  0.00171575,  0.03729681],
 [-0.00940464, -0.99932024,  0.03564885,  0.05048768],
 [ 0.        ,  0.        ,  0.        ,  1.        ]])

X_PMarker_1 = to_sym_pose(X_PMarker_1)
# X_PMarker_1 = sf.Pose3(sf.Rot3(sf.Quaternion(xyz=sf.V3(-0.489114447951239, 0.49289215136063, -0.505995191218143), w=0.5116573564374497)), t=sf.V3(0.0185031478297103, 0.0372968098897169, 0.0504876760349542))   
marker_1_key = "X_PM_21"
initial_values[marker_1_key] = X_PMarker_1

X_PMarker_2 = np.array([
 [ 0.01874839,  0.0017124 ,  0.99982317,  0.01944199],
 [ 0.00273942, -0.99999484,  0.00166175, -0.04381554],
 [ 0.99982048,  0.00270751, -0.01875332,  0.04926114],
 [ 0.        ,  0.        ,  0.        ,  1.        ]])

X_PMarker_2 = to_sym_pose(X_PMarker_2)
# X_PMarker_2 = sf.Pose3(sf.Rot3(sf.Quaternion(xyz = sf.V3(0.713704444180268, 0.00155940667004697, 0.700445144477117), w=0.00036631489587447195)), t=sf.V3(0.0194419853215462, -0.0438155354762162, 0.0492611449162438))
marker_2_key = "X_PM_65"
initial_values[marker_2_key] = X_PMarker_2

p_MP = sf.V3(-0.0295000001788139, 0.0295000001788139, 0.0)
initial_values["p_MP"] = p_MP


X_Whand_1 = np.array([
 [ 7.84064416e-01, -2.51986099e-01,  5.67226584e-01,  6.16351473e-01],
 [-2.04001255e-01, -9.67730818e-01, -1.47920763e-01,  4.86685121e-02],
 [ 5.86196622e-01,  2.64471708e-04, -8.10168779e-01,  2.86027012e-01],
 [ 0.00000000e+00,  0.00000000e+00,  0.00000000e+00,  1.00000000e+00]])
X_Whand_1 = to_sym_pose(X_Whand_1)
# X_Whand_1 = sf.Pose3(sf.Rot3(sf.Quaternion(xyz=sf.V3(0.943658308525011, -0.120803088735552, 0.305572259429198), w=0.03925818094359318)), t=sf.V3(0.616351473233307, 0.0486685120681392, 0.286027011788395))  
hand1_key = "X_Whand_87"
initial_values[hand1_key] = X_Whand_1

pixel_1_1 = sf.V2(130.762496948242, 161.024673461914)
pixel_1_1_key = "pixel_343"
initial_values[pixel_1_1_key] = pixel_1_1

pixel_1_2 = sf.V2(474.243072509766, 38.9922142028809)
pixel_1_2_key = "pixel_344"
initial_values[pixel_1_2_key] = pixel_1_2


X_Whand_2 = np.array([
 [ 0.78590493, -0.26157184,  0.56029778,  0.62405736],
 [-0.25369998, -0.96274388, -0.09359778,  0.09479096],
 [ 0.5639058 , -0.06858858, -0.82298594,  0.26222814],
 [ 0.        ,  0.        ,  0.        ,  1.        ]])

X_Whand_2 = to_sym_pose(X_Whand_2)

# X_Whand_2 = sf.Pose3(sf.Rot3(sf.Quaternion(xyz=sf.V3(0.944938456947157, -0.136324174767451, 0.297427726114313), w=0.006616622610469427)), t=sf.V3(0.624057359384263, 0.0947909630957727, 0.262228138815024))
hand2_key = "X_Whand_96"
initial_values[hand2_key] = X_Whand_2

pixel_2_1 = sf.V2(293.525634765625, 180.625991821289)
pixel_2_1_key = "pixel_346"
initial_values[pixel_2_1_key] = pixel_2_1

pixel_2_2 = sf.V2(582.009826660156, 49.0090980529785)
pixel_2_2_key = "pixel_347"
initial_values[pixel_2_2_key] = pixel_2_2


f1_1 = Factor(
    residual=eye_to_hand_residual,
    keys= [
        pixel_1_1_key,
        "p_MP",
        K_key,
        hand1_key,
        marker_1_key,
        camera_key,
        "eps"
    ]
) 

f1_2 = Factor(
    residual=eye_to_hand_residual,
    keys= [
        pixel_1_2_key,
        "p_MP",
        K_key,
        hand1_key,
        marker_2_key,
        camera_key,
        "eps"
    ]
) 

f2_1 = Factor(
    residual=eye_to_hand_residual,
    keys= [
        pixel_2_1_key,
        "p_MP",
        K_key,
        hand2_key,
        marker_1_key,
        camera_key,
        "eps"
    ]
)

f2_2 = Factor(
    residual=eye_to_hand_residual,
    keys= [
        pixel_2_2_key,
        "p_MP",
        K_key,
        hand2_key,
        marker_2_key,
        camera_key,
        "eps"
    ]
)




optimized_keys = [camera_key, marker_1_key, marker_2_key]

factors = [f1_1, f1_2, f2_1, f2_2]
optimizer = Optimizer(
    factors=factors,
    optimized_keys=["X_PM_21", "X_WCamera_24", "X_PM_65"], # DOES NOT WORK
    # optimized_keys=["X_WCamera_24", "X_PM_21", "X_PM_65"], # WORKS
    # optimized_keys=["X_PM_21", "X_PM_65", "X_WCamera_24"], # WORKS
    debug_stats=False,
    params=Optimizer.Params(
        verbose=True,
        iterations=100,
        initial_lambda=1.0,
        enable_bold_updates=True
    )
)

result = optimizer.optimize(
    initial_values
)
print(result.status)