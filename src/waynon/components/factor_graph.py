from typing import Optional 

import esper
from imgui_bundle import imgui

from waynon.components.component import Component
from waynon.utils.utils import COLORS


class FactorGraph(Component):
    iterations: int = 250
    enable_bold_updates: bool = False
    verbose: bool = False


    def get_manager(self):
        from waynon.solvers.factor_graph import FACTOR_GRAPH_SOLVER
        return FACTOR_GRAPH_SOLVER

    def property_order(self):
        return 200

    def draw_property(self, nursery, entity_id):
        imgui.separator_text("Factor Graph")
        imgui.spacing()
        imgui.push_style_color(imgui.Col_.button, COLORS["BLUE"])
        if imgui.button("Run", (imgui.get_content_region_avail().x, 40)):
            nursery.start_soon(self.get_manager().run, entity_id)
        imgui.spacing()
        imgui.pop_style_color()
        _, self.iterations = imgui.input_int("Iterations", self.iterations)
        _, self.enable_bold_updates = imgui.checkbox("Enable Bold Updates", self.enable_bold_updates)
        _, self.verbose = imgui.checkbox("Verbose", self.verbose)

class InitialValues(Component):
    pass

class Factors(Component):
    pass