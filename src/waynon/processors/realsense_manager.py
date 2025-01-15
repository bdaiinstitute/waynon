from typing import Dict
import logging

import esper
import numpy as np

from multiprocessing.managers import SharedMemoryManager
from realsense.single_realsense import SingleRealsense


logger = logging.getLogger(__name__)

class RealsenseManager:

    def __init__(self):
        self.shm_manager = SharedMemoryManager()
        self.shm_manager.start()
        self.cameras: Dict[str, SingleRealsense] = {}
        self.serials = []
        self.resolution = (1280, 720)
    
    def get_intrinsics(self, serial: str):
        return self.get_camera(serial).get_intrinsics()    
    
    def get_connected_serials(self):
        self.serials =  SingleRealsense.get_connected_devices_serial()
    
    def start_camera(self, entity_id: int):
        from waynon.components.realsense_camera import RealsenseCamera
        assert esper.entity_exists(entity_id)
        assert esper.has_component(entity_id, RealsenseCamera)
        realsense_data = esper.component_for_entity(entity_id, RealsenseCamera)
        serial = realsense_data.serial
        enable_depth = realsense_data.enable_depth

        assert serial in self.serials
        if serial not in self.cameras or not self.cameras[serial].is_alive():
            self.cameras[serial] = SingleRealsense(
                shm_manager=self.shm_manager,
                serial_number=serial,
                resolution=self.resolution,
                enable_depth=enable_depth,
                verbose=realsense_data.verbose
            )
        if not self.cameras[serial].is_alive():
            self.cameras[serial].start()
    
    def delete_camera(self, entity_id: int):
        from waynon.components.realsense_camera import RealsenseCamera
        assert esper.entity_exists(entity_id)
        assert esper.has_component(entity_id, RealsenseCamera)
        realsense_data = esper.component_for_entity(entity_id, RealsenseCamera)
        serial = realsense_data.serial
        if serial in self.serials and serial in self.cameras:
            if self.cameras[serial].is_alive():
                self.cameras[serial].stop()
            del self.cameras[serial]
    
    def stop_camera(self, entity_id: int):
        from waynon.components.realsense_camera import RealsenseCamera
        assert esper.entity_exists(entity_id)
        assert esper.has_component(entity_id, RealsenseCamera)
        realsense_data = esper.component_for_entity(entity_id, RealsenseCamera)
        serial = realsense_data.serial
        assert serial in self.serials
        if serial in self.cameras:
            self.cameras[serial].stop()
    
    def attach_camera(self, serial: str):
        if serial in self.serials:
            self.cameras[serial] = SingleRealsense(
                shm_manager=self.shm_manager,
                serial_number=serial,
                resolution=self.resolution,
                verbose=False
            )
        else:
            print(f"Serial {serial} not found")

    
    def get_camera(self, serial: str):
        if serial in self.cameras:
            return self.cameras[serial]
        elif serial in self.serials:
            self.cameras[serial] = SingleRealsense(
                shm_manager=self.shm_manager,
                serial_number=serial,
                resolution=self.resolution,
                verbose=False
            )
            return self.cameras[serial]
        return None
    
    def get_data(self, serial: str):
        if serial in self.cameras:
            return self.cameras[serial].get()
        return None

    def camera_started(self, serial: str):
        if serial in self.cameras:
            return self.cameras[serial].is_alive()
        return False
    
    def camera_ready(self, serial: str):
        if serial in self.cameras:
            return self.cameras[serial].is_ready
        return False
    
    def start_all_cameras(self):
        from waynon.components.realsense_camera import RealsenseCamera
        for entity_id, _ in esper.get_component(RealsenseCamera):
            self.start_camera(entity_id)
        
    
    def stop_all_cameras(self):
        for serial in self.cameras:
            if self.cameras[serial].is_alive():
                self.cameras[serial].stop()
        self.cameras = {}
    
    def __del__(self):
        self.stop_all_cameras()
    
    def process(self):
        from waynon.components.realsense_camera import RealsenseCamera
        from waynon.components.camera import PinholeCamera
        from waynon.components.renderable import StructuredPointCloud
        for entity, (camera, realsense, pc) in esper.get_components(PinholeCamera, RealsenseCamera, StructuredPointCloud):
            if realsense.running():
                logger.info(f"Processing camera {entity}")
                K = realsense.intrinsics()
                camera.fl_x = K[0, 0]
                camera.fl_y = K[1, 1]
                camera.cx = K[0, 2]
                camera.cy = K[1, 2]

                resolution = realsense.resolution()
                camera.width = resolution[0]
                camera.height = resolution[1]

                data = realsense.get_data()
                rgb = data['color']
                identifier = data["timestamp"]
                camera.update_image(rgb, identifier=identifier)
                if pc.show_pointcloud and "depth" in data:
                    depth_scale = realsense.depth_scale()
                    pc.update_depth(data["depth"], identifier=identifier, depth_scale=depth_scale)
                    pc.update_intrinsics(camera.fl_x, camera.fl_y, camera.cx, camera.cy, camera.width, camera.height)
                    pc.set_texture_id(camera.get_texture().id)
            else:
                pass


REALSENSE_MANAGER = RealsenseManager()