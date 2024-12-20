import cv2.aruco as aruco

from waynon.components.component import Component

class Marker(Component):
    id: int
    square_length: float
    marker_length: float
    marker_dict: int = aruco.DICT_4X4_50

