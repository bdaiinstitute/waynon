# Copyright (c) 2025 Boston Dynamics AI Institute LLC. All rights reserved.

from typing import Literal
import trio
import numpy as np
import pinocchio as pin

from imgui_bundle import imgui    
import panda_py


from waynon.utils.utils import ASSET_PATH, static, one_at_a_time
from waynon.components.component import Component

from waynon.processors.robot import FrankaManager, RobotManager
from waynon.utils.utils import COLORS


class Robot(Component):

    def set_manager(self, manager: RobotManager):
        self._manager = manager

    def get_manager(self) -> RobotManager | None:
        return self._manager

    def model_post_init(self, __context):
        self._manager = None

class Franka(Component):
    name: str = "noname"
    ip: str = "10.103.1.111"
    username: str = "admin"
    password: str = "Password!"

    @staticmethod
    def get_robot_links(robot_id):
        pass

    def model_post_init(self, __context):
        super().model_post_init(__context)
        self._manager = FrankaManager(self)

    def get_manager(self):
        return self._manager
    
    def draw_property(self, nursery: trio.Nursery, _):
        return draw_property(nursery=nursery, robot=self._manager)
    
    def property_order(self):
        return 200
    
    @staticmethod
    def default_name():
        return "Franka"

class FrankaLinks(Component):
    pass

class FrankaLink(Component):
    robot_id: int
    link_name: Literal[
        "panda_link0",
        "panda_link1",
        "panda_link2",
        "panda_link3",
        "panda_link4",
        "panda_link5",
        "panda_link6",
        "panda_link7",
        "panda_hand"
        ] 
    
    def _fix_on_load(self, new_to_old_entity_ids):
        self.robot_id = new_to_old_entity_ids[self.robot_id]


@static(busy = False, 
        cancel_scope = trio.CancelScope())
def draw_property(nursery: trio.Nursery, robot: FrankaManager):
    static = draw_property
    settings: Franka = robot.settings   

    imgui.separator_text("Franka Emika")

    async def connect_to_ip():
        static.cancel_scope.cancel()
        static.cancel_scope = trio.CancelScope()
        with static.cancel_scope:
            async with trio.open_nursery() as nursery:
                await robot.connect_to_ip(nursery, settings.ip, settings.username, settings.password)
    
    @one_at_a_time(static)
    async def disconnect():
        print("Disconnecting")
        static.cancel_scope.cancel()
        await robot.disconnect()

    if robot.connect_status == FrankaManager.ConnectionStatus.DISCONNECTED:
        imgui.push_style_color(imgui.Col_.button, COLORS["GREEN"])
        if imgui.button("Connect", size=(imgui.get_content_region_avail().x, 40)):
            nursery.start_soon(connect_to_ip)
        imgui.pop_style_color()
    else:
        imgui.push_style_color(imgui.Col_.button, COLORS["RED"])
        if imgui.button("Disconnect", size=(imgui.get_content_region_avail().x, 40)) and robot.connect_status == FrankaManager.ConnectionStatus.CONNECTED:
            nursery.start_soon(disconnect)
        imgui.pop_style_color()
    imgui.spacing()

    _, settings.ip = imgui.input_text("IP", settings.ip)
    _, settings.username = imgui.input_text("Username", settings.username)
    _, settings.password = imgui.input_text("Password", settings.password, flags=imgui.InputTextFlags_.password)
    imgui.label_text("Connection", robot.connect_status.value)
    imgui.label_text("Brakes", robot.brake_status.value)
    imgui.label_text("Mode", robot.operating_mode.value)

    @one_at_a_time(static)
    async def switch_mode():
        if robot.operating_mode == FrankaManager.OperatingMode.EXECUTION:
            await robot.desk.set_mode("programming")
        else:
            await robot.desk.set_mode("execution")
    
    @one_at_a_time(static)
    async def unlock_brakes():
        await robot.desk.unlock()
    
    @one_at_a_time(static)
    async def lock_brakes():
        await robot.desk.lock()

    @one_at_a_time(static)
    async def home():
        await robot.home()

    imgui.spacing()
    
    connected = robot.connect_status == FrankaManager.ConnectionStatus.CONNECTED
    if connected:
        imgui.separator()
        if robot.brake_status == FrankaManager.BrakeStatus.OPEN:
            if imgui.button("Lock"):
                nursery.start_soon(lock_brakes)
            imgui.same_line()
            if imgui.button("Mode"):
                nursery.start_soon(switch_mode)
        else:
            if imgui.button("Unlock"):
                nursery.start_soon(unlock_brakes)
        
        imgui.same_line()
        if imgui.button("Home"):
            nursery.start_soon(home)
        imgui.spacing()
        # imgui.text("Joints")
        # q = robot.q
        # if q is not None:
        #     for i, q_i in enumerate(q):
        #         imgui.text(f"q{i}: {q_i:.3f}")
    imgui.same_line()
