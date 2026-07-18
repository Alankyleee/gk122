# uncompyle6 version 3.9.3
# Python bytecode version base 3.8.0 (3413)
# Decompiled from: Python 3.12.3 | packaged by conda-forge | (main, Apr 15 2024, 18:20:11) [MSC v.1938 64 bit (AMD64)]
# Embedded file name: pyapp\config\config.py
"""
Description: 配置文件
usage:
    from pyapp.config.config import Config
    print(Config.rootDir)
"""
import os, getpass, platform, sys

class Config:
    __doc__ = "配置文件"
    appName = "得力高拍仪"
    appNameEN = "dlgpy"
    appVersion = "1.5.9"
    appDeveloper = "deli"
    appBlogs = ""
    appPackage = "dl.gpy"
    appUpdateUrl = "https://static-oss.delicloud.com/ucc/v2-mp/version.json"
    appISSID = "90F7BB42-4252-4281-B190-09C388A30A23"
    appSystem = platform.system()
    appIsMacOS = appSystem == "Darwin"
    codeDir = sys.path[0].replace("base_library.zip", "")
    appDir = codeDir.replace(appName + ".app/Contents/MacOS/", "")
    staticDir = os.path.join(codeDir, "static")
    storageDir = ""
    downloadDir = ""
    cacheDir = ""
    devEnv = True
    devPort = "8080"
    cryptoKey = "2043804044006733"
    ifCoverDB = False

    def init(self):
        """初始化"""
        self.getDir()

    def getDir(self):
        """获取电脑上的目录"""
        if Config.appSystem == "Darwin":
            user = getpass.getuser()
            storageDir = os.path.join("/", "Users", user, "Library", "Application Support")
            downloadDir = os.path.join("/", "Users", user, "Downloads")
        else:
            storageDir = os.getenv("APPDATA")
            downloadDir = os.path.join(os.getenv("USERPROFILE"), "Downloads")
        cacheDir = os.path.join(storageDir, "dlcache")
        storageDir = os.path.join(storageDir, Config.appPackage + ".gpy")
        if not os.path.isdir(cacheDir):
            os.mkdir(cacheDir)
        if not os.path.isdir(storageDir):
            os.mkdir(storageDir)
        Config.storageDir = storageDir
        Config.downloadDir = downloadDir
        Config.cacheDir = cacheDir

# okay decompiling D:\gk122\pyi\dlgpy.exe_extracted\PYZ-00.pyz_extracted\pyapp\config\config.pyc
