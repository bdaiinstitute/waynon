from typing import Tuple
import cv2.aruco as aruco
import numpy as np
import esper

from waynon.components.tree_utils import *

from .measurement_processor import MeasurementProcessor


class ArucoProcessor(MeasurementProcessor):
    async def run(self, detector_id: int, measurement_id: int):
        from waynon.components.aruco_detector import ArucoDetector, ArucoMeasurement
        from waynon.components.image_measurement import ImageMeasurement
        from waynon.components.simple import Deletable

        assert esper.entity_exists(detector_id)
        assert esper.entity_exists(measurement_id)
        assert esper.has_component(detector_id, ArucoDetector)
        assert esper.has_component(measurement_id, ImageMeasurement)

        detector = esper.component_for_entity(detector_id, ArucoDetector)
        measurement = esper.component_for_entity(measurement_id, ImageMeasurement)

        image = measurement.get_image_u()
        res = detect_all_markers_in_image(image, detector.marker_dict)

        if res:
            pixels, ids_found = res
            for i, marker_id in enumerate(ids_found):
                num_repeats = len(pixels[i])    
                if num_repeats != 1:
                    print(f"Warning: Found {num_repeats} markers with id {marker_id}")
                for j in range(num_repeats):
                    aruco_measurement = ArucoMeasurement(
                        detector_entity_id=detector_id,
                        marker_id=marker_id,
                        marker_dict=detector.marker_dict,
                        pixels=pixels[i][j].tolist(),
                    )
                    create_entity(f"Aruco {marker_id}", measurement_id, aruco_measurement, Deletable())


def detect_all_markers_in_image(img: np.ndarray, marker_dict = aruco.DICT_4X4_50) -> Tuple[np.ndarray, np.ndarray]:   
    """
    Example Return:
    ((array([[[459., 160.],
        [627., 166.],
        [622., 320.],
        [471., 318.]]], dtype=float32),), array([[3]], dtype=int32))
    """
    assert img.dtype == np.uint8

    aruco_dict = aruco.getPredefinedDictionary(marker_dict)
    parameters = aruco.DetectorParameters()
    detector = aruco.ArucoDetector(aruco_dict, parameters)
    marker_pixels, marker_ids, _ = detector.detectMarkers(img)

    return marker_pixels, marker_ids

ARUCO_PROCESSOR = ArucoProcessor()
