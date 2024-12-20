from typing import TYPE_CHECKING
import enum

import numpy as np
import trio
import panda_py
import pinocchio as pin

from waynon.panda.desk import Desk
from waynon.utils.utils import ASSET_PATH

if TYPE_CHECKING:
    from waynon.components.robot import RobotSettings

class Robot:
    class ConnectionStatus(enum.Enum):
        DISCONNECTED = "disconnected"
        CONNECTING = "connecting"
        CONNECTED = "connected"
    
    class BrakeStatus(enum.Enum):
        CLOSED = "closed"
        OPENING = "opening"
        OPEN = "open"
        CLOSING = "closing"
        UNKNOWN = "unknown"
    
    class OperatingMode(enum.Enum):
        UNKNOWN = "unknown"
        EXECUTION = "execution"
        PROGRAMMING = "programming"

    def __init__(self, settings: "RobotSettings"):
        self.settings = settings
        self.desk = Desk()
        self.connect_status = Robot.ConnectionStatus.DISCONNECTED
        self.brake_status = Robot.BrakeStatus.UNKNOWN
        self.operating_mode = Robot.OperatingMode.UNKNOWN
        self.q = np.array([0.0, -0.785, 0.0, -2.356, 0.0, 1.571, 0.785], dtype=np.float32)
        self._initialize_buttons()
        urdf_path = ASSET_PATH / "robots" / "panda" / "panda.urdf"
        assert ASSET_PATH.exists(), f"ASSET_PATH {ASSET_PATH} does not exist"
        assert urdf_path.exists(), f"urdf_path {urdf_path} does not exist"
        self._full_model = pin.buildModelFromUrdf(str(urdf_path))
        self._reduced_model = pin.buildReducedModel(
            self._full_model, [8, 9], np.zeros(9))
        self._model_data = self._full_model.createData()
    
    async def connect_to_ip(self, nursery: trio.Nursery, ip: str, username: str, password: str, platform: str = "fr3"):
        try:
            self.desk = Desk(ip, platform)
            self.connect_status = Robot.ConnectionStatus.CONNECTING
            await self.desk.login(username, password)
            res = await self.desk.take_control(force=True)
            await self.desk.activate_fci()

        except Exception as e:
            print(f"Failed to connect to robot: {e}")
            self.connect_status = Robot.ConnectionStatus.DISCONNECTED
            return False

        if not res:
            self.connect_status = Robot.ConnectionStatus.DISCONNECTED
            return False

        self.connect_status = Robot.ConnectionStatus.CONNECTED
            
        nursery.start_soon(self._read_brake_status)
        nursery.start_soon(self._read_joint_status)
        nursery.start_soon(self._read_mode)
        nursery.start_soon(self._read_buttons)

    
    async def disconnect(self):
        assert self.desk is not None
        await self.desk.logout()
        self.connect_status = Robot.ConnectionStatus.DISCONNECTED
        self.brake_status = Robot.BrakeStatus.UNKNOWN
        self.operating_mode = Robot.OperatingMode.UNKNOWN
    
    def fk(self, q: np.ndarray, gripper_width = 0.0) -> list[np.ndarray]: 
        assert len(q) == 7
        q = np.append(q, [0.01, 0.01])
        pin.forwardKinematics(self._full_model, self._model_data, q)
        pin.updateFramePlacements(self._full_model, self._model_data)
        res = [self._model_data.oMf[i].homogeneous for i in [
            self._full_model.getFrameId("panda_link0"),
            self._full_model.getFrameId("panda_link1"),
            self._full_model.getFrameId("panda_link2"),
            self._full_model.getFrameId("panda_link3"),
            self._full_model.getFrameId("panda_link4"),
            self._full_model.getFrameId("panda_link5"),
            self._full_model.getFrameId("panda_link6"),
            self._full_model.getFrameId("panda_link7"),
            self._full_model.getFrameId("panda_hand"),
            self._full_model.getFrameId("panda_leftfinger"),
            self._full_model.getFrameId("panda_rightfinger")]]
        return res


    async def _read_brake_status(self):
        async with self.desk.system_status_generator() as status:
            async for s in status:
                # 0 is closed
                # 2 is opening
                # 3 is open
                # 5 is closing
                # if any is 2:
                if "jointStatus" not in s:
                    print(f"Missing jointStatus in state: {s}")
                    continue

                brake_status = [b for b in s["jointStatus"]]
                if any([b == 2 for b in brake_status]):
                    self.brake_status = Robot.BrakeStatus.OPENING
                if all([b == 3 for b in brake_status]):
                    self.brake_status = Robot.BrakeStatus.OPEN
                if any([b == 5 for b in brake_status]):
                    self.brake_status = Robot.BrakeStatus.CLOSING
                if all([b == 0 for b in brake_status]):
                    self.brake_status = Robot.BrakeStatus.CLOSED
            
    async def _read_joint_status(self):
        async with self.desk.system_state_generator() as state:
            async for s in state:
                if "jointAngles" in s:
                    self.q = np.asanyarray(s["jointAngles"])
                else:
                    print(f"Missing jointAngles in state: {s}")

    async def _read_mode(self):
        async with self.desk.general_system_status_generator() as state:
            async for s in state:
                if "derived" in s and "operatingMode" in s["derived"]:
                    mode = s["derived"]["operatingMode"]
                    if mode == "Execution":
                        self.operating_mode = Robot.OperatingMode.EXECUTION
                    elif mode == "Programming":
                        self.operating_mode = Robot.OperatingMode.PROGRAMMING
                    else:
                        self.operating_mode = Robot.OperatingMode.UNKNOWN
                else:
                    print(f"Missing operatingMode in state: {s}")
    
    async def _read_buttons(self):
        async with self.desk.events_generator() as events:
            async for e in events:
                for button in self.buttons_down:
                    if button in e:
                        self.buttons_down[button]["down"] = e[button]

    def tick(self):
        for button in self.buttons_down:
            if self.buttons_down[button]["down"]:
                self.buttons_down[button]["t"] += 1
            else:
                self.buttons_down[button]["t"] = 0
    
    def is_button_pressed(self, button: str) -> bool:
        return self.buttons_down[button]["down"] and self.buttons_down[button]["t"] == 0
    
    def ready_to_move(self) -> bool:
        return self.connect_status == Robot.ConnectionStatus.CONNECTED and self.brake_status == Robot.BrakeStatus.OPEN
    
    async def home(self):
        assert self.connect_status == Robot.ConnectionStatus.CONNECTED
        panda = panda_py.Panda(self.settings.ip)
        return await trio.to_thread.run_sync(panda.move_to_start)
    
    async def move_to(self, q: np.ndarray):
        assert self.connect_status == Robot.ConnectionStatus.CONNECTED
        panda = panda_py.Panda(self.settings.ip)
        return await trio.to_thread.run_sync(panda.move_to_joint_position, q)

    def _initialize_buttons(self):
        self.buttons_down = {
            "circle": {
                "down": False,
                "t": 0,
            },
            "cross": {
                "down": False,
                "t": 0,
            },
            "check": {
                "down": False,
                "t": 0,
            },
            "up": {
                "down": False,
                "t": 0,
            },
            "down": {
                "down": False,
                "t": 0,
            },
            "left": {
                "down": False,
                "t": 0,
            },
            "right": {
                "down": False,
                "t": 0,
            }
        }


