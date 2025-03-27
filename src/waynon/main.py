# Copyright (c) 2025 Boston Dynamics AI Institute LLC. All rights reserved.

from pathlib import Path
from typing import Optional
import logging

import esper
import imgui_bundle.immapp.icons_fontawesome_6 as font_awesome
import marsoom
import pyglet
import trio
from trio_util import periodic
from imgui_bundle import imgui
from imgui_bundle import portable_file_dialogs as pfd
from pydantic import BaseModel

from waynon.components.camera import PinholeCamera
from waynon.components.scene_utils import create_empty_scene, load_scene, save_scene, export_calibration
from waynon.processors.realsense_manager import REALSENSE_MANAGER
from waynon.processors.render import RenderProcessor
from waynon.processors.robot import RobotProcessor
from waynon.processors.transforms import TransformProcessor
from waynon.viewmodels.property_viewer import PropertyViewModel
from waynon.viewmodels.scene_viewmodel import SceneViewModel
from waynon.viewmodels.viewer_2d_viewmodel import Viewer2DViewModel
from waynon.viewmodels.viewer_3d_viewmodel import Viewer3DViewModel
from waynon.utils.utils import LongTask

# set level
# logging.basicConfig(level=logging.INFO)



class Settings(BaseModel):
    path: Optional[Path] = Path("data/default")

    @staticmethod
    def try_load(path=Path("settings.json")):
        if path.exists():
            with open("settings.json", "r") as f:
                settings = Settings.model_validate_json(f.read())
        else:
            settings = Settings()
        return settings

    def save(self, path: Path = Path("settings.json")):
        with open(path, "w") as f:
            f.write(self.model_dump_json(indent=4))


class Window(marsoom.Window):
    def __init__(self, nursery: trio.Nursery, settings: Settings):
        super().__init__(caption="Waynon - Calibration Tool", docking=True)

        self.nursery = nursery
        self.settings = settings
        self._set_up_assets()

        self.property_viewmodel = PropertyViewModel(self.nursery)
        self.scene_viewmodel = SceneViewModel(self.nursery)
        self.viewer_3d_viewmodel = Viewer3DViewModel(self.nursery, self)
        self.viewer_2d_viewmodel = Viewer2DViewModel(self.nursery, self)

        self._open_dialog = None
        self._save_dialog = None
        self._export_dialog = None

        create_empty_scene()
        if settings.path:
            load_scene(self.settings.path)

        esper.add_processor(RobotProcessor())
        esper.add_processor(TransformProcessor())
        esper.add_processor(RenderProcessor())
        # esper.add_processor(REALSENSE_MANAGER)


    def _set_up_assets(self):
        work_path = Path(__file__).parent.parent.parent / "assets"
        font_path = work_path / "fonts" / "Font_Awesome_6_Free-Solid-900.otf"
        io = imgui.get_io()
        io.config_flags |= imgui.ConfigFlags_.nav_enable_keyboard.value

        font_size_pixel = 10.0
        font_cfg = imgui.ImFontConfig()
        font_cfg.merge_mode = True
        icons_range = [font_awesome.ICON_MIN_FA, font_awesome.ICON_MAX_FA, 0]
        io.fonts.add_font_from_file_ttf(
            filename=str(font_path),
            size_pixels=font_size_pixel,
            font_cfg=font_cfg,
            glyph_ranges_as_int_list=icons_range,
        )
        io.fonts.build()
        self.imgui_renderer.refresh_font_texture()
        pyglet.resource.path.append(str(work_path.absolute()))
        pyglet.resource.reindex()
        
        self.start_cameras = LongTask(
            self.nursery,
            "Start Cameras",
            REALSENSE_MANAGER.start_all_cameras,
        )

        self.stop_cameras = LongTask(
            self.nursery,
            "Stop Cameras",
            REALSENSE_MANAGER.stop_all_cameras,
        )

    def render(self):
        self._handle_keys()
        self._draw_menu_bar()
        self.property_viewmodel.draw()
        self.scene_viewmodel.draw()
        self.viewer_3d_viewmodel.draw()
        self.viewer_2d_viewmodel.draw()

    def _handle_keys(self):
        io = imgui.get_io()
        if io.key_ctrl and imgui.is_key_pressed(imgui.Key.s):
            self._save_scene()


    def _save_scene(self):
        if self.settings.path is not None and self.settings.path.exists():
            save_scene(self.settings.path)
        else:
            default_path = Path.cwd()
            self._save_dialog = pfd.save_file(
                "Save Scene", str(default_path), 
            )

    def _draw_menu_bar(self):
        if imgui.begin_main_menu_bar():
            if imgui.begin_menu("File", True):
                if imgui.menu_item_simple("New"):
                    create_empty_scene()
                if imgui.menu_item_simple("Open"):
                    default_path = self.settings.path.parent
                    if not default_path.exists():
                        default_path = Path.cwd()
                    self._open_dialog = pfd.select_folder(
                        "Open Scene", str(default_path), 
                    )

                if imgui.menu_item_simple("Save", "Ctrl+S"):
                    self._save_scene()

                if imgui.menu_item_simple("Save As"):
                    default_path = self.settings.path.parent
                    if not default_path.exists():
                        default_path = Path.cwd()
                    self._save_dialog = pfd.save_file(
                        "Save Scene", str(default_path), ["*.json"]
                    )
                
                if imgui.menu_item_simple("Export Calibration"):
                    default_path = self.settings.path.parent
                    if not default_path.exists():
                        default_path = Path.cwd()
                    self._export_dialog = pfd.save_file(
                        "Export Calibration", str(default_path), ["*.json"]
                    )

                imgui.end_menu()
            imgui.begin_disabled(REALSENSE_MANAGER.busy)
            if imgui.menu_item_simple("Connect All"):
                self.nursery.start_soon(REALSENSE_MANAGER.start_all_cameras)
            if imgui.menu_item_simple("Disconnect All"):
                self.nursery.start_soon(REALSENSE_MANAGER.stop_all_cameras)
            imgui.end_disabled()
            imgui.end_main_menu_bar()
        if self._export_dialog is not None and self._export_dialog.ready():
            result = self._export_dialog.result()
            if result:
                path = Path(result)
                self._export_dialog = None
                export_calibration(path)


        if self._open_dialog is not None and self._open_dialog.ready():
            result = self._open_dialog.result()
            if result:
                path = Path(result)
                load_scene(path)
                self.settings.path = path
                self.settings.save()
                self._open_dialog = None
        if self._save_dialog is not None and self._save_dialog.ready():
            result = self._save_dialog.result()
            if result:
                path = Path(result)
                if path.exists():
                    print("Already exists")
                else:
                    path.mkdir(parents=False, exist_ok=False)
                    save_scene(path)
                    self.settings.path = path
                    self.settings.save()
                    self._save_dialog = None


# ENTRY POINT
async def main_async():
    settings = Settings.try_load()
    REALSENSE_MANAGER.get_connected_serials()


    async def camera_loop():
        async for _ in periodic(1/30):
            REALSENSE_MANAGER.process()

    
    async def render_loop(window: marsoom.Window):
        async for _ in periodic(1/60):
            if window.should_exit():
                break
            esper.process()
            window.step()

    async with trio.open_nursery() as nursery:
        window = Window(nursery, settings=settings)
        nursery.start_soon(camera_loop)
        await render_loop(window)
        nursery.cancel_scope.cancel()

    REALSENSE_MANAGER.stop_all_cameras_sync()

    settings.save()


if __name__ == "__main__":
    trio.run(main_async)
