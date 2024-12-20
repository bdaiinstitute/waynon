import cv2.aruco as aruco

from imgui_bundle import imgui

from waynon.components.component import Component

class ArucoDetector(Component):
    enabled: bool = True
    marker_dict: int = aruco.DICT_4X4_50

    def draw_property(self, nursery, entity_id):
        imgui.separator()
        _, self.enabled = imgui.checkbox("Enabled", self.enabled)
        _, self.marker_dict = imgui.combo("Marker Dictionary", self.marker_dict, ["DICT_4X4_50", "DICT_5X5_50", "DICT_6X6_50", "DICT_7X7_50", "DICT_ARUCO_ORIGINAL", "DICT_APRILTAG_16h5", "DICT_APRILTAG_25h9", "DICT_APRILTAG_36h10", "DICT_APRILTAG_36h11"])
    
    def property_order(self):
        return 100
