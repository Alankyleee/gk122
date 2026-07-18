# uncompyle6 version 3.9.3
# Python bytecode version base 3.8.0 (3413)
# Decompiled from: Python 3.12.3 | packaged by conda-forge | (main, Apr 15 2024, 18:20:11) [MSC v.1938 64 bit (AMD64)]
# Embedded file name: algorithm\shot\ShotConfig.py
import algorithm.shot.ShotType as ShotType
import algorithm.shot.Moment as Moment

class ShotConfig:
    _instance = None
    moment = None

    def __init__(self, status, shot_type, interval_second):
        self.status = status
        self.shot_type = shot_type
        self.interval_seconds = interval_second

    def start_auto_shot(self):
        self.status = True
        self.shot_type = ShotType.AUTO
        self.interval_seconds = None
        self.moment = self.get_moment_4_auto()
        self.moment.reset_for_auto(3)

    def start_interval_shot(self, interval_second):
        self.status = True
        self.shot_type = ShotType.INTERVAL
        self.interval_seconds = interval_second
        self.moment = self.get_moment_4_interval()
        self.moment.reset_for_interval(interval_second)

    def stop_shot(self):
        self.status = False
        self.shot_type = None
        self.interval_seconds = None

    @staticmethod
    def get_instance():
        if not ShotConfig._instance:
            ShotConfig._instance = ShotConfig(False, None, None)
        return ShotConfig._instance

    @staticmethod
    def get_moment_4_auto():
        if ShotConfig.moment is None:
            ShotConfig.moment = Moment(3)
        return ShotConfig.moment

    @staticmethod
    def get_moment_4_interval():
        config = ShotConfig.get_instance()
        if ShotConfig.moment is None:
            ShotConfig.moment = Moment(3)
            ShotConfig.moment.reset_for_interval(config.interval_seconds)
        return ShotConfig.moment

# okay decompiling D:\gk122\pyi\dlgpy.exe_extracted\PYZ-00.pyz_extracted\algorithm\shot\ShotConfig.pyc
