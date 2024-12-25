from typing import Optional 

import esper
from imgui_bundle import imgui

from waynon.components.component import Component
from waynon.components.optimizable import Optimizable
from waynon.components.node import Node
from waynon.components.tree_utils import get_node
from waynon.utils.utils import COLORS


class FactorGraph(Component):
    iterations: int = 250
    enable_bold_updates: bool = False
    initial_lambda: float = 0.1
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
        _, self.initial_lambda = imgui.slider_float("Initial Lambda", self.initial_lambda, 0.0, 1.0)
        imgui.spacing()

        elements =  esper.get_component(Optimizable)
        if elements:
            imgui.spacing()
            imgui.separator()
            imgui.spacing()
            imgui.text_wrapped("Variables that are included in the optimization")
            flags = imgui.TableFlags_.resizable
            imgui.begin_table("Variables", 3, flags)
            imgui.table_setup_column("Name")
            imgui.table_setup_column("Optimize")
            imgui.table_setup_column("Use Measurements")
            imgui.table_headers_row()
            for optimizable_id, optimizable in elements:
                imgui.push_id(optimizable_id)
                node = get_node(optimizable_id)
                imgui.table_next_row()

                imgui.table_next_column()
                imgui.text(node.name)

                imgui.table_next_column()
                _, optimizable.optimize = imgui.checkbox("##Optimize", optimizable.optimize)

                imgui.table_next_column()
                _, optimizable.use_in_optimization = imgui.checkbox("##Use Measurements", optimizable.use_in_optimization)

                imgui.pop_id()
            imgui.end_table()
            imgui.spacing()


class InitialValues(Component):
    pass

class Factors(Component):
    pass