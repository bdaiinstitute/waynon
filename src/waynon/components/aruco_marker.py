import cv2.aruco as aruco

from imgui_bundle import imgui

from waynon.components.component import Component
from waynon.utils.aruco_textures import ARUCO_TEXTURES

class ArucoMarker(Component):
    id: int = 1
    square_length: float = 0.09
    marker_length: float = 0.07
    marker_dict: int = aruco.DICT_4X4_50

    def draw_property(self, nursery, entity_id):
        imgui.separator()
        _, self.id = imgui.input_int("ID", self.id)
        self.id = min(max(0, self.id), 100)
        
        _, self.square_length = imgui.input_float("Square Length", self.square_length)
        _, self.marker_length = imgui.input_float("Marker Length", self.marker_length)
        _, self.marker_dict = imgui.input_int("Dict", self.marker_dict)
        t = ARUCO_TEXTURES.get_texture(self.id, self.marker_dict)
        width = min(100, t.width)
        imgui.image(t.id, (width, width))

