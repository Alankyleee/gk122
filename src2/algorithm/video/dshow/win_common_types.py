# uncompyle6 version 3.9.3
# Python bytecode version base 3.8.0 (3413)
# Decompiled from: Python 3.12.3 | packaged by conda-forge | (main, Apr 15 2024, 18:20:11) [MSC v.1938 64 bit (AMD64)]
# Embedded file name: algorithm\video\dshow\win_common_types.py
from ctypes import POINTER, c_int, c_longlong, c_ulong, c_ulonglong, c_wchar_p
from ctypes.wintypes import SHORT
from comtypes import GUID
REFERENCE_TIME = c_longlong
LONG_PTR = c_ulong
OLE_HANDLE = c_int
LPCOLESTR = c_wchar_p
REFIID = POINTER(GUID)
REFGUID = POINTER(GUID)
WORD = SHORT
DWORDLONG = c_ulonglong

# okay decompiling D:\gk122\pyi\dlgpy.exe_extracted\PYZ-00.pyz_extracted\algorithm\video\dshow\win_common_types.pyc
