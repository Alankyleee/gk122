import re


VIRTUAL_CAMERA_KEYWORDS = (
    "obs", "virtual", "manycam", "snap camera", "xsplit", "ndi", "vcam",
)

GK122_MODEL_PATTERN = re.compile(r"(?<![a-z0-9])gk[\s_-]*122(?P<variant>a)?(?![a-z0-9])", re.I)


def is_virtual_camera_name(name):
    normalized = (name or "").casefold()
    return any(keyword in normalized for keyword in VIRTUAL_CAMERA_KEYWORDS)


def gk122_model_from_name(name):
    """按原厂 FriendlyName 规则识别 GK122/GK122a。"""
    normalized = (name or "").strip()
    # 原厂会去掉固件名称，例如 ``GK122 (14351)``。
    without_firmware = normalized.split("(", 1)[0].strip()
    match = GK122_MODEL_PATTERN.search(without_firmware)
    if match:
        return "GK122a" if match.group("variant") else "GK122"

    folded = without_firmware.casefold()
    if "得力" in folded and "高拍仪" in folded:
        return "GK122"
    return None


def is_gk122_camera_name(name):
    return gk122_model_from_name(name) is not None


def select_gk122_device(devices):
    candidates = [item for item in devices if item["is_gk122"] and not item["is_virtual"]]
    return max(candidates, key=lambda item: item["score"], default=None)
