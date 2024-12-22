from typing import Optional 

import esper
from imgui_bundle import imgui

from waynon.components.component import Component


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
        imgui.separator()
        _, self.iterations = imgui.input_int("Iterations", self.iterations)
        _, self.enable_bold_updates = imgui.checkbox("Enable Bold Updates", self.enable_bold_updates)
        _, self.verbose = imgui.checkbox("Verbose", self.verbose)
        if imgui.button("Run"):
            nursery.start_soon(self.get_manager().run, entity_id)

class InitialValues(Component):
    pass

class Factors(Component):
    pass