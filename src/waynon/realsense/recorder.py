from pathlib import Path
import numpy as np
import subprocess as sp
import shlex

class VideoRecorder:
    hevc_nvenc_counter: int = 0
    hevc_nvenc_limit: int = 7 # nvidia cards have a limit of 3 or 5 nvenc sessions. This can be patched to inf https://github.com/keylase/nvidia-patch
    def __init__(self, 
                 width: int, 
                 height: int,
                 recorder_type: str = "color", 
                 depth_scale: float = 6.0, 
                 fps: int = 30):
        self.writer = None
        self.recorder_type = recorder_type
        self.fps = fps
        self.width = width
        self.height = height
        self.depth_scale = depth_scale
        self.frame_counter = 0
        self.loglevel = "-loglevel info"
        # self.loglevel = "-loglevel quiet"
        # self.x265_params = '-x265-params "lossless=1 -p=ultrafast -tune=zerolatency"'
        # self.x265_params = '-x265-params "lossless=1 -tune=zerolatency"'
        self.x265_params = '-preset lossless'
        # self.x265_params = '-x265-params -lossless=1'
        if self.recorder_type == "color":
            if VideoRecorder.hevc_nvenc_counter >= VideoRecorder.hevc_nvenc_limit:
                VideoRecorder.hevc_nvenc_counter += 1
                encoder = "hevc_nvenc"
                print(f"Using nvenc encoder {VideoRecorder.hevc_nvenc_counter}")
                # encoder = "hevc"
            else:
                encoder = "hevc_nvenc"
                # encoder = "hevc"
            # encoder = "hevc" # if hardware limit of 5 reached use this instead
            self.get_command = lambda path: f'ffmpeg {self.loglevel} -threads 1 -y -s {self.width}x{self.height}  -pixel_format rgb24 -f rawvideo -r {self.fps} -i pipe: -vcodec {encoder} -pix_fmt yuv420p {path} -threads 1 {self.x265_params}'
        # elif self.recorder_type == "depth":
        #     encoder = "hevc"
        #     self.get_command = lambda path: f'ffmpeg {self.loglevel} -y -s {self.width}x{self.height} -pixel_format gray16le -f rawvideo -r {self.fps} -i pipe: -vcodec {encoder} -pix_fmt gray12le {path} -threads 1 {self.x265_params}'
        self.writer = None
    
    def started(self):
        return self.writer is not None
    
    def start(self, path: Path):
        if isinstance(path, str):
            path = Path(path)
        assert self.writer is None
        # print(self.get_command(path))
        self.writer = sp.Popen(shlex.split(self.get_command(path)), stdout=sp.DEVNULL, stdin=sp.PIPE)

    def record_frame(self, data: np.ndarray):
        assert self.writer is not None
        assert self.width == data.shape[1] and self.height == data.shape[0]
        if self.recorder_type == "depth":
            data = (data / self.depth_scale).clip(0, 1) * 65535
            data = data.astype(np.uint16)
        self.writer.stdin.write(data.tobytes())
        self.frame_counter += 1

    def stop(self):
        if self.writer is None:
            return
        self.writer.stdin.close()
        # self.writer.wait()
        self.writer.terminate()
        self.writer = None