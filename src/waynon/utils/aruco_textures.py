from typing import Dict
import cv2
import cv2.aruco as aruco
import marsoom.texture

class ArucoTextures:
    
    def __init__(self):
        self.textures: Dict[int, marsoom.texture.Texture] = {}
    
    def get_texture(self, marker_id: int, aruco_dict: int):
        if (marker_id, aruco_dict) not in self.textures:
            texture = marsoom.texture.Texture(1280, 720, 3)
            dictionary = aruco.getPredefinedDictionary(aruco_dict)
            marker_img = aruco.generateImageMarker(dictionary, int(marker_id), 256)
            marker_img = cv2.cvtColor(marker_img, cv2.COLOR_GRAY2RGB)
            marker_img = marker_img.astype("float32") / 255.0
            texture.copy_from_host(marker_img)
            self.textures[(marker_id, aruco_dict)] = texture

        return self.textures[(marker_id, aruco_dict)]

ARUCO_TEXTURES = ArucoTextures()    