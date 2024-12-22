import cv2.aruco as aruco

import esper

from imgui_bundle import imgui

from waynon.components.component import Component, ValidityResult
from waynon.components.camera import Camera
from waynon.components.tree_utils import try_component
from waynon.components.aruco_marker import ArucoMarker


class ArucoMeasurement(Component):
    detector_entity_id: int
    camera_entity_id: int
    marker_entity_id: int

    marker_id: int
    marker_dict: int
    pixels: list[list[float]]

    def get_camera(self):
        return try_component(self.camera_entity_id, Camera)
    
    def get_marker(self):
        return try_component(self.marker_entity_id, ArucoMarker)
    
    def valid(self):
        if self.get_camera() is None:
            return ValidityResult.invalid("Camera not found")
        if self.get_marker() is None:
            return ValidityResult.invalid("Marker not found")
        
        marker = self.get_marker()
        if marker.id != self.marker_id:
            return ValidityResult.invalid("Marker ID does not match")
        if marker.marker_dict != self.marker_dict:
            return ValidityResult.invalid("Marker Dict does not match")
        
        return ValidityResult.valid()

    def draw_property(self, nursery, entity_id):
        imgui.separator()
        imgui.text(f"Marker ID: {self.marker_id}")
        imgui.text(f"Dict: {self.marker_dict}")
        for i, pixel in enumerate(self.pixels):
            imgui.text(f"Corner {i}: {pixel}")


    def _fix_on_load(self, new_to_old_entity_ids):
        self.detector_entity_id = new_to_old_entity_ids[self.detector_entity_id]
        self.camera_entity_id = new_to_old_entity_ids[self.camera_entity_id]
        self.marker_entity_id = new_to_old_entity_ids[self.marker_entity_id]


