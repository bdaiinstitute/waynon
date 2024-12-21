import numpy as np
import esper

from waynon.components.node import Node
from waynon.components.transform import Transform
from waynon.components.renderable import Mesh, ImageQuad
from waynon.components.aruco_marker import ArucoMarker
from waynon.components.scene_utils import get_world_id
from waynon.utils.aruco_textures import ARUCO_TEXTURES
import pyglet

class RenderProcessor(esper.Processor):

    def process(self):        
        for entity, (transform, mesh) in esper.get_components(Transform, Mesh):
            matrix = transform.get_X_WT()
            mesh.set_X_WT(matrix)

        for entity, (transform, quad) in esper.get_components(Transform, ImageQuad):
            matrix = transform.get_X_WT()
            quad.set_X_WT(matrix)

        for entity, (marker, quad) in esper.get_components(ArucoMarker, ImageQuad):
            tid = ARUCO_TEXTURES.get_texture(marker.id, marker.marker_dict).id
            quad.set_texture(tid)