# Copyright (c) 2025 Robotics and AI Institute LLC dba RAI Institute. All rights reserved.

import esper
import marsoom
import marsoom.texture
import numpy as np
from imgui_bundle import imgui
from pyglet import gl

from waynon.components.aruco_detector import ArucoDetector
from waynon.components.aruco_marker import ArucoMarker
from waynon.components.simple import Component
from waynon.components.transform import Transform
from waynon.detectors.aruco_processor import detect_all_markers_in_image
from waynon.processors.realsense_manager import RealsenseManager


class PinholeCamera(Component):
    # intrinsics
    fl_x: float = 500.0
    fl_y: float = 500.0
    cx: float = 640.0
    cy: float = 360.0

    # resolution
    width: int = 1280
    height: int = 720


    def K(self):
        return np.array(
            [[self.fl_x, 0.0, self.cx], [0.0, self.fl_y, self.cy], [0.0, 0.0, 1.0]],
            dtype=np.float32,
        )

    def get_texture(self):
        return self._texture


    def get_image_u(self):
        """Get the image as uint8 between 0 and 255"""
        return self._image_u

    def guess_position(self, camera_entity_id: int, marker_entity_id: int, guess_camera: bool = True):
        import cv2
        from scipy.spatial.transform import Rotation as R

        # get all markers
        assert esper.entity_exists(marker_entity_id)
        assert esper.has_components(marker_entity_id, ArucoMarker, Transform)
        assert esper.entity_exists(camera_entity_id)
        assert esper.has_components(camera_entity_id, PinholeCamera, Transform)

        marker = esper.component_for_entity(marker_entity_id, ArucoMarker)
        marker_transform = esper.component_for_entity(marker_entity_id, Transform)
        camera_transform = esper.component_for_entity(camera_entity_id, Transform)
        if self._image_u is None:
            print("No image to detect markers in")
            return

        marker_pixels, marker_ids = detect_all_markers_in_image(
            self._image_u, marker.marker_dict
        )
        if marker_ids is None:
            print("No markers found")
            return
        if marker.id not in marker_ids:
            print(f"Marker {marker.id} not found")
            return

        idx = np.where(marker_ids == marker.id)[0][0]
        all_pixels = marker_pixels[idx]
        if len(all_pixels) > 1:
            print(
                f"Warning: Found {len(all_pixels)} markers with id {marker.id}. Using first one"
            )

        pixels = all_pixels[0]
        p_MPs = marker.get_P_MC()
        distortion = np.zeros((5, 1))
        K = np.array(
            [[self.fl_x, 0, self.cx], [0, self.fl_y, self.cy], [0, 0, 1]],
            dtype=np.float32,
        )

        res, rvec, tvec = cv2.solvePnP(
            p_MPs, pixels, K, distortion, False, cv2.SOLVEPNP_IPPE_SQUARE
        )
        if not res:
            print("Failed to solve PnP")
            return
        r = R.from_rotvec(np.array(rvec).flatten())
        X_CM = np.eye(4)
        X_CM[:3, :3] = r.as_matrix()
        X_CM[:3, 3] = np.array(tvec).flatten()

        if guess_camera:
            X_WM = marker_transform.get_X_WT()
            X_WC = X_WM @ np.linalg.inv(X_CM)
            rot_x = R.from_rotvec([np.pi, 0, 0]).as_matrix()
            X_x = np.eye(4)
            X_x[:3, :3] = rot_x
            X_WC = X_WC @ X_x
            camera_transform.set_X_WT(X_WC)
        else:
            print("Guessing marker position")
            X_WC = camera_transform.get_X_WT()
            X_WC = X_WC @ np.array([[1, 0, 0, 0], [0, -1, 0, 0], [0, 0, -1, 0], [0, 0, 0, 1]]) # opencv standard
            X_WM = X_WC @ X_CM
            marker_transform.set_X_WT(X_WM)

    def update_image(self, image: np.ndarray, identifier: int = None):
        assert image.dtype == np.uint8, f"Image must be uint8, got {image.dtype}"
        # if self._image_u == image:
        #     return
        if identifier is not None:
            if self._identifier == identifier:
                return

            self._identifier = identifier

        self._image_u = image
        # image_float = image / 255.0
        # image_float = image_float.astype("float32")
        # self._image_f = image_float
        self._texture.copy_from_host(self._image_u)

    def model_post_init(self, __context):
        self._texture = marsoom.texture.Texture(1280, 720, fmt=gl.GL_BGR)
        self._guessing_camera = False
        self._image_u = None
        self._identifier = -1
        return super().model_post_init(__context)

    def draw_property(self, nursery, e: int):
        imgui.separator_text("Pinhole Camera")
        imgui.label_text("Resolution", f"{self.width}x{self.height}")
        imgui.label_text("Focal", f"{self.fl_x}, {self.fl_y}")
        imgui.label_text("Principal", f"{self.cx}, {self.cy}")

        imgui.spacing()

        markers = esper.get_component(ArucoMarker)
        if markers:
            _, self._guessing_camera = imgui.checkbox("Guessing Camera", self._guessing_camera)
            if self._guessing_camera:
                imgui.text_wrapped(
                    "Guess the position of the camera using one of the below markers"
                )
            else:
                imgui.text_wrapped("Guess the position of the marker below using one of the camera position")

            for marker_entity_id, marker in markers:
                if imgui.image_button(
                    f"guess_{marker_entity_id}", marker.get_texture().id, (50, 50)
                ):
                    self.guess_position(e, marker_entity_id, self._guessing_camera)
                imgui.same_line()
            imgui.new_line()

    def on_selected(self, nursery, entity_id, just_selected):
        if just_selected:
            esper.dispatch_event("image_viewer", entity_id)

    def property_order(self):
        return 200


class DepthCamera(Component):
    width: int = 1280
    height: int = 720
    # show_pointcloud: bool = False

    def model_post_init(self, __context):
        self._depth_image = None
        self._pc = marsoom.StructuredPointCloud(1280, 720)

    # def draw_property(self, nursery, entity_id):
    #     imgui.separator_text("Depth Camera")
    #     _, self.show_pointcloud = imgui.checkbox("Show Pointcloud", self.show_pointcloud)
    # #     imgui.text(f"Resolution: {self.width}x{self.height}")

    def property_order(self):
        return 150
