from pathlib import Path
from typing import Optional

import esper
import imgui_bundle.immapp.icons_fontawesome_6 as font_awesome
import marsoom
import pyglet
import trio
import warp as wp
from imgui_bundle import imgui
from imgui_bundle import portable_file_dialogs as pfd
from pydantic import BaseModel

from waynon.components.camera import PinholeCamera
from waynon.components.scene_utils import create_empty_scene, load_scene, save_scene
from waynon.processors.realsense_manager import REALSENSE_MANAGER
from waynon.processors.render import RenderProcessor
from waynon.processors.robot import RobotProcessor
from waynon.processors.transforms import TransformProcessor
from waynon.viewmodels.property_viewer import PropertyViewModel
from waynon.viewmodels.scene_viewmodel import SceneViewModel
from waynon.viewmodels.viewer_2d_viewmodel import Viewer2DViewModel
from waynon.viewmodels.viewer_3d_viewmodel import Viewer3DViewModel


class Settings(BaseModel):
    path: Optional[Path] = Path("default.json")

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
        self._set_up_assets()

        self.nursery = nursery
        self.settings = settings

        self.property_viewmodel = PropertyViewModel(self.nursery)
        self.scene_viewmodel = SceneViewModel(self.nursery)
        self.viewer_3d_viewmodel = Viewer3DViewModel(self.nursery, self)
        self.viewer_2d_viewmodel = Viewer2DViewModel(self.nursery, self)

        self._open_dialog = None
        self._save_dialog = None

        create_empty_scene()
        if settings.path:
            load_scene(self.settings.path)

        esper.add_processor(RobotProcessor())
        esper.add_processor(TransformProcessor())
        esper.add_processor(RenderProcessor())
        esper.add_processor(REALSENSE_MANAGER)

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

    def draw(self):
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
                "Save Scene", str(default_path), ["*.json"]
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
                    self._open_dialog = pfd.open_file(
                        "Open Scene", str(default_path), ["*.json"]
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

                imgui.end_menu()
            imgui.end_main_menu_bar()
        if self._open_dialog is not None and self._open_dialog.ready():
            result = self._open_dialog.result()
            if result:
                result = result[0]
            path = Path(result)
            load_scene(path)
            self.settings.path = path
            self.settings.save()
            self._open_dialog = None
        if self._save_dialog is not None and self._save_dialog.ready():
            result = self._save_dialog.result()
            if result:
                path = Path(result)
                save_scene(path)
                self.settings.path = path
                self.settings.save()
                self._save_dialog = None


async def render_gui(window: marsoom.Window):
    while not window.should_exit():
        esper.process()
        window.step()
        await trio.sleep(1 / 60.0)


# ENTRY POINT
async def main_async():
    wp.init()
    settings = Settings.try_load()
    REALSENSE_MANAGER.get_connected_serials()

    async with trio.open_nursery() as nursery:
        window = Window(nursery, settings=settings)
        await render_gui(window)
        nursery.cancel_scope.cancel()

    REALSENSE_MANAGER.stop_all_cameras()

    settings.save()


if __name__ == "__main__":
    trio.run(main_async)
