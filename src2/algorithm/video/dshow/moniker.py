# uncompyle6 version 3.9.3
# Python bytecode version base 3.8.0 (3413)
# Decompiled from: Python 3.12.3 | packaged by conda-forge | (main, Apr 15 2024, 18:20:11) [MSC v.1938 64 bit (AMD64)]
# Embedded file name: algorithm\video\dshow\moniker.py
from ctypes.wintypes import _ULARGE_INTEGER
from comtypes import COMMETHOD, GUID, HRESULT, POINTER, IPersist, IUnknown, c_int, c_ulong

class IPersistStream(IPersist):
    _case_insensitive_ = True
    _iid_ = GUID("{00000109-0000-0000-C000-000000000046}")
    _idlflags_ = []


class ISequentialStream(IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID("{0C733A30-2A1C-11CE-ADE5-00AA0044773D}")
    _idlflags_ = []


class IStream(ISequentialStream):
    _case_insensitive_ = True
    _iid_ = GUID("{0000000C-0000-0000-C000-000000000046}")
    _idlflags_ = []


IPersistStream._methods_ = [
 COMMETHOD([], HRESULT, "IsDirty"),
 COMMETHOD([], HRESULT, "Load", (
  [
   "in"], POINTER(IStream), "pstm")),
 COMMETHOD([], HRESULT, "Save", (
  [
   "in"], POINTER(IStream), "pstm"), (
  [
   "in"], c_int, "fClearDirty")),
 COMMETHOD([], HRESULT, "GetSizeMax", (
  [
   "out"], POINTER(_ULARGE_INTEGER), "pcbSize"))]

class IEnumMoniker(IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID("{00000102-0000-0000-C000-000000000046}")
    _idlflags_ = []


class IMoniker(IPersistStream):
    _case_insensitive_ = True
    _iid_ = GUID("{0000000F-0000-0000-C000-000000000046}")
    _idlflags_ = []


IMONIKER = POINTER(IMoniker)

class IBindCtx(IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID("{0000000E-0000-0000-C000-000000000046}")
    _idlflags_ = []


IEnumMoniker._methods_ = [
 COMMETHOD([], HRESULT, "Next", (
  [
   "in"], c_ulong, "celt"), (
  [
   "out"], POINTER(POINTER(IMoniker)), "rgelt"), (
  [
   "out"], POINTER(c_ulong), "pceltFetched")),
 COMMETHOD([], HRESULT, "Skip", (
  [
   "in"], c_ulong, "celt")),
 COMMETHOD([], HRESULT, "Reset"),
 COMMETHOD([], HRESULT, "Clone", (
  [
   "out"], POINTER(POINTER(IMoniker)), "ppenum"))]
IMoniker._methods_ = [
 COMMETHOD([], HRESULT, "BindToObject", (
  [
   "in"], POINTER(IBindCtx), "pbc"), (
  [
   "in"], POINTER(IMoniker), "pmkToLeft"), (
  [
   "in"], POINTER(GUID), "riidResult"), (
  [
   "out"], POINTER(POINTER(IUnknown)), "ppvResult")),
 COMMETHOD([], HRESULT, "BindToStorage", (
  [
   "in"], POINTER(IBindCtx), "pbc"), (
  [
   "in"], POINTER(IMoniker), "pmkToLeft"), (
  [
   "in"], POINTER(GUID), "riid"), (
  [
   "out"], POINTER(POINTER(IUnknown)), "ppvObj"))]

# okay decompiling D:\gk122\pyi\dlgpy.exe_extracted\PYZ-00.pyz_extracted\algorithm\video\dshow\moniker.pyc
