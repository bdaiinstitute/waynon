# Copyright (c) 2025 Boston Dynamics AI Institute LLC. All rights reserved.

from pathlib import Path

import esper
import marsoom
import marsoom.texture
import numpy as np
import trio
from imgui_bundle import imgui
from PIL import Image
import pyglet

from waynon.components.aruco_marker import ArucoMarker
from waynon.components.aruco_measurement import ArucoMeasurement
from waynon.components.camera import PinholeCamera
from waynon.components.image_measurement import ImageMeasurement
from waynon.components.measurement import Measurement
from waynon.components.scene_utils import get_relative_transform_X_TS, rotate_around_x, get_data_path
from waynon.components.transform import Transform
from waynon.components.tree_utils import *


class Viewer2DViewModel:
    def __init__(self, nursery: trio.Nursery, window: marsoom.Window):
        self.nursery = nursery
        self.window = window
        self.viewer_2d = self.window.create_2D_viewer()
        self.local_texture = marsoom.texture.Texture(1280, 720)
        self.current_entity_id = None
        esper.set_handler("image_viewer", self._on_image_viewer)

    def draw(self):

        imgui.begin("2D Viewer")
        # set texture to not repeat
        self.viewer_2d.draw()
        self._draw_image_measurement()
        imgui.end()

    def _on_image_viewer(self, entity_id):
        if esper.entity_exists(entity_id):
            if esper.has_component(entity_id, PinholeCamera):
                self.current_entity_id = entity_id
                camera = esper.component_for_entity(entity_id, PinholeCamera)
                t = camera.get_texture()
                if t:
                    self.viewer_2d.set_texture(t)

            if esper.has_component(entity_id, ImageMeasurement):
                self.current_entity_id = entity_id
                raw_measurement = esper.component_for_entity(
                    entity_id, ImageMeasurement
                )
                print(get_data_path())
                image_path = get_data_path() / raw_measurement.image_path
                print(image_path)
                if Path(image_path).exists():
                    image = Image.open(image_path)
                    image = np.array(image, dtype=np.uint8)
                    self.viewer_2d.set_texture(self.local_texture)
                    image = image.astype(np.float32) / 255.0
                    self.viewer_2d.update_image(image)

    def _draw_image_measurement(self):
        if self.current_entity_id is None or not esper.entity_exists(
            self.current_entity_id
        ):
            return
        if not esper.has_component(self.current_entity_id, ImageMeasurement):
            return

        image_measurement = esper.component_for_entity(
            self.current_entity_id, ImageMeasurement
        )
        aruco_measurement_ids = find_children_with_component(
            self.current_entity_id, ArucoMeasurement
        )
        v = self.viewer_2d
        for aruco_measurement_id in aruco_measurement_ids:
            aruco_measurement = esper.component_for_entity(
                aruco_measurement_id, ArucoMeasurement
            )
            pixels = aruco_measurement.pixels
            v.polyline([*pixels, pixels[0]], color=(1, 0, 0, 1), thickness=2)
            for i, corner in enumerate(pixels):
                if v.circle(corner, color=(0, 1, 0, 1), thickness=1):
                    if imgui.is_mouse_down(0):
                        new_pos = v.get_mouse_position()
                        pixels[i][0] = float(new_pos[0])
                        pixels[i][1] = float(new_pos[1])

            marker_entity_id = aruco_measurement.marker_entity_id
            camera_entity_id = aruco_measurement.camera_entity_id
            camera = esper.try_component(camera_entity_id, PinholeCamera)
            X_MC = get_relative_transform_X_TS(
                source_entity=camera_entity_id, target_entity=marker_entity_id
            )
            X_MC = rotate_around_x(X_MC)  # convert to opencv
            X_CM = np.linalg.inv(X_MC)
            marker = esper.try_component(marker_entity_id, ArucoMarker)

            p_MF = marker.get_P_MC()
            p_CF = X_CM[:3, :3] @ p_MF.T + X_CM[:3, 3:]
            projected_CF = camera.K() @ p_CF  # (N, 3)
            projected_CF = projected_CF[:2, :] / projected_CF[2:, :]

            for i, corner in enumerate(projected_CF.T):
                v.circle(corner, color=(0, 0, 1, 1), thickness=4)
