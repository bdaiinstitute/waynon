import esper

import marsoom.texture
import marsoom

from imgui_bundle import imgui

from waynon.components.simple import Component
from waynon.processors.camera import CameraManager

class Camera(Component):
    serial: str = ""

    def get_texture(self):
        return self._texture
    
    def get_image_f(self):
        """Get the image as float32 between 0 and 1"""
        return self._image_f
    
    def get_image_u(self):
        """Get the image as uint8 between 0 and 255"""
        return self._image_u
    
    def running(self):
        return CameraManager.instance().camera_ready(self.serial)
    
    def update(self):
        res = self.get_manager().get_image(self.serial)
        if res:
            if "color" in res:
                self._image_u = res["color"]
                img = res["color"] / 255.0
                img = img.astype("float32")
                self._image_f = img
                self._texture.copy_from_host(img)

    def model_post_init(self, __context):
        self._texture = marsoom.texture.Texture(1280, 720, 3)
        self._image_f = None
        self._image_u = None
        return super().model_post_init(__context)
    
    def get_manager(self):
        return CameraManager.instance()
    
    def draw_property(self, nursery, e:int):
        imgui.separator_text("Camera")
        c = esper.component_for_entity(e, Camera)
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
                imgui.text(f"Status: {"active" if alive else "inactive"}")
                if not alive:
                    if imgui.button("Start"):
                        manager.start_camera(c.serial)
                else:
                    if imgui.button("Stop"):
                        manager.stop_camera(c.serial)
                texture = c.get_texture()
                if texture:
                    w = min(imgui.get_content_region_avail().x, 500)
                    h = w * texture.height // texture.width
                    imgui.image(texture.id, image_size=(w, h))
            else:
                imgui.text("Serial not connected")
    
