import numpy as np
import esper

from waynon.components.node import Node
from waynon.components.transform import Transform
from waynon.components.renderable import Mesh, ImageQuad, CameraWireframe, ArucoDrawable
from waynon.components.camera import PinholeCamera
from waynon.components.aruco_marker import ArucoMarker
from waynon.components.scene_utils import get_world_id
from waynon.utils.aruco_textures import ARUCO_TEXTURES
import pyglet

class RenderProcessor(esper.Processor):

    def process(self):        
        for entity, (transform, drawable) in esper.get_components(Transform, Mesh):
            matrix = transform.get_X_WT()
            drawable.set_X_WT(matrix)

        for entity, (transform, drawable) in esper.get_components(Transform, ImageQuad):
            matrix = transform.get_X_WT()
            drawable.set_X_WT(matrix)

        for entity, (transform, camera, drawable) in esper.get_components(Transform, PinholeCamera, CameraWireframe):
            matrix = transform.get_X_WT()
            drawable.set_X_WT(matrix)
            drawable.update_intrinsics(camera.fl_x, camera.fl_y, camera.cx, camera.cy, camera.width, camera.height)
            texture = camera.get_texture()
            if texture is not None:
                drawable.set_texture_id(texture.id)

        for entity, (transform, marker, drawable) in esper.get_components(Transform, ArucoMarker, ArucoDrawable):
            drawable.set_marker_dict(marker.marker_dict)
            drawable.set_marker_size(marker.marker_length)
            drawable.set_marker_id(marker.id)
            matrix = transform.get_X_WT()
            drawable.set_X_WT(matrix)