# Taken from https://github.com/real-stanford/diffusion_policy/blob/main/diffusion_policy/real_world/single_realsense.py

from typing import Optional, Callable, Dict, Tuple
import math
import os
import enum
import time
import json
import numpy as np
import pyrealsense2 as rs
import multiprocessing as mp
from pathlib import Path
import cv2
from threadpoolctl import threadpool_limits
from multiprocessing.managers import SharedMemoryManager
from .shared_memory.shared_ndarray import SharedNDArray
from .shared_memory.shared_memory_ring_buffer import SharedMemoryRingBuffer
from .shared_memory.shared_memory_queue import SharedMemoryQueue, Full, Empty
from .recorder import VideoRecorder

class Command(enum.Enum):
    SET_COLOR_OPTION = 0
    SET_DEPTH_OPTION = 1
    START_RECORDING = 2
    STOP_RECORDING = 3
    RECORD_FRAME = 4
    RESTART_PUT = 5

class SingleRealsense(mp.Process):
    MAX_PATH_LENGTH = 4096 # linux path has a limit of 4096 bytes

    def __init__(
            self, 
            shm_manager: SharedMemoryManager,
            serial_number,
            resolution=(1280,720),
            depth_resolution=(640,480),
            capture_fps=30,
            put_fps=None,
            put_downsample=True,
            record_fps=None,
            enable_color=True,
            enable_depth=False,
            enable_infrared=False,
            record_depth = True,
            align_depth_to_color=True,
            get_max_k=30,
            advanced_mode_config=None,
            transform: Optional[Callable[[Dict], Dict]] = None,
            vis_transform: Optional[Callable[[Dict], Dict]] = None,
            recording_transform: Optional[Callable[[Dict], Dict]] = None,
            verbose=False
        ):
        super().__init__()

        if put_fps is None:
            put_fps = capture_fps
        if record_fps is None:
            record_fps = capture_fps
        self.align_depth_to_color = align_depth_to_color

        # create ring buffer
        resolution = tuple(resolution)
        shape = resolution[::-1]
        if align_depth_to_color:
            depth_shape = shape
        else:
            depth_shape = depth_resolution[::-1]
        examples = dict()
        if enable_color:
            examples['color'] = np.empty(
                shape=shape+(3,), dtype=np.uint8)
        if enable_depth:
            examples['depth'] = np.empty(
                shape=depth_shape, dtype=np.uint16)
        if enable_infrared:
            examples['infrared'] = np.empty(
                shape=depth_shape, dtype=np.uint8)
        examples['camera_capture_timestamp'] = 0.0
        examples['camera_receive_timestamp'] = 0.0
        examples['timestamp'] = 0.0
        examples['step_idx'] = 0

        expected_put_fps = put_fps
        expedcted_capture_fps = capture_fps
        if serial_number.startswith('f'):
            expected_put_fps *= 2
            expedcted_capture_fps *= 2

        vis_ring_buffer = SharedMemoryRingBuffer.create_from_examples(
            shm_manager=shm_manager,
            examples=examples if vis_transform is None 
                else vis_transform(dict(examples)),
            get_max_k=1,
            get_time_budget=0.2,
            put_desired_frequency=expedcted_capture_fps
        )

        ring_buffer = SharedMemoryRingBuffer.create_from_examples(
            shm_manager=shm_manager,
            examples=examples if transform is None
                else transform(dict(examples)),
            get_max_k=get_max_k,
            get_time_budget=0.2,
            put_desired_frequency=expected_put_fps
        )

        # create command queue
        examples = {
            'cmd': Command.SET_COLOR_OPTION.value,
            'option_enum': rs.option.exposure.value,
            'option_value': 0.0,
            'video_path': np.array('a'*self.MAX_PATH_LENGTH),
            'recording_start_time': 0.0,
            'put_start_time': 0.0
        }

        command_queue = SharedMemoryQueue.create_from_examples(
            shm_manager=shm_manager,
            examples=examples,
            buffer_size=128
        )

        # create shared array for intrinsics
        intrinsics_array = SharedNDArray.create_from_shape(
                mem_mgr=shm_manager,
                shape=(7,),
                dtype=np.float64)
        intrinsics_array.get()[:] = 0

        depth_intrinsics_array = SharedNDArray.create_from_shape(
                mem_mgr=shm_manager,
                shape=(7,),
                dtype=np.float64)
        depth_intrinsics_array.get()[:] = 0

        distortion_array = SharedNDArray.create_from_shape(
                mem_mgr=shm_manager,
                shape=(5,),
                dtype=np.float64)
        distortion_array.get()[:] = 0

        depth_distortion_array = SharedNDArray.create_from_shape(
                mem_mgr=shm_manager,
                shape=(5,),
                dtype=np.float64)
        depth_distortion_array.get()[:] = 0

        extrinsincs_array = SharedNDArray.create_from_shape(
                mem_mgr=shm_manager,
                shape=(16,),
                dtype=np.float64)
        extrinsincs_array.get()[:] = 0

        # create video recorder
        self.color_video_recorder = None
        self.depth_video_recorder = None
        if enable_color:
            self.color_video_recorder = VideoRecorder(
                width=resolution[0],
                height=resolution[1],
                fps=record_fps,
                recorder_type='color'
            )
        self.record_depeth = record_depth
        if enable_depth and record_depth:
            self.depth_video_recorder = VideoRecorder(
                width=resolution[0],
                height=resolution[1],
                fps=record_fps,
                recorder_type='depth'
            )
        # realsense uses bgr24 pixel format
        # default thread_type to FRAEM
        # i.e. each frame uses one core
        # instead of all cores working on all frames.
        # this prevents CPU over-subpscription and
        # improves performance significantly
        # video_recorder = VideoRecorder.create_h264(
        #     fps=record_fps, 
        #     codec='h264',
        #     input_pix_fmt='bgr24', 
        #     crf=18,
        #     thread_type='FRAME',
        #     thread_count=1)

        # copied variables
        self.serial_number = serial_number
        self.resolution = resolution
        self.depth_resolution = depth_resolution
        self.capture_fps = capture_fps
        self.put_fps = put_fps
        self.put_downsample = put_downsample
        self.record_fps = record_fps
        self.enable_color = enable_color
        self.enable_depth = enable_depth
        self.enable_infrared = enable_infrared
        self.advanced_mode_config = advanced_mode_config
        self.transform = transform
        self.vis_transform = vis_transform
        self.recording_transform = recording_transform
        self.verbose = verbose
        self.put_start_time = None

        # shared variables
        self.stop_event = mp.Event()
        self.ready_event = mp.Event()
        self.ring_buffer = ring_buffer
        self.vis_ring_buffer = vis_ring_buffer
        self.command_queue = command_queue
        self.intrinsics_array = intrinsics_array
        self.distortion_array = distortion_array
        self.extrinsics_array = extrinsincs_array
        self.depth_intrinsics_array = depth_intrinsics_array
        self.depth_distortion_array = depth_distortion_array
    
    @staticmethod
    def get_connected_devices_serial():
        serials = list()
        for d in rs.context().devices:
            if d.get_info(rs.camera_info.name).lower() != 'platform camera':
                serial = d.get_info(rs.camera_info.serial_number)
                product_line = d.get_info(rs.camera_info.product_line)
                if product_line == 'D400':
                    # only works with D400 series
                    serials.append(serial)
        serials = sorted(serials)
        return serials

    # ========= context manager ===========
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    # ========= user API ===========
    def start(self, wait=True, put_start_time=None):
        self.put_start_time = put_start_time
        super().start()
        if wait:
            self.start_wait()
    
    def stop(self, wait=True):
        self.stop_event.set()
        if wait:
            self.end_wait()

    def start_wait(self):
        self.ready_event.wait()
    
    def end_wait(self):
        self.join()

    @property
    def is_ready(self):
        return self.ready_event.is_set()

    def get(self, k=None, out=None):
        if k is None:
            return self.ring_buffer.get(out=out)
        else:
            return self.ring_buffer.get_last_k(k, out=out)
    
    def get_vis(self, out=None):
        return self.vis_ring_buffer.get(out=out)
    
    # ========= user API ===========
    def set_color_option(self, option: rs.option, value: float):
        self.command_queue.put({
            'cmd': Command.SET_COLOR_OPTION.value,
            'option_enum': option.value,
            'option_value': value
        })

    def set_depth_option(self, option: rs.option, value: float):
        self.command_queue.put({
            'cmd': Command.SET_DEPTH_OPTION.value,
            'option_enum': option.value,
            'option_value': value
        })
    
    def set_exposure(self, exposure=None, gain=None):
        """
        exposure: (1, 10000) 100us unit. (0.1 ms, 1/10000s)
        gain: (0, 128)
        """

        if exposure is None and gain is None:
            # auto exposure
            self.set_color_option(rs.option.enable_auto_exposure, 1.0)
        else:
            # manual exposure
            self.set_color_option(rs.option.enable_auto_exposure, 0.0)
            if exposure is not None:
                self.set_color_option(rs.option.exposure, exposure)
            if gain is not None:
                self.set_color_option(rs.option.gain, gain)
    
    def set_white_balance(self, white_balance=None):
        if white_balance is None:
            self.set_color_option(rs.option.enable_auto_white_balance, 1.0)
        else:
            self.set_color_option(rs.option.enable_auto_white_balance, 0.0)
            self.set_color_option(rs.option.white_balance, white_balance)

    def get_intrinsics_depth(self):
        assert self.ready_event.is_set()
        fx, fy, ppx, ppy = self.depth_intrinsics_array.get()[:4]
        mat = np.eye(3)
        mat[0,0] = fx
        mat[1,1] = fy
        mat[0,2] = ppx
        mat[1,2] = ppy
        return mat

    def get_dist_coeffs_depth(self):
        assert self.ready_event.is_set()
        return self.depth_distortion_array.get()

    def get_intrinsics(self):
        assert self.ready_event.is_set()
        fx, fy, ppx, ppy = self.intrinsics_array.get()[:4]
        mat = np.eye(3)
        mat[0,0] = fx
        mat[1,1] = fy
        mat[0,2] = ppx
        mat[1,2] = ppy
        return mat
    
    def get_dist_coeffs(self):
        assert self.ready_event.is_set()
        return self.distortion_array.get()

    def get_extrinsics(self) -> np.ndarray:
        assert self.ready_event.is_set()
        X_CD = self.extrinsics_array.get().reshape(4, 4)
        return X_CD

    def get_depth_scale(self):
        assert self.ready_event.is_set()
        scale = self.intrinsics_array.get()[-1]
        return scale
    
    def start_recording(self, video_path: str, start_time: float=-1):
        assert self.enable_color

        path_len = len(video_path.encode('utf-8'))
        if path_len > self.MAX_PATH_LENGTH:
            raise RuntimeError('video_path too long.')

        video_path = str(video_path)
    #     start_time = command['recording_start_time']
    #     if start_time < 0:
    #         start_time = None
        if self.color_video_recorder:
            self.color_video_recorder.start(video_path)
        if self.depth_video_recorder:
            # add _depth to path
            video_path = Path(video_path)
            video_path = video_path.parent.joinpath(
                video_path.stem + '_depth' + video_path.suffix)
            self.depth_video_recorder.start(video_path)
        # self.command_queue.put({
        #     'cmd': Command.START_RECORDING.value,
        #     'video_path': video_path,
        #     'recording_start_time': start_time
        # })
        
    def stop_recording(self):
        if self.color_video_recorder:
            self.color_video_recorder.stop()
        if self.depth_video_recorder:
            self.depth_video_recorder.stop()
        # self.command_queue.put({
        #     'cmd': Command.STOP_RECORDING.value
        # })
    
    def record_frame(self):
        rec_data = self.get()
        if self.color_video_recorder:
            self.color_video_recorder.record_frame(rec_data["color"])
        if self.depth_video_recorder:
            self.depth_video_recorder.record_frame(rec_data["depth"])
        # self.command_queue.put({
        #     'cmd': Command.RECORD_FRAME.value
        # })
    
    def restart_put(self, start_time):
        self.command_queue.put({
            'cmd': Command.RESTART_PUT.value,
            'put_start_time': start_time
        })
    
    def project(self, X):
        if X.shape[0] == 3:
            if len(X.shape) == 1:
                X = np.append(X, 1)
            else:
                X = np.concatenate([X, np.ones((1, X.shape[1]))], axis=0)

        K = np.zeros((4, 4))
        K[:3, :3] = self.get_intrinsics()
        K[2, 2] = 1
        x = K @ X
        result = np.round(x[0:2] / x[2]).astype(int)
        width, height = self.resolution
        if not (0 <= result[0] < width and 0 <= result[1] < height):
            print("Projected point outside of image bounds")
        return result[0], result[1]
     
    # ========= interval API ===========
    def run(self):
        # limit threads
        threadpool_limits(1)
        # cv2.setNumThreads(1) # this blocks the second time its used ...

        w, h = self.resolution
        dw, dh = self.depth_resolution
        fps = self.capture_fps
        align = rs.align(rs.stream.color)
        # Enable the streams from all the intel realsense devices
        rs_config = rs.config()
        if self.enable_color:
            rs_config.enable_stream(rs.stream.color, 
                w, h, rs.format.rgb8, fps)
        if self.enable_depth:
            rs_config.enable_stream(rs.stream.depth, 
                dw, dh, rs.format.z16, fps)
        if self.enable_infrared:
            rs_config.enable_stream(rs.stream.infrared,
                dw, dh, rs.format.y8, fps)
        
        try:
            rs_config.enable_device(self.serial_number)

            # start pipeline
            pipeline = rs.pipeline()
            if self.verbose:
                print(f"Starting pipeline for {self.serial_number}, {self.resolution} {self.capture_fps}fps.")
            pipeline_profile = pipeline.start(rs_config)

            # report global time
            # https://github.com/IntelRealSense/librealsense/pull/3909
            d = pipeline_profile.get_device().first_color_sensor()
            d.set_option(rs.option.global_time_enabled, 1)

            # setup advanced mode
            if self.advanced_mode_config is not None:
                json_text = json.dumps(self.advanced_mode_config)
                device = pipeline_profile.get_device()
                advanced_mode = rs.rs400_advanced_mode(device)
                advanced_mode.load_json(json_text)

            # get
            color_stream = pipeline_profile.get_stream(rs.stream.color)
            intr = color_stream.as_video_stream_profile().get_intrinsics()
            order = ['fx', 'fy', 'ppx', 'ppy', 'height', 'width']
            for i, name in enumerate(order):
                self.intrinsics_array.get()[i] = getattr(intr, name)
            
            
            # distortion coefficients
            distortion = intr.coeffs
            self.distortion_array.get()[:] = distortion

            if self.enable_depth:
                depth_sensor = pipeline_profile.get_device().first_depth_sensor()
                if self.serial_number.startswith('f'):
                    depth_sensor.set_option(rs.option.visual_preset,  int(rs.l500_visual_preset.short_range))
                    depth_sensor.set_option(rs.option.confidence_threshold, 3)

                depth_scale = depth_sensor.get_depth_scale()
                self.intrinsics_array.get()[-1] = depth_scale

                depth_stream = pipeline_profile.get_stream(rs.stream.depth)
                extrinsics = depth_stream.get_extrinsics_to(color_stream)
                X_CD = np.eye(4)
                X_CD[:3, :3] = np.array(extrinsics.rotation).reshape(3, 3)
                X_CD[:3, 3] = np.array(extrinsics.translation)
                self.extrinsics_array.get()[:] = X_CD.flatten()

                intr = depth_stream.as_video_stream_profile().get_intrinsics()
                order = ['fx', 'fy', 'ppx', 'ppy', 'height', 'width']
                for i, name in enumerate(order):
                    self.depth_intrinsics_array.get()[i] = getattr(intr, name)
                
                
                # distortion coefficients
                depth_distortion = intr.coeffs
                self.distortion_array.get()[:] = depth_distortion
            

            
            # one-time setup (intrinsics etc, ignore for now)
            if self.verbose:
                print(f'[SingleRealsense {self.serial_number}] Main loop started.')



            #time.sleep(4) # @jc211: this waits for all the other cameras to stabilize. When using multiple cameras, not having this makes the stream lag.
            # put frequency regulation
            
            put_idx = None
            put_start_time = self.put_start_time
            if put_start_time is None:
                put_start_time = time.time()

            iter_idx = 0
            t_start = time.time()
            while not self.stop_event.is_set():
                # wait for frames to come in
                frameset = pipeline.wait_for_frames()
                receive_time = time.time()
              
                # align frames to color
                if self.enable_depth and self.align_depth_to_color:
                    frameset = align.process(frameset)

                # grab data
                data = dict()
                data['camera_receive_timestamp'] = receive_time
                # realsense report in ms
                data['camera_capture_timestamp'] = frameset.get_timestamp() / 1000
                if self.enable_color:
                    color_frame = frameset.get_color_frame()
                    data['color'] = np.asarray(color_frame.get_data())
                    t = color_frame.get_timestamp() / 1000
                    data['camera_capture_timestamp'] = t
                    # print('device', time.time() - t)
                    # print(color_frame.get_frame_timestamp_domain())
                if self.enable_depth:
                    data['depth'] = np.asarray(
                        frameset.get_depth_frame().get_data())
                if self.enable_infrared:
                    data['infrared'] = np.asarray(
                        frameset.get_infrared_frame().get_data())
                
                # apply transform
                put_data = data
                if self.transform is not None:
                    put_data = self.transform(dict(data))

                if self.put_downsample:                
                    # put frequency regulation
                    local_idxs, global_idxs, put_idx \
                        = get_accumulate_timestamp_idxs(
                            timestamps=[receive_time],
                            start_time=put_start_time,
                            dt=1/self.put_fps,
                            # this is non in first iteration
                            # and then replaced with a concrete number
                            next_global_idx=put_idx,
                            # continue to pump frames even if not started.
                            # start_time is simply used to align timestamps.
                            allow_negative=True
                        )

                    for step_idx in global_idxs:
                        put_data['step_idx'] = step_idx
                        # put_data['timestamp'] = put_start_time + step_idx / self.put_fps
                        put_data['timestamp'] = receive_time
                        # print(step_idx, data['timestamp'])
                        self.ring_buffer.put(put_data, wait=False) # was false jc211
                else:
                    step_idx = int((receive_time - put_start_time) * self.put_fps)
                    put_data['step_idx'] = step_idx
                    put_data['timestamp'] = receive_time
                    self.ring_buffer.put(put_data, wait=False) # was false jc211

                # signal ready
                if iter_idx == 0:
                    self.ready_event.set()
                
                # put to vis
                vis_data = data
                if self.vis_transform == self.transform:
                    vis_data = put_data
                elif self.vis_transform is not None:
                    vis_data = self.vis_transform(dict(data))
                self.vis_ring_buffer.put(vis_data, wait=False) # was false jc211
                
                # record frame
                rec_data = data
                if self.recording_transform == self.transform:
                    rec_data = put_data
                elif self.recording_transform is not None:
                    rec_data = self.recording_transform(dict(data))

                # if self.video_recorder.is_ready():
                #     self.video_recorder.write_frame(rec_data['color'], 
                #         frame_time=receive_time)

                # perf
                t_end = time.time()
                duration = t_end - t_start
                frequency = np.round(1 / duration, 1)
                t_start = t_end
                if self.verbose:
                    print(f'[SingleRealsense {self.serial_number}] FPS {frequency}')

                # fetch command from queue
                try:
                    commands = self.command_queue.get_all()
                    n_cmd = len(commands['cmd'])
                except Empty:
                    n_cmd = 0

                # execute commands
                recorded_frame = False
                for i in range(n_cmd):
                    command = dict()
                    for key, value in commands.items():
                        command[key] = value[i]
                    cmd = command['cmd']
                    if cmd == Command.SET_COLOR_OPTION.value:
                        sensor = pipeline_profile.get_device().first_color_sensor()
                        option = rs.option(command['option_enum'])
                        value = float(command['option_value'])
                        sensor.set_option(option, value)
                        # print('auto', sensor.get_option(rs.option.enable_auto_exposure))
                        # print('exposure', sensor.get_option(rs.option.exposure))
                        # print('gain', sensor.get_option(rs.option.gain))
                    elif cmd == Command.SET_DEPTH_OPTION.value:
                        sensor = pipeline_profile.get_device().first_depth_sensor()
                        option = rs.option(command['option_enum'])
                        value = float(command['option_value'])
                        sensor.set_option(option, value)
                    elif cmd == Command.START_RECORDING.value:
                        put_idx = None
                        video_path = str(command['video_path'])
                    #     start_time = command['recording_start_time']
                    #     if start_time < 0:
                    #         start_time = None
                        if self.color_video_recorder:
                            self.color_video_recorder.start(video_path)
                        if self.depth_video_recorder:
                            # add _depth to path
                            video_path = Path(video_path)
                            video_path = video_path.parent.joinpath(
                                video_path.stem + '_depth' + video_path.suffix)
                            self.depth_video_recorder.start(video_path)
                    elif cmd == Command.STOP_RECORDING.value:
                        if self.color_video_recorder:
                            self.color_video_recorder.stop()
                        if self.depth_video_recorder:
                            self.depth_video_recorder.stop()
                        # stop need to flush all in-flight frames to disk, which might take longer than dt.
                        # soft-reset put to drop frames to prevent ring buffer overflow.
                        # put_idx = None
                    elif cmd == Command.RECORD_FRAME.value:
                        if recorded_frame:
                            continue
                        if self.color_video_recorder:
                            self.color_video_recorder.record_frame(rec_data["color"])
                        if self.depth_video_recorder:
                            self.depth_video_recorder.record_frame(rec_data["depth"])
                        recorded_frame = True
                    elif cmd == Command.RESTART_PUT.value:
                        put_idx = None
                        put_start_time = command['put_start_time']
                        # self.ring_buffer.clear()

                iter_idx += 1
        finally:
            # self.video_recorder.stop()
            if self.color_video_recorder:
                self.color_video_recorder.stop()
            if self.depth_video_recorder:
                self.depth_video_recorder.stop()
            rs_config.disable_all_streams()
            self.ready_event.set()
        
        if self.verbose:
            print(f'[SingleRealsense {self.serial_number}] Exiting worker process.')
    
