# uncompyle6 version 3.9.3
# Python bytecode version base 3.8.0 (3413)
# Decompiled from: Python 3.12.3 | packaged by conda-forge | (main, Apr 15 2024, 18:20:11) [MSC v.1938 64 bit (AMD64)]
# Embedded file name: pyapp\api\Ui.py
import json

class Ui:
    config = {'menu':"single", 
     'actionStatus':{"value": ""}, 
     'print_mode':{"value": False}, 
     'common':{
      'resolution': None, 
      'rotate': 0, 
      'light': 0, 
      'contrast': 0, 
      'denoise': 0, 
      'sharpen': 0, 
      'autofocus': True, 
      'focus': 0}, 
     'preview':{'boxs':"单张", 
      'scale':100}, 
     'boxs_ocr':{"value": "不裁切"}, 
     'output':{'lens':"原图", 
      'boxs':[],  'mark':{
       'text': '""', 
       'font': '""', 
       'size': '""', 
       'color': '""', 
       'transparency': '""'}, 
      'mosaic':False, 
      'patch':True, 
      'rotate':False, 
      'output_format':"JPG", 
      'output_format_papers':"JPG", 
      'output_format_ocr':"docx", 
      'output_format_code':"JPG", 
      'video_format':"MP4", 
      'name_way':{'prefix':"IMG_", 
       'suffix':"index"}, 
      'name_way_papers':{'prefix':"IMG_", 
       'suffix':"index"}}, 
     'calcBox':{'scaleRate':1, 
      'imageSize':[
       0, 0], 
      'offset':[
       0, 0], 
      'boxs':[],  'mosaic':[],  'ocr':[]}, 
     'continuous_shot':{'mode':"手动扫描", 
      'duration':0}, 
     'papers_type':{"value": "身份证"}, 
     'code_type':{"value": "一维码"}, 
     'concat_type':{'value':"上下竖拼", 
      'targetPosition':""}, 
     'ocr_select':{"value": False}, 
     'audio':{"value": "静音"}, 
     'voice':{"value": True}, 
     'focusing':{"value": False}, 
     'currentA3':{"value": False}}

    def __init__(self):
        return

    def changeConfig(self, data):
        data = json.loads(data)
        for item in data:
            if item["type"] == "menu":
                self.config["menu"] = item["value"]
            else:
                self.config[item["type"]][item["key"]] = item["value"]

    def intToFloat(self, point):
        x, y = point
        scaleRate = self.config["calcBox"]["scaleRate"]
        offsetX, offsetY = self.config["calcBox"]["offset"]
        imageSizeW, imageSizeH = self.config["calcBox"]["imageSize"]
        x = (x / scaleRate + offsetX) / imageSizeW
        y = (y / scaleRate + offsetY) / imageSizeH
        return (
         x, y)

    def calcBoxCoordinates(self):
        boxs = self.config["calcBox"]["boxs"]
        return [
         self.intToFloat(boxs[0]), self.intToFloat(boxs[1]), self.intToFloat(boxs[2]), self.intToFloat(boxs[3])]

    def calcMosaicCoordinates(self):
        boxs = self.config["calcBox"]["mosaic"]
        return [
         self.intToFloat(boxs[0]), self.intToFloat(boxs[1]), self.intToFloat(boxs[2]), self.intToFloat(boxs[3])]

    def calcOcrCoordinates(self):
        boxs = self.config["calcBox"]["ocr"]
        return [
         self.intToFloat(boxs[0]), self.intToFloat(boxs[1]), self.intToFloat(boxs[2]), self.intToFloat(boxs[3])]

# okay decompiling D:\gk122\pyi\dlgpy.exe_extracted\PYZ-00.pyz_extracted\pyapp\api\Ui.pyc
