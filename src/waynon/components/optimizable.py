from imgui_bundle import imgui
from waynon.components.component import Component

class Optimizable(Component):
    optimize: bool = True

    def draw_property(self, nursery, entity_id):
        imgui.separator()
        _, self.optimize = imgui.checkbox("Optimize", self.optimize)
    
    def property_order(self):
        return 100
