import pyglet
# Copyright (c) 2025 Robotics and AI Institute LLC dba RAI Institute. All rights reserved.

import numpy as np
import pinocchio as pin

import marsoom

from waynon.utils.utils import static, one_at_a_time, COLORS, ASSET_PATH

@static(model = None, data = None, last_q = None)
def fk(q: np.ndarray, gripper_width = 0.0) -> list[np.ndarray]: 
    assert len(q) == 7

    static = fk
    if static.model is None:
        urdf_path = ASSET_PATH / "robots" / "panda" / "panda.urdf"
        static.model = pin.buildModelFromUrdf(str(urdf_path))
        static.data = static.model.createData()

    q = np.append(q, [0.01, 0.01])
    d = static.data
    m = static.model

    if static.last_q is None or not np.allclose(static.last_q, q):
        pin.forwardKinematics(m, d, q)
        pin.updateFramePlacements(m, d)
        static.last_q = q

    res = [d.oMf[i].homogeneous for i in [
        m.getFrameId("panda_link0"),
        m.getFrameId("panda_link1"),
        m.getFrameId("panda_link2"),
        m.getFrameId("panda_link3"),
        m.getFrameId("panda_link4"),
        m.getFrameId("panda_link5"),
        m.getFrameId("panda_link6"),
        m.getFrameId("panda_link7"),
        m.getFrameId("panda_hand"),
        m.getFrameId("panda_leftfinger"),
        m.getFrameId("panda_rightfinger")]]
    return res

@static(models = None, batch = None)
def draw_robot(q, color=COLORS["PURPLE"]):
    static = draw_robot
    names = ["link0", "link1", "link2", "link3", "link4", "link5", "link6", "link7", "hand"]#, "finger", "finger"]
    if static.models is None:
        static.models = {}
        batch = pyglet.graphics.Batch()    
        for name in names:
            static.models[name] = pyglet.resource.model(f"robots/panda/meshes/{name}.stl", batch=batch)
        static.batch = batch

    batch = static.batch
    res = fk(q)
    for i, name in enumerate(names):
        static.models[name].matrix = pyglet.math.Mat4(res[i].T.flatten().tolist())
        static.models[name].color = color
    batch.draw()

@static(model = None, batch = None, shape=None)
def draw_axis(matrix):
    static = draw_axis
    if static.model is None:
        batch = pyglet.graphics.Batch()
        static.model = marsoom.Axes(batch=batch)
        static.shape = marsoom.Point(0, 0, 0, color=(255, 0, 0), batch=batch)
        static.batch = batch    

    m = static.model
    b = static.batch
    s = static.shape
    m.matrix = pyglet.math.Mat4(matrix.T.flatten().tolist())
    s.position = matrix[:3, 3].tolist()
    pyglet.gl.glPointSize(10)
    b.draw()    

@static(model = None, batch = None, shape=None)
def draw_wireframe(matrix):
    static = draw_wireframe
    if static.model is None:
        batch = pyglet.graphics.Batch()
        static.model = marsoom.CameraWireframe(batch=batch)
        static.shape = marsoom.Point(0, 0, 0, color=(255, 0, 0), batch=batch)
        static.batch = batch    

    m = static.model
    b = static.batch
    s = static.shape
    m.matrix = pyglet.math.Mat4(matrix.T.flatten().tolist())
    s.position = matrix[:3, 3].tolist()
    pyglet.gl.glPointSize(10)
    b.draw()    