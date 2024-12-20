import cv2.aruco as aruco

from imgui_bundle import imgui

from waynon.components.component import Component
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

class ArucoMeasurement(Component):
    detector_entity_id: int
    marker_id: int
    marker_dict: int
    pixels: list[list[float]]

    def draw_property(self, nursery, entity_id):
        imgui.separator()
        imgui.text(f"Detector: {self.detector_entity_id}")
        imgui.text(f"Marker ID: {self.marker_id}")
        imgui.text(f"Dict: {self.marker_dict}")
        imgui.text(f"Pixels: {self.pixels}")


    def _fix_on_load(self, new_to_old_entity_ids):
        if self.detector_entity_id in new_to_old_entity_ids:
            self.detector_entity_id = new_to_old_entity_ids[self.detector_entity_id]
        else:
            print(f"Detector {self.detector_entity_id} not found")
