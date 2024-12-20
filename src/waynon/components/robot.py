import trio
import numpy as np
import pinocchio as pin

from imgui_bundle import imgui    


from waynon.utils.utils import ASSET_PATH, static, one_at_a_time
from waynon.components.component import Component

from waynon.processors.robot import Robot


class RobotSettings(Component):
    name: str = "noname"
    ip: str = "10.103.1.111"
    username: str = "admin"
    password: str = "Password!"

    def model_post_init(self, __context):
        super().model_post_init(__context)
        self._manager = Robot(self)

    def get_manager(self):
        return self._manager
    
    def draw_property(self, nursery: trio.Nursery, _):
        return draw_property(nursery=nursery, robot=self._manager)
    
    def property_order(self):
        return 200


@static(busy = False, 
        cancel_scope = trio.CancelScope())
def draw_property(nursery: trio.Nursery, robot: Robot):
    static = draw_property
    settings: RobotSettings = robot.settings   

    imgui.separator()

    imgui.text(f"Connection: {robot.connect_status.value}")
    imgui.text(f"Brakes {robot.brake_status.value}")
    imgui.text(f"Mode: {robot.operating_mode.value}")

    imgui.separator()

    imgui.input_text("IP", settings.ip)
    _, settings.username = imgui.input_text("Username", settings.username)
    _, settings.password = imgui.input_text("Password", settings.password, flags=imgui.InputTextFlags_.password)


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

    if robot.connect_status == Robot.ConnectionStatus.DISCONNECTED:
        if imgui.button("Connect"):
            nursery.start_soon(connect_to_ip)
    else:
        if imgui.button("Disconnect") and robot.connect_status == Robot.ConnectionStatus.CONNECTED:
            nursery.start_soon(disconnect)
    
    @one_at_a_time(static)
    async def switch_mode():
        if robot.operating_mode == Robot.OperatingMode.EXECUTION:
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
    
    connected = robot.connect_status == Robot.ConnectionStatus.CONNECTED
    if connected:
        imgui.same_line()
        if robot.brake_status == Robot.BrakeStatus.OPEN:
            if imgui.button("Lock"):
                nursery.start_soon(lock_brakes)
            imgui.same_line()
            if imgui.button("Mode"):
                nursery.start_soon(switch_mode)
        elif robot.brake_status == Robot.BrakeStatus.CLOSED:   
            if imgui.button("Unlock"):
                nursery.start_soon(unlock_brakes)
        else:
            imgui.text("Brakes are moving")
        
        imgui.same_line()
        if imgui.button("Home"):
            nursery.start_soon(home)
        
        imgui.separator()
        imgui.text("Joints")
        q = robot.q
        if q is not None:
            for i, q_i in enumerate(q):
                imgui.text(f"q{i}: {q_i:.3f}")
    imgui.same_line()