from imgui_bundle import imgui

from .camera import PinholeCamera
from .component import Component
from .robot import Robot
from .tree_utils import *


class Measurement(Component):

    def on_selected(self, nursery, entity_id, just_selected):
        from .image_measurement import ImageMeasurement
        from .joint_measurement import JointMeasurement

        joint_measurement_id = find_child_with_component(entity_id, JointMeasurement)
        image_measurement_id = find_child_with_component(entity_id, ImageMeasurement)
        if just_selected:
            if image_measurement_id:
                # Display the image
                esper.dispatch_event("image_viewer", image_measurement_id)

                # Set the image on the camera
                image_measurement = esper.component_for_entity(
                    image_measurement_id, ImageMeasurement
                )
                camera_entity_id = image_measurement.camera_id
                if esper.entity_exists(camera_entity_id):
                    # set its texture
                    camera = esper.try_component(camera_entity_id, PinholeCamera)
                    if camera:
                        camera.update_image(image_measurement.get_image_u())

            if joint_measurement_id:
                joint_measurement = esper.try_component(
                    joint_measurement_id, JointMeasurement
                )
                robot = esper.try_component(joint_measurement.robot_id, Robot)
                if robot:
                    robot.get_manager().set_q(joint_measurement.joint_values)
