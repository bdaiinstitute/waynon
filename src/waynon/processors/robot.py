import enum
from typing import TYPE_CHECKING, Dict, Literal

import esper
import numpy as np
import panda_py
import pinocchio as pin
import trio

from panda_desk import Desk
from waynon.utils.utils import ASSET_PATH, COLORS

if TYPE_CHECKING:
    from waynon.components.robot import Franka, Robot


class RobotManager:

    def read_q(self) -> np.ndarray:
        raise NotImplementedError
    
    def set_offline_q(self, q: np.ndarray):
        raise NotImplementedError

    def fk(self, q: list[float]) -> Dict[str, np.ndarray]:
        # Returns a dictionary of link names to their transforms in base frame
        raise NotImplementedError

    def ready_to_move(self) -> bool:
        raise NotImplementedError

    async def move_to(self, q: np.ndarray):
        raise NotImplementedError


class FrankaManager(RobotManager):
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

    def __init__(self, settings: "Franka"):
        self.settings = settings
        self.desk = Desk()
        self.panda = None
        self.connect_status = FrankaManager.ConnectionStatus.DISCONNECTED
        self.brake_status = FrankaManager.BrakeStatus.UNKNOWN
        self.operating_mode = FrankaManager.OperatingMode.UNKNOWN
        self.offline_q = np.array(
            [0.0, -0.785, 0.0, -2.356, 0.0, 1.571, 0.785], dtype=np.float32
        )
        self._initialize_buttons()
        urdf_path = ASSET_PATH / "robots" / "panda" / "panda.urdf"
        assert ASSET_PATH.exists(), f"ASSET_PATH {ASSET_PATH} does not exist"
        assert urdf_path.exists(), f"urdf_path {urdf_path} does not exist"
        self._full_model = pin.buildModelFromUrdf(str(urdf_path))
        # self._reduced_model = pin.buildReducedModel(
        #     self._full_model, [8, 9], np.zeros(9))
        self._model_data = self._full_model.createData()

        self.last_transforms = self.fk(self.offline_q)

    async def connect_to_ip(
        self,
        nursery: trio.Nursery,
        ip: str,
        username: str,
        password: str,
        platform: str = "fr3",
    ):
        try:
            self.desk = Desk(ip, platform)
            self.panda = panda_py.Panda(self.settings.ip)
            self.connect_status = FrankaManager.ConnectionStatus.CONNECTING
            await self.desk.login(username, password)
            res = await self.desk.take_control(force=True)
            await self.desk.activate_fci()

        except Exception as e:
            print(f"Failed to connect to robot: {e}")
            self.connect_status = FrankaManager.ConnectionStatus.DISCONNECTED
            return False

        if not res:
            self.connect_status = FrankaManager.ConnectionStatus.DISCONNECTED
            return False

        self.connect_status = FrankaManager.ConnectionStatus.CONNECTED

        nursery.start_soon(self._read_brake_status)
        # nursery.start_soon(self._read_joint_status)
        nursery.start_soon(self._read_mode)
        nursery.start_soon(self._read_buttons)

    async def disconnect(self):
        assert self.desk is not None
        await self.desk.logout()
        self.connect_status = FrankaManager.ConnectionStatus.DISCONNECTED
        self.brake_status = FrankaManager.BrakeStatus.UNKNOWN
        self.operating_mode = FrankaManager.OperatingMode.UNKNOWN

    def fk(self, q: np.ndarray, gripper_width=0.0) -> list[np.ndarray]:
        assert len(q) == 7
        q = np.append(q, [0.01, 0.01])
        pin.forwardKinematics(self._full_model, self._model_data, q)
        pin.updateFramePlacements(self._full_model, self._model_data)

        links = [
            "panda_link0",
            "panda_link1",
            "panda_link2",
            "panda_link3",
            "panda_link4",
            "panda_link5",
            "panda_link6",
            "panda_link7",
            "panda_hand",
            "panda_leftfinger",
            "panda_rightfinger",
        ]
        prev_links = [None] + links[:-1]

        d = self._model_data
        frame_ids = [self._full_model.getFrameId(link) for link in links]
        oMi = {
            link: d.oMf[frame_id].homogeneous
            for link, frame_id in zip(links, frame_ids)
        }
        return oMi

    async def _read_brake_status(self):
        async with self.desk.system_status() as status:
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
                    self.brake_status = FrankaManager.BrakeStatus.OPENING
                if all([b == 3 for b in brake_status]):
                    self.brake_status = FrankaManager.BrakeStatus.OPEN
                if any([b == 5 for b in brake_status]):
                    self.brake_status = FrankaManager.BrakeStatus.CLOSING
                if all([b == 0 for b in brake_status]):
                    self.brake_status = FrankaManager.BrakeStatus.CLOSED

    # async def _read_joint_status(self):
    #     async with self.desk.robot_states() as state:
    #         async for s in state:
    #             if "jointAngles" in s:
    #                 self.q = np.asanyarray(s["jointAngles"])
    #             else:
    #                 print(f"Missing jointAngles in state: {s}")

    async def _read_mode(self):
        async with self.desk.general_system_status() as state:
            async for s in state:
                if "derived" in s and "operatingMode" in s["derived"]:
                    mode = s["derived"]["operatingMode"]
                    if mode == "Execution":
                        self.operating_mode = FrankaManager.OperatingMode.EXECUTION
                    elif mode == "Programming":
                        self.operating_mode = FrankaManager.OperatingMode.PROGRAMMING
                    else:
                        self.operating_mode = FrankaManager.OperatingMode.UNKNOWN
                else:
                    print(f"Missing operatingMode in state: {s}")

    async def _read_buttons(self):
        async with self.desk.button_events() as events:
            async for e in events:
                for button in self.buttons_down:
                    if button in e:
                        self.buttons_down[button]["down"] = e[button]

    def tick(self):
        self.last_transforms = self.fk(self.read_q())
        for button in self.buttons_down:
            if self.buttons_down[button]["down"]:
                self.buttons_down[button]["t"] += 1
                t = self.buttons_down[button]["t"]
            else:
                self.buttons_down[button]["t"] = 0

    def set_offline_q(self, q: np.ndarray):
        self.offline_q = q 

    def read_q(self):
        if self.connect_status == FrankaManager.ConnectionStatus.DISCONNECTED:
            return self.offline_q
        return self.panda.q

    def is_button_pressed(
        self, button: Literal["circle", "cross", "check", "up", "down", "left", "right"]
    ) -> bool:
        return self.buttons_down[button]["down"] and self.buttons_down[button]["t"] == 1

    def ready_to_move(self) -> bool:
        return (
            self.connect_status == FrankaManager.ConnectionStatus.CONNECTED
            and self.brake_status == FrankaManager.BrakeStatus.OPEN
        )

    async def home(self):
        assert self.connect_status == FrankaManager.ConnectionStatus.CONNECTED
        await self.panda.move_to_start()
        # return await trio.to_thread.run_sync(panda.move_to_start)

    async def move_to(self, q: np.ndarray):
        assert self.connect_status == FrankaManager.ConnectionStatus.CONNECTED
        await self.panda.movej(q)

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
            },
        }


class RobotProcessor(esper.Processor):
    def process(self):
        from waynon.components.node import Node
        from waynon.components.renderable import Mesh
        from waynon.components.robot import Franka, FrankaLink, Robot
        from waynon.components.transform import Transform

        for entity, (robot, franka) in esper.get_components(Robot, Franka):
            manager = franka.get_manager()
            robot.set_manager(manager)
            manager.tick()

        for entity, (node, link, transform, mesh) in esper.get_components(
            Node, FrankaLink, Transform, Mesh
        ):
            robot_manager = esper.component_for_entity(
                link.robot_id, Robot
            ).get_manager()
            X_BL = robot_manager.last_transforms[link.link_name]  # All relative to base
            transform.set_X_PT(X_BL)
            if robot_manager.ready_to_move():
                mesh.set_color(COLORS["GREEN"])
            else:
                mesh.set_color(COLORS["RED"])
