from typing import Tuple
import cv2.aruco as aruco
import numpy as np
import esper

from waynon.components.tree_utils import *

from .measurement_processor import MeasurementProcessor


class ArucoProcessor(MeasurementProcessor):
    async def run(self, detector_id: int, measurement_id: int):
        from waynon.components.aruco_detector import ArucoDetector, ArucoMeasurement
        from waynon.components.measurement import Measurement
        from waynon.components.image_measurement import ImageMeasurement
        from waynon.components.joint_measurement import JointMeasurement
        from waynon.components.aruco_marker import ArucoMarker
        from waynon.components.simple import Deletable

        assert esper.entity_exists(detector_id)
        assert esper.entity_exists(measurement_id)
        assert esper.has_component(detector_id, ArucoDetector)
        assert esper.has_component(measurement_id, Measurement)


        iid = find_child_with_component(measurement_id, ImageMeasurement)
        assert iid is not None, "Measurement must have an ImageMeasurement"

        delete_children(iid, lambda id, c: isinstance(c, ArucoMeasurement))

        detector = esper.component_for_entity(detector_id, ArucoDetector)
        image_measurement = esper.component_for_entity(iid, ImageMeasurement)

        image = image_measurement.get_image_u()
        res = detect_all_markers_in_image(image, detector.marker_dict)
        markers_in_system = {}
        for marker_entity_id, marker in esper.get_component(ArucoMarker):
            markers_in_system[marker.id] = marker_entity_id

        if res:
            pixels, ids_found = res
            for i, marker_id in enumerate(ids_found):
                marker_id = int(marker_id) # comes in as np.ndarray
                if marker_id not in markers_in_system:
                    print(f"Warning: Marker {marker_id} detected but not in system")
                    continue
                marker_entity_id = markers_in_system[marker_id]
                num_repeats = len(pixels[i])    
                if num_repeats != 1:
                    print(f"Warning: Found {num_repeats} markers with id {marker_id}")
                for j in range(num_repeats):
                    aruco_measurement = ArucoMeasurement(
                        camera_entity_id=image_measurement.camera_id,
                        marker_entity_id=marker_entity_id,
                        detector_entity_id=detector_id,
                        marker_id=marker_id,
                        marker_dict=detector.marker_dict,
                        pixels=pixels[i][j].tolist(),
                    )
                    create_entity(f"Aruco {marker_id}", iid, aruco_measurement, Deletable())


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
    parameters.cornerRefinementMethod = aruco.CORNER_REFINE_SUBPIX  
    detector = aruco.ArucoDetector(aruco_dict, parameters)
    marker_pixels, marker_ids, _ = detector.detectMarkers(img)

    return marker_pixels, marker_ids

ARUCO_PROCESSOR = ArucoProcessor()
