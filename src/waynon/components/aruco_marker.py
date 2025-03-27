# Copyright (c) 2025 Boston Dynamics AI Institute LLC. All rights reserved.

import cv2.aruco as aruco
import numpy as np
from imgui_bundle import imgui

from waynon.components.component import Component
from waynon.utils.aruco_textures import ARUCO_TEXTURES

aruco_dict_names = [
    "4X4_50",
    "4X4_100",
    "4X4_250",
    "4X4_1000",
    "5X5_50",
    "5X5_100",
    "5X5_250",
    "5X5_1000",
    "6X6_50",
    "6X6_100",
    "6X6_250",
    "6X6_1000",
    "7X7_50",
    "7X7_100",
    "7X7_250",
    "7X7_1000",
    "ARUCO_ORIGINAL",
    "APRILTAG_16h5",
    "APRILTAG_16H5",
    "APRILTAG_25h9",
    "APRILTAG_25H9",
    "APRILTAG_36h10",
    "APRILTAG_36H10",
    "APRILTAG_36h11",
    "APRILTAG_36H11",
    "ARUCO_MIP_36h12",
    "ARUCO_MIP_36H12",
]
aruco_dict_values = [
    aruco.DICT_4X4_50,
    aruco.DICT_4X4_100,
    aruco.DICT_4X4_250,
    aruco.DICT_4X4_1000,
    aruco.DICT_5X5_50,
    aruco.DICT_5X5_100,
    aruco.DICT_5X5_250,
    aruco.DICT_5X5_1000,
    aruco.DICT_6X6_50,
    aruco.DICT_6X6_100,
    aruco.DICT_6X6_250,
    aruco.DICT_6X6_1000,
    aruco.DICT_7X7_50,
    aruco.DICT_7X7_100,
    aruco.DICT_7X7_250,
    aruco.DICT_7X7_1000,
    aruco.DICT_ARUCO_ORIGINAL,
    aruco.DICT_APRILTAG_16h5,
    aruco.DICT_APRILTAG_16H5,
    aruco.DICT_APRILTAG_25h9,
    aruco.DICT_APRILTAG_25H9,
    aruco.DICT_APRILTAG_36h10,
    aruco.DICT_APRILTAG_36H10,
    aruco.DICT_APRILTAG_36h11,
    aruco.DICT_APRILTAG_36H11,
    aruco.DICT_ARUCO_MIP_36h12,
    aruco.DICT_ARUCO_MIP_36H12,
]


class ArucoMarker(Component):
    id: int = 1
    marker_length: float = 0.07
    marker_dict: int = aruco.DICT_4X4_50

    def get_texture(self):
        return ARUCO_TEXTURES.get_texture(self.id, self.marker_dict)

    def draw_property(self, nursery, entity_id):
        imgui.push_id(entity_id)
        imgui.separator_text("Aruco Marker")
        t = ARUCO_TEXTURES.get_texture(self.id, self.marker_dict)
        width = imgui.get_content_region_avail().x
        max_width = 200
        width = min(width, max_width)
        imgui.image(t.id, (width, width))
        imgui.spacing()
        _, self.id = imgui.input_int("ID", self.id)
        self.id = min(max(0, self.id), 100)
        _, self.marker_length = imgui.input_float("Marker Length", self.marker_length)

        current_item = aruco_dict_values.index(self.marker_dict)
        if imgui.begin_combo("Dict", aruco_dict_names[current_item]):
            for i, (name, value) in enumerate(zip(aruco_dict_names, aruco_dict_values)):
                selected = current_item == i
                res, _ = imgui.selectable(name, selected)
                if res:
                    print(f"Selected {name}, {value}")
                    self.marker_dict = value
                if selected:
                    imgui.set_item_default_focus()
            imgui.end_combo()
        imgui.pop_id()

    def get_P_MC(self) -> np.ndarray:
        """Get the marker points in the marker coordinate system"""
        marker_size = self.marker_length
        marker_points = np.array(
            [
                [-marker_size / 2, marker_size / 2, 0.0],
                [marker_size / 2, marker_size / 2, 0.0],
                [marker_size / 2, -marker_size / 2, 0.0],
                [-marker_size / 2, -marker_size / 2, 0.0],
            ],
            dtype=np.float64,
        )
        return marker_points

    @staticmethod
    def default_name():
        return "Aruco"