def get_accumulate_timestamp_idxs(
    timestamps: list[float],  
    start_time: float, 
    dt: float, 
    eps:float=1e-5,
    next_global_idx: Optional[int]=0,
    allow_negative=False
    ) -> Tuple[list[int], list[int], int]:
    """
    For each dt window, choose the first timestamp in the window.
    Assumes timestamps sorted. One timestamp might be chosen multiple times due to dropped frames.
    next_global_idx should start at 0 normally, and then use the returned next_global_idx. 
    However, when overwiting previous values are desired, set last_global_idx to None.

    Returns:
    local_idxs: which index in the given timestamps array to chose from
    global_idxs: the global index of each chosen timestamp
    next_global_idx: used for next call.
    """
    local_idxs = list()
    global_idxs = list()
    for local_idx, ts in enumerate(timestamps):
        # add eps * dt to timestamps so that when ts == start_time + k * dt 
        # is always recorded as kth element (avoiding floating point errors)
        global_idx = math.floor((ts - start_time) / dt + eps)
        if (not allow_negative) and (global_idx < 0):
            continue
        if next_global_idx is None:
            next_global_idx = global_idx

        n_repeats = max(0, global_idx - next_global_idx + 1)
        for i in range(n_repeats):
            local_idxs.append(local_idx)
            global_idxs.append(next_global_idx + i)
        next_global_idx += n_repeats
    return local_idxs, global_idxs, next_global_idx