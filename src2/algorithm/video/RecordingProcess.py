# uncompyle6 version 3.9.3
# Python bytecode version base 3.8.0 (3413)
# Decompiled from: Python 3.12.3 | packaged by conda-forge | (main, Apr 15 2024, 18:20:11) [MSC v.1938 64 bit (AMD64)]
# Embedded file name: algorithm\video\RecordingProcess.py
import ctypes, subprocess, time
from apscheduler.schedulers.background import BackgroundScheduler
from algorithm.video import EnvUtil
import algorithm.video.exception.RecordingException as RecordingException

def get_video_encoder(config):
    video_encoder = "libx264"
    if config.file_suffix == "wmv":
        video_encoder = "wmv2"
    else:
        if config.file_suffix == "flv":
            video_encoder = "flv"
    return video_encoder


class RecordingProcess:
    _instance = None

    def __init__(self):
        self.recording_flag = False
        self.finish_flag = True
        self.popen = None
        self.current_frame = None
        self.start_time = None
        self.finish_time = None
        self.recorder = None
        self.scheduler = None

    def start_recording(self):
        if not self.recording_flag:
            raise self.finish_flag or RecordingException("录制未结束")
        else:
            self.finish_time = None
            config = VideoConfig.get_instance()
            ffmpeg_exe = EnvUtil.get_ffmpeg_exe_name()
            video_encoder = get_video_encoder(config)
            if config.audio_flag:
                command = [(f"{ffmpeg_exe}"),
                 "-f", "rawvideo",
                 "-pixel_format", "bgr24",
                 "-r", (f"{config.fps}"),
                 "-video_size", f"{config.resolution[0]}x{config.resolution[1]}",
                 "-i", "-",
                 "-f", "dshow",
                 "-rtbufsize", "200M",
                 "-i", f"audio={config.audio_device_name}",
                 "-pix_fmt", "yuv420p",
                 "-preset", "ultrafast",
                 "-tune", "zerolatency",
                 "-c:v", (f"{video_encoder}"),
                 "-r", (f"{config.fps}"),
                 "-b:v", "2000k",
                 "-shortest",
                 "-y",
                 (f"{config.file_name}")]
            else:
                command = [(f"{ffmpeg_exe}"),
                 "-f", "rawvideo",
                 "-pixel_format", "bgr24",
                 "-r", (f"{config.fps}"),
                 "-video_size", f"{config.resolution[0]}x{config.resolution[1]}",
                 "-i", "-",
                 "-pix_fmt", "yuv420p",
                 "-preset", "ultrafast",
                 "-tune", "zerolatency",
                 "-c:v", (f"{video_encoder}"),
                 "-r", (f"{config.fps}"),
                 "-b:v", "2000k",
                 "-y",
                 (f"{config.file_name}")]
        print("ffmpeg命令：", command)
        self.popen = subprocess.Popen(command,
          shell=False,
          stdin=(subprocess.PIPE),
          stdout=(subprocess.DEVNULL),
          stderr=(subprocess.STDOUT),
          creationflags=(subprocess.CREATE_NO_WINDOW))
        print("启动线程：", self.popen.pid)
        self.recording_flag = True
        self.finish_flag = False
        self.scheduler = BackgroundScheduler()
        print("float(1 / config.fps)", float(1 / config.fps))
        self.scheduler.add_job((self.write_frame), trigger="interval", seconds=(float(1 / config.fps)))
        self.scheduler.start()
        ctypes.windll.kernel32.SetThreadExecutionState(2147483650L)
        print("已开始录制")

    def write_frame(self):
        if not self.recording_flag or self.popen is None or self.current_frame is None:
            return
            self.popen.stdin.write(self.current_frame)
            if self.start_time is None:
                self.start_time = time.time()

    def stop_recording(self):
        ctypes.windll.kernel32.SetThreadExecutionState(2147483648L)
        try:
            self.recording_flag = False
            self.scheduler.shutdown()
            self.on_thread_finished()
        except Exception as e:
            try:
                print(e)
            finally:
                e = None
                del e

        else:
            print("子线程结束录制")

    def on_thread_finished(self):
        self.popen.stdin.close()
        self.popen = None
        self.finish_time = time.time()
        self.finish_flag = True
        self.scheduler = None
        print(f"视频预览api: 录制时长：{self.finish_time - self.start_time}秒")
        self.start_time = None

    def get_duration(self):
        if not self.recording_flag or self.finish_flag or self.start_time is None:
            return 0
        return int(time.time() - self.start_time)

    def set_current_frame(self, img):
        if self.recording_flag:
            if img is not None:
                self.current_frame = img.copy()

    @staticmethod
    def get_instance():
        if not RecordingProcess._instance:
            RecordingProcess._instance = RecordingProcess()
        return RecordingProcess._instance


def check_status():
    if RecordingProcess.get_instance().recording_flag:
        raise RecordingException("正在录制中，无法修改该配置")


class VideoConfig:
    _instance = None

    def __init__(self, resolution):
        self.resolution = resolution
        self.fps = 10
        self.audio_flag = False
        self.audio_device_name = None
        self.file_name = None
        self.file_suffix = None

    def set_resolution(self, resolution):
        if self.resolution == resolution:
            return
        check_status()
        self.resolution = resolution

    def set_fps(self, fps):
        if self.fps == fps:
            return
        check_status()
        self.fps = fps

    def prepare_recording(self, with_audio_flag, audio_device_name, file_name, file_suffix):
        check_status()
        self.audio_flag = False
        if with_audio_flag:
            if audio_device_name is not None:
                if audio_device_name != "":
                    if not EnvUtil.get_audio_device_names().__contains__(audio_device_name):
                        raise RecordingException("无效的录音设备")
                    self.audio_flag = True
                    self.audio_device_name = audio_device_name
        self.file_name = file_name
        self.file_suffix = file_suffix

    @staticmethod
    def get_instance():
        if not VideoConfig._instance:
            VideoConfig._instance = VideoConfig((1280, 720))
        return VideoConfig._instance

# okay decompiling D:\gk122\pyi\dlgpy.exe_extracted\PYZ-00.pyz_extracted\algorithm\video\RecordingProcess.pyc
