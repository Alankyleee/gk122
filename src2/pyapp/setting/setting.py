# uncompyle6 version 3.9.3
# Python bytecode version base 3.8.0 (3413)
# Decompiled from: Python 3.12.3 | packaged by conda-forge | (main, Apr 15 2024, 18:20:11) [MSC v.1938 64 bit (AMD64)]
# Embedded file name: pyapp\setting\setting.py
import json
from pyapp.config.config import Config
import os
from algorithm.api import getMicrophoneDeviceNames

class Setting:
    userSetting = {}
    userSettingPath = None
    ui = None
    imageApi = None

    def __init__(self, ui, imageApi):
        self.ui = ui
        self.imageApi = imageApi
        self.init()

    def init(self):
        self.userSettingPath = os.path.join(Config.cacheDir, "userSetting.json")
        self.userSetting = {}
        self.getConfig()

    def getConfig(self):
        try:
            if not os.path.exists(self.userSettingPath):
                with open(self.userSettingPath, "w") as file:
                    json.dump({}, file)
            else:
                with open((self.userSettingPath), "r", encoding="utf-8") as userSettingJson:
                    self.userSetting = json.load(userSettingJson)
        except Exception as e:
            try:
                print(e)
            finally:
                e = None
                del e

        else:
            micList = [
             {'label':"静音", 
              'value':"静音"}]
            _micList = getMicrophoneDeviceNames()
            for item in _micList:
                micList.append({'label':item,  'value':item})
            else:
                self.syncSettingAndUi()

    def syncSettingAndUi(self):
        with open("./static/json/setting.json", "r", encoding="utf-8") as f:
            presetConfig = json.load(f)
        settings = {**presetConfig, **(self.userSetting)}
        for key in settings:
            if key == "fileFolder":
                if settings[key] != "":
                    self.imageApi.dest = settings[key]
            elif key == "voice":
                self.ui.config["voice"]["value"] = settings[key]
            elif key == "menu":
                self.ui.config["menu"] = settings[key]
            elif key == "name_way":
                self.ui.config["output"]["name_way"] = settings[key]
            elif key == "name_way_papers":
                self.ui.config["output"]["name_way_papers"] = settings[key]
            elif key == "continuous_shot_duration":
                self.ui.config["continuous_shot"]["duration"] = settings[key]
            else:
                if key == "boxs":
                    self.ui.config["preview"]["boxs"] = settings[key]
                if key == "boxs_ocr":
                    self.ui.config["boxs_ocr"]["value"] = settings[key]
                if key == "ocr_select":
                    self.ui.config["ocr_select"]["value"] = settings[key]
                if key == "continuous_shot":
                    self.ui.config["continuous_shot"]["mode"] = settings[key]
                if key == "color_filter":
                    self.ui.config["output"]["lens"] = settings[key]
                if key == "concat_type":
                    self.ui.config["concat_type"]["value"] = settings[key]
                if key == "papers_type":
                    self.ui.config["papers_type"]["value"] = settings[key]
                if key == "output_format":
                    self.ui.config["output"]["output_format"] = settings[key]
                if key == "output_format_papers":
                    self.ui.config["output"]["output_format_papers"] = settings[key]
                if key == "output_format_ocr":
                    self.ui.config["output"]["output_format_ocr"] = settings[key]
                if key == "output_format_code":
                    self.ui.config["output"]["output_format_code"] = settings[key]
                if key == "code_type":
                    self.ui.config["code_type"]["value"] = settings[key]
                if key == "video_format":
                    self.ui.config["output"]["video_format"] = settings[key]
                if key == "audio":
                    self.ui.config["audio"]["value"] = settings[key]

    def changeFileFolder(self, data):
        self.userSetting["fileFolder"] = data
        with open(self.userSettingPath, "w") as file:
            json.dump(self.userSetting, file)

    def changeUserConfig(self, data):
        data = json.loads(data)
        for item in data:
            if item["type"] == "menu":
                self.userSetting["menu"] = item["value"]
            else:
                if item["type"] == "voice":
                    self.userSetting["voice"] = item["value"]
                elif item["type"] == "preview":
                    if item["key"] == "boxs":
                        self.userSetting["boxs"] = item["value"]
                if item["type"] == "output":
                    if item["key"] == "lens":
                        self.userSetting["color_filter"] = item["value"]
                    if item["key"] == "output_format":
                        self.userSetting["output_format"] = item["value"]
                    if item["key"] == "output_format_papers":
                        self.userSetting["output_format_papers"] = item["value"]
                    if item["key"] == "video_format":
                        self.userSetting["video_format"] = item["value"]
                    if item["key"] == "output_format_ocr":
                        self.userSetting["output_format_ocr"] = item["value"]
                    if item["key"] == "output_format_code":
                        self.userSetting["output_format_code"] = item["value"]
                    if item["key"] == "name_way":
                        self.userSetting["name_way"] = item["value"]
                    if item["key"] == "name_way_papers":
                        self.userSetting["name_way_papers"] = item["value"]
                if item["type"] == "continuous_shot":
                    if item["key"] == "mode":
                        self.userSetting["continuous_shot"] = item["value"]
                    if item["key"] == "duration":
                        self.userSetting["continuous_shot_duration"] = item["value"]
                if item["type"] == "papers_type":
                    self.userSetting["papers_type"] = item["value"]
                if item["type"] == "concat_type" and item["key"] == "value":
                    self.userSetting["concat_type"] = item["value"]
            if item["type"] == "code_type":
                self.userSetting["code_type"] = item["value"]
            if item["type"] == "boxs_ocr":
                self.userSetting["boxs_ocr"] = item["value"]
            if item["type"] == "ocr_select":
                self.userSetting["ocr_select"] = item["value"]
        else:
            try:
                with open(self.userSettingPath, "w") as file:
                    json.dump(self.userSetting, file)
            except Exception as e:
                try:
                    print(e)
                finally:
                    e = None
                    del e

# okay decompiling D:\gk122\pyi\dlgpy.exe_extracted\PYZ-00.pyz_extracted\pyapp\setting\setting.pyc
