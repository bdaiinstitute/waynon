from imgui_bundle import imgui
from waynon.components.component import Component

class Optimizable(Component):
    optimize: bool = True
    use_in_optimization: bool = False

    def draw_property(self, nursery, entity_id):
        imgui.separator_text("Optimization")
        _, self.optimize = imgui.checkbox("Optimize", self.optimize)
        _, self.use_in_optimization = imgui.checkbox("Use Measurements", self.use_in_optimization)
    
    def property_order(self):
        return 500
