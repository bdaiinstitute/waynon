# Copyright (c) 2025 Boston Dynamics AI Institute LLC. All rights reserved.

import cv2.aruco as aruco

from imgui_bundle import imgui

from waynon.components.simple import Detector
from waynon.detectors.measurement_processor import MeasurementProcessor

class ArucoDetector(Detector):
    marker_dict: int = aruco.DICT_4X4_50

    def get_processor(self) -> MeasurementProcessor:
        from waynon.detectors.aruco_processor import ARUCO_PROCESSOR
        return ARUCO_PROCESSOR

    def draw_property(self, nursery, entity_id):
        super().draw_property(nursery, entity_id)
        imgui.separator()
        _, self.marker_dict = imgui.input_int("Dict", self.marker_dict) 
    
    def property_order(self):
        return 200

