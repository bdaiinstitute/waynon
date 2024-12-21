from pathlib import Path
from typing import Optional

from pydantic import BaseModel
import trio
import warp as wp
import esper
import pyglet

import marsoom

from waynon.components.scene_utils import create_empty_scene, load_scene, save_scene 
from waynon.components.camera import Camera
from waynon.processors.camera import CameraManager
from waynon.processors.transforms import TransformProcessor
from waynon.processors.robot import RobotProcessor
from waynon.processors.render import RenderProcessor

from waynon.viewmodels.property_viewer import PropertyViewModel
from waynon.viewmodels.scene_viewmodel import SceneViewModel
from waynon.viewmodels.viewer_2d_viewmodel import Viewer2DViewModel
from waynon.viewmodels.viewer_3d_viewmodel import Viewer3DViewModel


class Settings(BaseModel):
    path: Optional[Path] = "default.json"   

    @staticmethod
    def try_load(path = Path("settings.json")):
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
        super().__init__(docking=True)
        self._set_up_assets()

        self.nursery = nursery  
        self.settings = settings

        self.property_viewmodel = PropertyViewModel(self.nursery)
        self.scene_viewmodel = SceneViewModel(self.nursery)
        self.viewer_3d_viewmodel = Viewer3DViewModel(self.nursery, self)
        self.viewer_2d_viewmodel = Viewer2DViewModel(self.nursery, self)


        create_empty_scene()
        load_scene()

        esper.add_processor(RobotProcessor())
        esper.add_processor(TransformProcessor())
        esper.add_processor(RenderProcessor())
    
    def _set_up_assets(self):
        work_path = Path(__file__).parent.parent.parent / "assets"
        pyglet.resource.path.append(str(work_path.absolute()))
        pyglet.resource.reindex()
    

    def draw(self):
        self.property_viewmodel.draw()
        self.scene_viewmodel.draw()
        self.viewer_3d_viewmodel.draw()
        self.viewer_2d_viewmodel.draw()


async def update_cameras(window: marsoom.Window):
    while not window.should_exit():
        for _, camera in esper.get_component(Camera):
            camera.update()
        await trio.sleep(1/30.0)

async def render_gui(window: marsoom.Window):
    while not window.should_exit():
        esper.process()
        window.step()
        await trio.sleep(1/60.0)


# ENTRY POINT
async def main_async():
    wp.init()
    settings = Settings.try_load()
    CameraManager.instance().get_connected_serials()
    
    async with trio.open_nursery() as nursery:
        window = Window(nursery, settings=settings)
        nursery.start_soon(update_cameras, window)  
        await render_gui(window)
        nursery.cancel_scope.cancel()
    CameraManager.instance().stop_all_cameras()

    
    settings.save()
    save_scene(settings.path)

if __name__ == '__main__':
    trio.run(main_async)