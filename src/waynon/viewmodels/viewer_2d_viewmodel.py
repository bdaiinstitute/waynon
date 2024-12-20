from pathlib import Path

from PIL import Image
import numpy as np

import trio
import esper

from imgui_bundle import imgui

import marsoom
import marsoom.texture

from waynon.components.camera import Camera
from waynon.components.raw_measurement import RawMeasurement

class Viewer2DViewModel:
    def __init__(self, nursery: trio.Nursery, window: marsoom.Window):
        self.nursery = nursery  
        self.window = window
        self.viewer_2d = self.window.create_2D_viewer()
        self.local_texture = marsoom.texture.Texture(1280, 720, 3)
        esper.set_handler("image_viewer", self._on_image_viewer)
    
    def draw(self):
        imgui.begin("2D Viewer")
        self.viewer_2d.draw()
        imgui.end()

    def _on_image_viewer(self, entity_id):
        if esper.entity_exists(entity_id):
            if esper.has_component(entity_id, Camera):
                camera = esper.component_for_entity(entity_id, Camera)
                t = camera.get_texture()
                if t:
                    self.viewer_2d.set_texture(t)
            
            if esper.has_component(entity_id, RawMeasurement):
                raw_measurement = esper.component_for_entity(entity_id, RawMeasurement)
                image_path = raw_measurement.image_path
                if Path(image_path).exists():
                    image = Image.open(image_path)
                    image = np.array(image, dtype=np.uint8)
                    self.viewer_2d.set_texture(self.local_texture)
                    image = image.astype(np.float32) / 255.0
                    self.viewer_2d.update_image(image)
