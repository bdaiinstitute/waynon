import numpy as np
import esper
import pyglet

from waynon.components.transform import Transform
from waynon.components.renderable import Mesh, ImageQuad, CameraWireframe, ArucoDrawable, StructuredPointCloud
from waynon.components.camera import PinholeCamera
from waynon.components.aruco_marker import ArucoMarker
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

        for entity, (transform, sc) in esper.get_components(Transform, StructuredPointCloud):
            X_WT = transform.get_X_WT()
            sc.set_X_WT(X_WT)

        for entity, (transform, marker, drawable) in esper.get_components(Transform, ArucoMarker, ArucoDrawable):
            drawable.set_marker_dict(marker.marker_dict)
            drawable.set_marker_size(marker.marker_length)
            drawable.set_marker_id(marker.id)
            matrix = transform.get_X_WT()
            drawable.set_X_WT(matrix)