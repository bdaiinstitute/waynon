# Copyright (c) 2025 Boston Dynamics AI Institute LLC. All rights reserved.

import esper
import trio


import marsoom.texture
import marsoom

from imgui_bundle import imgui
from imgui_bundle import icons_fontawesome_6 as icons

from waynon.components.simple import Component
from waynon.processors.realsense_manager import REALSENSE_MANAGER
from waynon.utils.utils import COLORS

class RealsenseCamera(Component):
    serial: str = ""
    enable_depth: bool = False
    verbose: bool = False

    def model_post_init(self, __context):
        manager = REALSENSE_MANAGER
        if self.serial in manager.serials:
            manager.attach_camera(self.serial)
    

    def running(self):
        return REALSENSE_MANAGER.camera_started(self.serial) and REALSENSE_MANAGER.camera_ready(self.serial)
    
    def intrinsics(self):
        camera = REALSENSE_MANAGER.get_camera(self.serial)
        assert camera, "Camera not found"
        return camera.get_intrinsics()

    def depth_scale(self):
        camera = REALSENSE_MANAGER.get_camera(self.serial)
        assert camera, "Camera not found"
        return camera.get_depth_scale()
    
    def resolution(self):
        return REALSENSE_MANAGER.get_camera(self.serial).resolution
    
    def get_data(self):
        return REALSENSE_MANAGER.get_data(self.serial)
    
    def get_manager(self):
        return REALSENSE_MANAGER
    
    def draw_context(self, nursery, entity_id):
        c = esper.component_for_entity(entity_id, RealsenseCamera)
        disabled = REALSENSE_MANAGER.busy
        imgui.begin_disabled(disabled)
        if c.running():
            if imgui.menu_item_simple(f"{icons.ICON_FA_STOP} Stop"):
                nursery.start_soon(REALSENSE_MANAGER.stop_camera, entity_id)
        else:
            enabled =  c.serial in REALSENSE_MANAGER.cameras
            imgui.begin_disabled(not enabled)
            if imgui.menu_item_simple(f"{icons.ICON_FA_PLAY} Start"):
                nursery.start_soon(REALSENSE_MANAGER.start_camera, entity_id)
            imgui.end_disabled()
        imgui.end_disabled()
    
    def draw_property(self, nursery: trio.Nursery, e:int):
        imgui.separator_text("Realsense")
        c = esper.component_for_entity(e, RealsenseCamera)
        manager = c.get_manager()
        _, c.enable_depth = imgui.checkbox("Enable Depth", c.enable_depth)
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
                    imgui.text_colored(COLORS["RED"], serial)
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
                disabled = manager.busy
                imgui.begin_disabled(disabled)
                if not alive:
                    imgui.push_style_color(imgui.Col_.button, COLORS["GREEN"])
                    if imgui.button("Start", (imgui.get_content_region_avail().x, 40)):
                        nursery.start_soon(manager.start_camera, e)
                    imgui.pop_style_color()
                else:
                    imgui.push_style_color(imgui.Col_.button, COLORS["RED"])
                    if imgui.button("Stop", (imgui.get_content_region_avail().x, 40)):
                        nursery.start_soon(manager.stop_camera, e)
                    imgui.pop_style_color()
                imgui.end_disabled()
                if imgui.button("Detach", (imgui.get_content_region_avail().x, 20)):
                    manager.delete_camera(e)
                    self.serial = ""

            else:
                imgui.text("Serial not connected")
        imgui.spacing()

        imgui.label_text("Serial", c.serial)

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
        return 50
    
