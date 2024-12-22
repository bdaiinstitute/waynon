from typing import Dict
import esper

from multiprocessing.managers import SharedMemoryManager
from waynon.realsense.single_realsense import SingleRealsense

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
    
    def start_camera(self, serial: str):
        assert serial in self.serials
        if serial not in self.cameras or not self.cameras[serial].is_alive():
            self.cameras[serial] = SingleRealsense(
                shm_manager=self.shm_manager,
                serial_number=serial,
                resolution=self.resolution,
                verbose=False
            )
        self.cameras[serial].start()
    
    def stop_camera(self, serial: str):
        assert serial in self.serials
        if serial in self.cameras:
            self.cameras[serial].stop()
    
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
        for entity, (camera, realsense) in esper.get_components(PinholeCamera, RealsenseCamera):
            if realsense.running():
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
                camera.update_image(rgb)


REALSENSE_MANAGER = RealsenseManager()