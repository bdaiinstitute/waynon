import esper

import marsoom.texture
import marsoom

from imgui_bundle import imgui

from waynon.components.simple import Component
from waynon.processors.realsense_manager import REALSENSE_MANAGER
from waynon.utils.utils import COLORS

class RealsenseCamera(Component):
    serial: str = ""
    enable_depth: bool = False
    verbose: bool = False

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
    
    def draw_context(self, nursery, entity_id):
        c = esper.component_for_entity(entity_id, RealsenseCamera)
        if c.running():
            if imgui.menu_item_simple("Stop"):
                REALSENSE_MANAGER.stop_camera(entity_id)
        else:
            enabled =  c.serial in REALSENSE_MANAGER.cameras
            imgui.begin_disabled(not enabled)
            if imgui.menu_item_simple("Start"):
                REALSENSE_MANAGER.start_camera(entity_id)
            imgui.end_disabled()
    
    def draw_property(self, nursery, e:int):
        imgui.separator_text("Realsense")
        c = esper.component_for_entity(e, RealsenseCamera)
        manager = c.get_manager()
        # _, c.enable_depth = imgui.checkbox("Enable Depth", c.enable_depth)
        # _, c.verbose = imgui.checkbox("Verbose", c.verbose)

        imgui.spacing()
        if not c.serial:
            _, c.serial = imgui.input_text("Serial", c.serial)
            imgui.spacing()
            imgui.text("No serial set - select one")
            imgui.spacing()
            serials = manager.serials
            for serial in serials:
                imgui.push_id(serial)
                if serial in manager.cameras:
                    imgui.text_colored(serial, COLORS["RED"])
                else:
                    imgui.text(serial)
                imgui.same_line(imgui.get_window_width() - 40)
                if imgui.small_button("Set"):
                    c.serial = serial
                imgui.pop_id()
        else:
            camera = manager.get_camera(c.serial)
            if camera:
                alive = manager.camera_started(c.serial)
                if not alive:
                    imgui.push_style_color(imgui.Col_.button, COLORS["GREEN"])
                    if imgui.button("Start", (imgui.get_content_region_avail().x, 40)):
                        manager.start_camera(e)
                    imgui.pop_style_color()
                else:
                    imgui.push_style_color(imgui.Col_.button, COLORS["RED"])
                    if imgui.button("Stop", (imgui.get_content_region_avail().x, 40)):
                        manager.stop_camera(e)
                    imgui.pop_style_color()
            else:
                imgui.text("Serial not connected")
        imgui.spacing()

        _, c.serial = imgui.input_text("Serial", c.serial)

        data = c.get_data()
        if data:
            if "depth" in data:
                imgui.label_text("Depth", f"{data['depth'].shape}")
            if "color" in data:
                imgui.label_text("Color", f"{data['color'].shape}")
            if "timestamp" in data:
                imgui.label_text("Timestamp", f"{data['timestamp']}")
            if "step_idx" in data:
                imgui.label_text("Step", f"{data['step_idx']}")
            if "camera_capture_timestamp" in data:
                imgui.label_text("Camera Capture Timestamp", f"{data['camera_capture_timestamp']}")
            if "camera_receive_timestamp" in data:
                imgui.label_text("Camera Receive Timestamp", f"{data['camera_receive_timestamp']}")
    @staticmethod 
    def default_name():
        return "Realsense"
    
    def property_order(self):
        return 200
    
