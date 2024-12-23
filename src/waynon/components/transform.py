import numpy as np
import esper

from imgui_bundle import imgui

from waynon.components.component import Component
from waynon.components.node import Node

class Transform(Component):
    X_PT: list[float] = [1.0, 0.0, 0.0, 0.0, 
                         0.0, 1.0, 0.0, 0.0, 
                         0.0, 0.0, 1.0, 0.0, 
                         0.0, 0.0, 0.0, 1.0]
    locked: bool = False
    visible: bool = True
    modifiable: bool = True
    
    def model_post_init(self, __context):
        self._X_WT = [1.0, 0.0, 0.0, 0.0, 
                      0.0, 1.0, 0.0, 0.0, 
                      0.0, 0.0, 1.0, 0.0, 
                      0.0, 0.0, 0.0, 1.0]
        self._dirty = True
        self._parent_id: int = -1
        return super().model_post_init(__context)

    def get_X_PT(self) -> np.ndarray:
        return np.asarray(self.X_PT).reshape(4, 4)

    def set_X_PT(self, X_PT: np.ndarray):
        self.X_PT = X_PT.flatten().tolist()
        self._dirty = True
    
    def get_X_WT(self) -> np.ndarray:
        return np.asarray(self._X_WT).reshape(4, 4)
    
    def set_X_WT(self, X_WT: np.ndarray):
        X_WP = self.get_parent_X_WT()
        X_PW = np.linalg.inv(X_WP)
        X_PT = X_PW @ X_WT
        self.set_X_PT(X_PT)
    
    def get_parent_X_WT(self) -> np.ndarray:
        if self._parent_id == -1:
            return np.eye(4, dtype=np.float32)
        assert esper.has_component(self._parent_id, Transform)
        transform = esper.component_for_entity(self._parent_id, Transform)
        return transform.get_X_WT()
    
    def property_order(self):
        return 100
    
    def draw_property(self, nursery, entity_id:int):
        imgui.separator_text("Transform")
        _, self.visible = imgui.checkbox("Draw Frame", self.visible)
    
    def on_selected(self, nursery, entity_id, just_selected):
        if just_selected:
            if self.modifiable:
                esper.dispatch_event("modify_transform", entity_id) 

