# uncompyle6 version 3.9.3
# Python bytecode version base 3.8.0 (3413)
# Decompiled from: Python 3.12.3 | packaged by conda-forge | (main, Apr 15 2024, 18:20:11) [MSC v.1938 64 bit (AMD64)]
# Embedded file name: algorithm\setting\capture_prop.py
import os, re, yaml
from ast import literal_eval
root_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) + "/"
properties_path = root_path + "static/properties/capture.yaml"

def parse_resolution_string(res_string):
    res_string = res_string.replace(" ", "")
    match = re.match("(\\d+),(\\d+),(.+)", res_string)
    if match:
        return (int(match.group(1)), int(match.group(2)), match.group(3))
    return res_string


with open(properties_path, "r", encoding="utf-8") as file:
    properties = yaml.safe_load(file)
for value in properties.values():
    value["resolution"]["doc_scan"] = [parse_resolution_string(res) for res in value["resolution"]["doc_scan"]]
    value["resolution"]["video_recording"] = [parse_resolution_string(res) for res in value["resolution"]["video_recording"]]
else:
    resolution_alias = {'(5232,3924)': '"2100万像素"', 
     '(4912,3684)': '"1800万像素"', 
     '(4608,3456)': '"1600万像素"', 
     '(4328,3246)': '"1400万像素"', 
     '(4032,3024)': '"1200万像素"', 
     '(3668,2751)': '"1000万像素"', 
     '(3264,2448)': '"800万像素"', 
     '(2592,1944)': '"500万像素"', 
     '(2048,1536)': '"300万像素"', 
     '(1920,1080)': '"200万像素"', 
     '(1600,1200)': '"192万像素"', 
     '(1280,960)': '"123万像素"', 
     '(1280,720)': '"92万像素"', 
     '(800,600)': '"48万像素"', 
     '(640,480)': '"30万像素"'}

    def get_device_info(device_name):
        device_name = get_name_without_firmware(device_name)
        if device_name not in properties:
            print("不支持的设备")
            return
        return properties[device_name]


    def filter_mike(mikes):
        res = []
        for mike in mikes:
            filte = False
            for key in properties.keys():
                if "disable_mike" in properties[key]:
                    if mike.find(key) != -1:
                        filte = True
                    if not filte:
                        res.append(mike)
                return res


    def get_name_without_firmware(device_name):
        left_bracket_index = device_name.find("(")
        if left_bracket_index != -1:
            return device_name[None[:left_bracket_index]].strip()
        return device_name


    def get_doc_scan_resolutions(device_name):
        device_name = get_name_without_firmware(device_name)
        if device_name in properties:
            resolutions = properties[device_name]["resolution"]["doc_scan"]
            resolutions = str_list_to_tuple_list(resolutions)
            resolution_with_alias = []
            for resolution in resolutions:
                alias = get_resolution_alias(resolution[0], resolution[1])
                resolution_with_alias.append((resolution[0], resolution[1], alias))
            else:
                return resolution_with_alias

        return []


    def get_video_recording_resolutions(device_name):
        device_name = get_name_without_firmware(device_name)
        if device_name in properties:
            resolutions = properties[device_name]["resolution"]["video_recording"]
            resolutions = str_list_to_tuple_list(resolutions)
            resolution_with_alias = []
            for resolution in resolutions:
                alias = get_resolution_alias(resolution[0], resolution[1])
                resolution_with_alias.append((resolution[0], resolution[1], alias))
            else:
                return resolution_with_alias

        return []


    def get_resolution_alias(w, h):
        resolution = "(" + str(w) + "," + str(h) + ")"
        if not resolution_alias.keys().__contains__(resolution):
            return ""
        return resolution_alias[resolution]


    def str_list_to_tuple_list(str_list):
        tuple_list = [eval(resolution) for resolution in str_list]
        return tuple_list


    if __name__ == "__main__":
        device_name = "15161S  (14351)"
        print(get_device_info(device_name))

# okay decompiling D:\gk122\pyi\dlgpy.exe_extracted\PYZ-00.pyz_extracted\algorithm\setting\capture_prop.pyc
