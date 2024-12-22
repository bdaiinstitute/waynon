import esper

import marsoom.texture
import marsoom

from imgui_bundle import imgui

from waynon.components.simple import Component
from waynon.processors.realsense_manager import REALSENSE_MANAGER

class RealsenseCamera(Component):
    serial: str = ""

    def running(self):
        return REALSENSE_MANAGER.camera_ready(self.serial)
    
    def intrinsics(self):
        camera = REALSENSE_MANAGER.get_camera(self.serial)
        assert camera, "Camera not found"
        return camera.get_intrinsics()
    
    def resolution(self):
        return REALSENSE_MANAGER.get_camera(self.serial).resolution
    
    def get_data(self):
        return REALSENSE_MANAGER.get_data(self.serial)
    
    def get_manager(self):
        return REALSENSE_MANAGER
    
    def draw_property(self, nursery, e:int):
        imgui.separator_text("Realsense")
        c = esper.component_for_entity(e, RealsenseCamera)
        manager = c.get_manager()
        _, c.serial = imgui.input_text("Serial", c.serial)
        if not c.serial:
            imgui.spacing()
            imgui.text("No serial set - select one")
            imgui.spacing()
            serials = manager.serials
            for serial in serials:
                imgui.push_id(serial)
                imgui.text(serial)
                imgui.same_line(imgui.get_window_width() - 40)
                if imgui.small_button("set"):
                    c.serial = serial
                imgui.pop_id()
        else:
            camera = manager.get_camera(c.serial)
            if camera:
                alive = manager.camera_started(c.serial)
                if alive:
                    imgui.text(f"Status: active")
                else:
                    imgui.text(f"Status: inactive")
                if not alive:
                    if imgui.button("Start"):
                        manager.start_camera(c.serial)
                else:
                    if imgui.button("Stop"):
                        manager.stop_camera(c.serial)
                # texture = c.get_texture()
                # if texture:
                #     w = min(imgui.get_content_region_avail().x, 500)
                #     h = w * texture.height // texture.width
                #     imgui.image(texture.id, image_size=(w, h))
            else:
                imgui.text("Serial not connected")
    @staticmethod 
    def default_name():
        return "Realsense"
    
