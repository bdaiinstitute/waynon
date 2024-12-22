from PIL import Image
import esper
import trio

from imgui_bundle import imgui


from .tree_utils import *
from .component import Component
from .node import Node
from .pose_group import PoseGroup
from .camera import Camera
from .simple import Detectors, Detector
from .factor_graph import FactorGraph

class MeasurementGroup(Component):
    pass

class DataNode(Component):
    pass

class Solvers(Component):

    def draw_context(self, nursery, entity_id):
        imgui.separator()
        if imgui.menu_item_simple("Add Factor Graph Solver"):
            create_entity("Factor Graph", entity_id, FactorGraph())

class CollectorData(Component):
    group_blacklist: list[int] = []
    camera_blacklist: list[int] = []    

    def draw_context(self, nursery, entity_id):
        from waynon.components.scene_utils import create_aruco_detector, create_entity
        from waynon.components.tree_utils import find_child_with_component
        imgui.separator()
        if imgui.menu_item_simple("Add Aruco Detector"):
            detector_id = find_child_with_component(entity_id, Detectors)
            if detector_id is None:
                detector_id, _ = create_entity("Detectors", entity_id, Detectors())
            create_aruco_detector("Aruco Detector", detector_id)

    def property_order(self):
        return 100

    def draw_property(self, nursery, entity_id):
        draw_collector(nursery, entity_id)



def draw_collector(nursery: trio.Nursery, collector_id: int):
        from waynon.processors.collector import Collector
        from waynon.components.scene_utils import get_detectors
        from .scene_utils import get_world_id

        collector_data = esper.component_for_entity(collector_id, CollectorData)

        pose_group_ids = find_descendants_with_component(get_world_id(), PoseGroup)


        imgui.separator_text("Pose Groups")
        for group_id in pose_group_ids:
            node, group = esper.try_components(group_id, Node, PoseGroup)
            imgui.push_id(group_id)
            enabled = group_id not in collector_data.group_blacklist
            res, _ = imgui.checkbox(node.name, enabled)
            if res:
                if enabled:
                    collector_data.group_blacklist.append(group_id)
                else:
                    collector_data.group_blacklist.remove(group_id)
            imgui.pop_id()
        
        imgui.separator_text("Cameras")
        for entity, (node, camera) in esper.get_components(Node, Camera):
            imgui.push_id(entity)
            enabled = entity not in collector_data.camera_blacklist
            res, _ = imgui.checkbox(f"{node.name} ({camera.serial})", enabled)
            if res:
                if enabled:
                    collector_data.camera_blacklist.append(entity)
                else:
                    collector_data.camera_blacklist.remove(entity)
            imgui.pop_id()

        can_run = Collector.instance().can_run(collector_data)
        disabled = not can_run

        detector_ids = get_detectors(collector_id)
        if detector_ids:
            imgui.separator_text("Detectors")
            for detector_id in detector_ids:
                detector = component_for_entity_with_instance(detector_id, Detector)
                node = get_node(detector_id)
                imgui.push_id(detector_id)
                _, detector.enabled = imgui.checkbox(node.name, detector.enabled)
                imgui.pop_id()  

            
        imgui.begin_disabled(disabled)
        if imgui.button("Collect"):
            nursery.start_soon(Collector.instance().collect, collector_id)
        imgui.end_disabled()
        imgui.same_line()
        if imgui.button("Run Detectors"):
            nursery.start_soon(Collector.instance().run_detectors, collector_id)
