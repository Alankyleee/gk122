VIRTUAL_CAMERA_KEYWORDS = (
    "obs", "virtual", "manycam", "snap camera", "xsplit", "ndi", "vcam",
)

GK122_NAME_KEYWORDS = (
    "gk122", "得力", "deli", "document camera", "document scanner", "scanner",
    "高拍仪",
)


def is_virtual_camera_name(name):
    normalized = (name or "").casefold()
    return any(keyword in normalized for keyword in VIRTUAL_CAMERA_KEYWORDS)


def is_gk122_camera_name(name):
    normalized = (name or "").casefold()
    return any(keyword in normalized for keyword in GK122_NAME_KEYWORDS)


def select_gk122_device(devices):
    candidates = [item for item in devices if item["is_gk122"] and not item["is_virtual"]]
    return max(candidates, key=lambda item: item["score"], default=None)
