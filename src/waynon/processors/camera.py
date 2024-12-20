from typing import Dict
from multiprocessing.managers import SharedMemoryManager
from waynon.realsense.single_realsense import SingleRealsense

class CameraManager:
    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = CameraManager()
        return cls._instance

    def __init__(self):
        self.shm_manager = SharedMemoryManager()
        self.shm_manager.start()
        self.cameras: Dict[str, SingleRealsense] = {}
        self.serials = []
        self.resolution = (1280, 720)

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
    
    def get_image(self, serial: str):
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
    