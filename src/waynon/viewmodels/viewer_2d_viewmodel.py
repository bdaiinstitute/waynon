from pathlib import Path

from PIL import Image
import numpy as np

import trio
import esper

from imgui_bundle import imgui

import marsoom
import marsoom.texture

from waynon.components.tree_utils import *
from waynon.components.camera import Camera
from waynon.components.image_measurement import ImageMeasurement
from waynon.components.aruco_detector import ArucoMeasurement

class Viewer2DViewModel:
    def __init__(self, nursery: trio.Nursery, window: marsoom.Window):
        self.nursery = nursery  
        self.window = window
        self.viewer_2d = self.window.create_2D_viewer()
        self.local_texture = marsoom.texture.Texture(1280, 720, 3)
        self.current_entity_id = None
        esper.set_handler("image_viewer", self._on_image_viewer)
    
    def draw(self):
        imgui.begin("2D Viewer")
        self.viewer_2d.draw()
        self._draw_image_measurement()
        imgui.end()

    def _on_image_viewer(self, entity_id):
        if esper.entity_exists(entity_id):
            self.current_entity_id = entity_id
            if esper.has_component(entity_id, Camera):
                camera = esper.component_for_entity(entity_id, Camera)
                t = camera.get_texture()
                if t:
                    self.viewer_2d.set_texture(t)
            
            if esper.has_component(entity_id, ImageMeasurement):
                raw_measurement = esper.component_for_entity(entity_id, ImageMeasurement)
                image_path = raw_measurement.image_path
                if Path(image_path).exists():
                    image = Image.open(image_path)
                    image = np.array(image, dtype=np.uint8)
                    self.viewer_2d.set_texture(self.local_texture)
                    image = image.astype(np.float32) / 255.0
                    self.viewer_2d.update_image(image)
    
    def _draw_image_measurement(self):
        if self.current_entity_id is None or not esper.entity_exists(self.current_entity_id):
            return
        if not esper.has_component(self.current_entity_id, ImageMeasurement):
            return

        image_measurement = esper.component_for_entity(self.current_entity_id, ImageMeasurement)
        aruco_measurement_ids = find_children_with_component(self.current_entity_id, ArucoMeasurement)
        v = self.viewer_2d
        for aruco_measurement_id in aruco_measurement_ids:
            aruco_measurement = esper.component_for_entity(aruco_measurement_id, ArucoMeasurement)
            pixels = aruco_measurement.pixels
            v.polyline([*pixels, pixels[0]], color=(1, 0, 0, 1), thickness=2)
            for i, corner in enumerate(pixels):
                if v.circle(corner, color=(0, 1, 0, 1), thickness=1):
                    if imgui.is_mouse_down(0):
                        new_pos = v.get_mouse_position()
                        pixels[i][0] = float(new_pos[0])
                        pixels[i][1] = float(new_pos[1])


