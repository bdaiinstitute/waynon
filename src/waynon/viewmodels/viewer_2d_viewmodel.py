import trio
import esper

from imgui_bundle import imgui

import marsoom

from waynon.components.camera import Camera

class Viewer2DViewModel:
    def __init__(self, nursery: trio.Nursery, window: marsoom.Window):
        self.nursery = nursery  
        self.window = window
        self.viewer_2d = self.window.create_2D_viewer()
    
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
