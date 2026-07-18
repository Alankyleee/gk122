import cv2
import yaml
import threading
import time
import os
import base64
import json
import shutil
import numpy as np
from datetime import datetime
from flask import Flask, jsonify, request, Response, send_from_directory, send_file
from flask_cors import CORS
from pathlib import Path
from camera_selection import (
    gk122_model_from_name,
    is_virtual_camera_name,
    select_gk122_device,
)

try:
    from cv2_enumerate_cameras import enumerate_cameras
except ImportError:
    enumerate_cameras = None

BASE_DIR = Path(__file__).parent
CAPTURE_YAML = BASE_DIR / "capture.yaml"
DEVICE_NAME = "GK122"
OUTPUT_DIR = BASE_DIR / "output"
PREVIEW_DIR = OUTPUT_DIR / "preview"
PAPERS_DIR = OUTPUT_DIR / "papers"
CODE_DIR = OUTPUT_DIR / "code"
CACHE_DIR = BASE_DIR / "cache"

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

capture_lock = threading.Lock()
video_capture = None
current_frame = None
current_frame_jpeg = None
frame_count = 0
is_running = False
capture_thread = None
device_index = 0
device_backend = None
device_name = ""
device_catalog = []
device_profiles = {}
config = None
camera_diagnostics = {
    "enumeration": [],
    "selected": None,
    "attempts": [],
    "last_error": None,
}

scan_state = {
    "mode": "manual",
    "interval_seconds": 3,
    "auto_delay": 3,
    "is_scanning": False,
    "scan_count": 0,
    "scan_thread": None,
    "stop_event": threading.Event(),
}

ui_config = {
    "menu": "single",
    "common": {"resolution": None, "rotate": 0, "light": 0, "contrast": 0,
               "denoise": 0, "sharpen": 0, "autofocus": True, "focus": 0},
    "preview": {"boxs": "单张", "scale": 100},
    "output": {"lens": "原图", "output_format": "JPG", "video_format": "MP4",
               "name_way": {"prefix": "IMG_", "suffix": "index"},
               "output_format_papers": "JPG", "output_format_ocr": "docx",
               "output_format_code": "JPG"},
    "continuous_shot": {"mode": "手动扫描", "duration": 3},
    "papers_type": {"value": "身份证"},
    "code_type": {"value": "一维码"},
    "concat_type": {"value": "上下竖拼", "targetPosition": ""},
    "audio": {"value": "静音"},
}


def ensure_dirs():
    for d in [OUTPUT_DIR, PREVIEW_DIR, PAPERS_DIR, CODE_DIR, CACHE_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def load_config():
    global config, device_profiles
    if CAPTURE_YAML.exists():
        with open(CAPTURE_YAML, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        device_profiles = data or {}
        config = device_profiles.get(DEVICE_NAME, {})
    else:
        config = {
            "recommend_resolution": [3264, 2448],
            "backup_resolution": [2048, 1536],
            "recommend_fourcc": "MJPG",
            "recommend_light": 0,
            "recommend_contrast": 32,
            "recommend_sharpen": 2,
            "resolution": {
                "doc_scan": [[4608, 3456], [3264, 2448], [2048, 1536], [1920, 1080]],
                "video_recording": [[2048, 1536], [1920, 1080], [1280, 720]],
            },
        }
        device_profiles = {DEVICE_NAME: config}


def get_device_profile(name):
    model = gk122_model_from_name(name) or DEVICE_NAME
    return device_profiles.get(model, config), model


def open_camera(index, backend=None):
    """按枚举结果打开设备，旧版数字索引则兼容 MSMF/DirectShow 回退。"""
    if backend is not None:
        return cv2.VideoCapture(int(index), int(backend))
    cap = cv2.VideoCapture(int(index), cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap.release()
        cap = cv2.VideoCapture(int(index), cv2.CAP_MSMF)
    return cap


def enumerate_device_entries():
    """获取与 OpenCV 索引一一对应的真实设备名称。"""
    if enumerate_cameras is not None:
        try:
            cameras = list(enumerate_cameras(cv2.CAP_DSHOW))
            if cameras:
                return [{
                    "index": int(camera.index),
                    "backend": int(camera.backend),
                    "name": camera.name or f"摄像头 ({camera.index})",
                    "vid": getattr(camera, "vid", None),
                    "pid": getattr(camera, "pid", None),
                    "path": getattr(camera, "path", None),
                    "name_detection": True,
                } for camera in cameras]
        except Exception as exc:
            app.logger.warning("DirectShow 设备名称枚举失败: %s", exc)

    # 缺少名称枚举依赖时保留旧版行为，但不再把索引写死为 GK122。
    return [{
        "index": i, "backend": int(cv2.CAP_DSHOW), "name": f"摄像头 ({i})",
        "vid": None, "pid": None, "path": None, "name_detection": False,
    } for i in range(10)]


def probe_device(entry):
    """只根据 DirectShow FriendlyName 分类，不提前打开摄像头。"""
    name = entry["name"]
    virtual = is_virtual_camera_name(name)
    model = gk122_model_from_name(name)
    result = dict(entry)
    result.update({
        "readable": None,
        "is_virtual": virtual,
        "is_gk122": bool(model and not virtual),
        "model": model,
        "max_width": 0,
        "max_height": 0,
        "score": (-1000 if virtual else 0) + (200 if model else 0),
    })
    return result


def list_devices():
    """按原厂方式枚举 FriendlyName；此阶段不打开任何摄像头。"""
    global device_catalog, camera_diagnostics
    entries = enumerate_device_entries()
    name_detection_available = any(item["name_detection"] for item in entries)
    devices = [probe_device(entry) for entry in entries]
    devices.sort(key=lambda item: item["score"], reverse=True)
    for item in devices:
        item["name_detection_available"] = name_detection_available
    device_catalog = devices
    camera_diagnostics["enumeration"] = [dict(item) for item in devices]
    return devices


def decode_fourcc(value):
    try:
        encoded = int(value)
    except (TypeError, ValueError, OverflowError):
        return ""
    return "".join(chr((encoded >> (8 * i)) & 0xFF) for i in range(4)).rstrip("\x00")


def safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return 0


def capture_snapshot(cap):
    if not cap:
        return {"opened": False}
    snapshot = {
        "opened": bool(cap.isOpened()),
        "width": safe_int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": safe_int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "fourcc": decode_fourcc(cap.get(cv2.CAP_PROP_FOURCC)),
    }
    try:
        snapshot["backend_name"] = cap.getBackendName()
    except (AttributeError, cv2.error):
        snapshot["backend_name"] = None
    return snapshot


def apply_settings(cap, settings=None, profile=None):
    """复刻原厂写入顺序：宽、高、自动曝光、MJPG，再写图像参数。"""
    if not cap or not cap.isOpened():
        return False
    s = settings or {}
    device_profile = profile or config
    width = s.get("width", device_profile["recommend_resolution"][0])
    height = s.get("height", device_profile["recommend_resolution"][1])
    fourcc_str = s.get("fourcc", device_profile.get("recommend_fourcc", "MJPG"))
    brightness = s.get("brightness", device_profile.get("recommend_light", 0))
    contrast = s.get("contrast", device_profile.get("recommend_contrast", 32))
    sharpness = s.get("sharpness", device_profile.get("recommend_sharpen", 2))
    fourcc = cv2.VideoWriter_fourcc(*fourcc_str)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
    cap.set(cv2.CAP_PROP_FOURCC, fourcc)
    cap.set(cv2.CAP_PROP_BRIGHTNESS, brightness)
    cap.set(cv2.CAP_PROP_CONTRAST, contrast)
    cap.set(cv2.CAP_PROP_SHARPNESS, sharpness)
    return True


def read_first_frame(cap, requested_width, requested_height, profile=None):
    """协商可用分辨率并读取首帧，避免驱动不接受单一分辨率时黑屏。"""
    global camera_diagnostics
    device_profile = profile or config
    configured = device_profile.get("resolution", {}).get("doc_scan", [])
    candidates = [(requested_width, requested_height)]
    candidates.extend((int(width), int(height)) for width, height in configured)
    candidates.extend([
        tuple(device_profile["recommend_resolution"]),
        tuple(device_profile["backup_resolution"]),
        (1920, 1080),
        (1280, 720),
    ])

    camera_diagnostics["attempts"] = []
    seen = set()
    for width, height in candidates:
        if (width, height) in seen:
            continue
        seen.add((width, height))
        apply_settings(cap, {"width": width, "height": height}, device_profile)
        attempt = {"requested": [width, height], "negotiated": capture_snapshot(cap), "reads": 0}
        camera_diagnostics["attempts"].append(attempt)
        # 16MP UVC 在 DirectShow 切换格式后可能需要数帧才开始输出。
        for _ in range(10):
            attempt["reads"] += 1
            ret, frame = cap.read()
            if ret and frame is not None and frame.size:
                attempt["frame"] = [int(frame.shape[1]), int(frame.shape[0])]
                return frame
            time.sleep(0.05)
        attempt["error"] = "no_frame"
    return None


def capture_loop():
    global current_frame, current_frame_jpeg, frame_count, is_running
    error_count = 0
    last_error_time = time.time()
    while is_running:
        with capture_lock:
            if not video_capture or not video_capture.isOpened():
                time.sleep(0.1)
                continue
            ret, frame = video_capture.read()
        if not ret:
            error_count += 1
            if time.time() - last_error_time > 5 and error_count > 50:
                break
            time.sleep(0.05)
            continue
        if frame is None or not frame.size:
            time.sleep(0.05)
            continue
        error_count = 0
        last_error_time = time.time()
        current_frame = frame
        frame_count += 1
        ret_jpg, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if ret_jpg:
            current_frame_jpeg = buf.tobytes()
        time.sleep(0.02)
    is_running = False


def get_output_filename(fmt="jpg", prefix="IMG_", suffix="index"):
    now = datetime.now()
    if suffix == "date":
        filename = f"{prefix}{now.strftime('%Y%m%d_%H%M%S')}"
    else:
        existing = [f for f in os.listdir(OUTPUT_DIR) if f.startswith(prefix) and f.endswith(f".{fmt.lower()}")]
        idx = len(existing) + 1
        filename = f"{prefix}{idx}"
    filepath = OUTPUT_DIR / f"{filename}.{fmt.lower()}"
    times = 0
    while filepath.exists():
        times += 1
        filepath = OUTPUT_DIR / f"{filename}_{times}.{fmt.lower()}"
    return filepath


def post_process_frame(frame, options=None):
    opts = options or {}
    angle = opts.get("rotate", 0)
    if angle == 90:
        frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
    elif angle == 180:
        frame = cv2.rotate(frame, cv2.ROTATE_180)
    elif angle == 270:
        frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
    if opts.get("denoise", 0) > 0:
        frame = cv2.fastNlMeansDenoisingColored(frame, None, opts["denoise"], 10, 7, 21)
    if opts.get("sharpen", 0) > 0:
        kernel = np.array([[-1, -1, -1], [-1, 9 + opts["sharpen"], -1], [-1, -1, -1]])
        frame = cv2.filter2D(frame, -1, kernel)
    if opts.get("brightness", 0) != 0 or opts.get("contrast", 0) != 0:
        bright = opts.get("brightness", 0)
        cont = opts.get("contrast", 0)
        frame = cv2.convertScaleAbs(frame, alpha=1 + cont / 100, beta=bright)
    return frame


def save_frame_to_file(frame, filepath, fmt="jpg", quality=92):
    ext = f".{fmt.lower()}"
    if fmt == "png":
        params = [cv2.IMWRITE_PNG_COMPRESSION, 3]
    else:
        params = [cv2.IMWRITE_JPEG_QUALITY, quality]
    ret, buf = cv2.imencode(ext, frame, params)
    if ret:
        buf.tofile(str(filepath))
        return True
    return False


def save_preview(frame, scan_id, idx, fmt="jpg"):
    preview_path = PREVIEW_DIR / f"{scan_id}_{idx}.{fmt.lower()}"
    save_frame_to_file(frame, preview_path, fmt)
    return str(preview_path)


def continuous_scan_loop(mode, interval, stop_event, callback):
    count = 0
    while not stop_event.is_set():
        if current_frame is None:
            time.sleep(0.1)
            continue
        frame = current_frame.copy()
        count += 1
        callback(frame, count)
        if mode == "interval":
            stop_event.wait(interval)
        elif mode == "auto":
            time.sleep(3)
        else:
            break


# ========================= API Routes =========================

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/devices")
def api_devices():
    devices = list_devices()
    return jsonify({
        "devices": devices,
        "count": len(devices),
        "name_detection_available": bool(devices and devices[0]["name_detection_available"]),
    })


@app.route("/api/config")
def api_config():
    return jsonify({"device": DEVICE_NAME, "config": config, "ui": ui_config})


@app.route("/api/start", methods=["POST"])
def api_start():
    global video_capture, is_running, capture_thread, device_index, device_backend, device_name
    global current_frame, current_frame_jpeg, frame_count
    global camera_diagnostics
    data = request.json or {}
    width = int(data.get("width", config["recommend_resolution"][0]))
    height = int(data.get("height", config["recommend_resolution"][1]))

    devices = device_catalog
    if not devices:
        devices = list_devices()

    selected = None
    if data.get("auto_select"):
        if devices and not devices[0].get("name_detection_available"):
            return jsonify({
                "success": False,
                "message": "无法安全识别 GK122，请先执行 pip install -r requirements.txt 后重启服务。",
            }), 409
        selected = select_gk122_device(devices)
        if not selected:
            return jsonify({
                "success": False,
                "message": "DirectShow 设备列表中未找到 GK122/GK122a，请安装原厂驱动并重新插拔 USB。",
            }), 404
    else:
        requested_index = int(data.get("index", 0))
        requested_backend = data.get("backend")
        if requested_backend is not None:
            requested_backend = int(requested_backend)
        selected = next((item for item in devices
                         if item["index"] == requested_index
                         and (requested_backend is None or item["backend"] == requested_backend)), None)
        if selected and selected["is_virtual"] and not data.get("allow_virtual"):
            return jsonify({"success": False, "message": f"{selected['name']} 是虚拟摄像头，请选择 GK122。"}), 400
        if selected is None:
            selected = {"index": requested_index, "backend": requested_backend, "name": f"摄像头 ({requested_index})"}

    device_index = int(selected["index"])
    device_backend = selected.get("backend")
    device_name = selected["name"]
    selected_profile, selected_model = get_device_profile(device_name)
    camera_diagnostics["selected"] = {
        "index": device_index,
        "backend": device_backend,
        "name": device_name,
        "model": selected_model,
    }
    camera_diagnostics["last_error"] = None

    # 彻底停掉旧读取线程，防止切换设备时线程继续读取已释放的句柄。
    is_running = False
    if capture_thread and capture_thread.is_alive():
        capture_thread.join(timeout=1.0)
    with capture_lock:
        if video_capture and video_capture.isOpened():
            video_capture.release()
            video_capture = None
        current_frame = None
        current_frame_jpeg = None
        frame_count = 0
        video_capture = open_camera(device_index, device_backend)
        if not video_capture.isOpened():
            camera_diagnostics["last_error"] = "open_failed"
            video_capture.release()
            video_capture = None
            return jsonify({
                "success": False,
                "message": f"无法打开摄像头: {device_name}",
                "diagnostics": camera_diagnostics,
            }), 400
        camera_diagnostics["opened"] = capture_snapshot(video_capture)
        # VideoCapture.isOpened() 只表示句柄打开；必须拿到真实首帧才算连接成功。
        first_frame = read_first_frame(video_capture, width, height, selected_profile)
        if first_frame is None:
            camera_diagnostics["last_error"] = "no_frame"
            video_capture.release()
            video_capture = None
            return jsonify({
                "success": False,
                "message": f"{device_name} 已打开但没有视频帧，请关闭占用摄像头的软件后重试。",
                "diagnostics": camera_diagnostics,
            }), 400
        current_frame = first_frame
        actual_h, actual_w = first_frame.shape[:2]
        ret_jpg, buf = cv2.imencode(".jpg", first_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not ret_jpg:
            video_capture.release()
            video_capture = None
            current_frame = None
            return jsonify({"success": False, "message": "首帧读取成功，但 JPEG 编码失败。"}), 500
        current_frame_jpeg = buf.tobytes()
        frame_count = 1
        is_running = True
        capture_thread = threading.Thread(target=capture_loop, daemon=True)
        capture_thread.start()
    return jsonify({
        "success": True, "width": actual_w, "height": actual_h,
        "device": {"index": device_index, "backend": device_backend, "name": device_name, "model": selected_model},
    })


@app.route("/api/stop", methods=["POST"])
def api_stop():
    global is_running, video_capture, current_frame, current_frame_jpeg
    is_running = False
    if capture_thread and capture_thread.is_alive():
        capture_thread.join(timeout=1.0)
    with capture_lock:
        if video_capture:
            video_capture.release()
            video_capture = None
        current_frame = None
        current_frame_jpeg = None
    return jsonify({"success": True})


@app.route("/api/status")
def api_status():
    with capture_lock:
        opened = video_capture and video_capture.isOpened()
        w = h = 0
        if opened:
            w = int(video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    return jsonify({
        "is_opened": bool(opened), "width": w, "height": h,
        "frame_count": frame_count, "running": is_running,
        "device": {"index": device_index, "backend": device_backend, "name": device_name},
        "scanning": scan_state["is_scanning"], "scan_count": scan_state["scan_count"],
    })


@app.route("/api/diagnostics")
def api_diagnostics():
    return jsonify(camera_diagnostics)


@app.route("/api/settings", methods=["POST"])
def api_settings():
    data = request.json or {}
    with capture_lock:
        if video_capture and video_capture.isOpened():
            selected_profile, _ = get_device_profile(device_name)
            apply_settings(video_capture, data, selected_profile)
            w = int(video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            return jsonify({"success": True, "width": w, "height": h,
                            "settings": {
                                "brightness": int(video_capture.get(cv2.CAP_PROP_BRIGHTNESS)),
                                "contrast": int(video_capture.get(cv2.CAP_PROP_CONTRAST)),
                                "sharpness": int(video_capture.get(cv2.CAP_PROP_SHARPNESS)),
                                "saturation": int(video_capture.get(cv2.CAP_PROP_SATURATION)),
                            }})
    return jsonify({"success": False, "message": "摄像头未开启"}), 400


@app.route("/api/frame")
def api_frame():
    if current_frame_jpeg is None:
        return jsonify({"success": False, "message": "无可用帧"}), 404
    return Response(current_frame_jpeg, mimetype="image/jpeg")


@app.route("/api/frame_base64")
def api_frame_base64():
    if current_frame_jpeg is None:
        return jsonify({"success": False, "message": "无可用帧"}), 404
    b64 = base64.b64encode(current_frame_jpeg).decode("ascii")
    return jsonify({"success": True, "image": "data:image/jpeg;base64," + b64,
                     "width": current_frame.shape[1] if current_frame is not None else 0,
                     "height": current_frame.shape[0] if current_frame is not None else 0})


@app.route("/api/stream")
def api_stream():
    def gen():
        while True:
            if current_frame_jpeg:
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n"
                       b"Content-Length: " + str(len(current_frame_jpeg)).encode() + b"\r\n\r\n"
                       + current_frame_jpeg + b"\r\n")
            time.sleep(0.05)
    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/api/rotate", methods=["POST"])
def api_rotate():
    global current_frame, current_frame_jpeg
    data = request.json or {}
    angle = int(data.get("angle", 90))
    if current_frame is None:
        return jsonify({"success": False, "message": "无可用帧"}), 404
    if angle == 90:
        rotated = cv2.rotate(current_frame, cv2.ROTATE_90_CLOCKWISE)
    elif angle == 180:
        rotated = cv2.rotate(current_frame, cv2.ROTATE_180)
    elif angle == 270:
        rotated = cv2.rotate(current_frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
    else:
        return jsonify({"success": False, "message": "无效角度"}), 400
    current_frame = rotated
    ret_jpg, buf = cv2.imencode(".jpg", rotated, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if ret_jpg:
        current_frame_jpeg = buf.tobytes()
    return jsonify({"success": True, "angle": angle})


# ========================= 单张扫描 =========================

@app.route("/api/scan/single", methods=["POST"])
def api_scan_single():
    if current_frame is None:
        return jsonify({"success": False, "message": "无可用帧"}), 404
    data = request.json or {}
    fmt = data.get("format", "jpg")
    quality = int(data.get("quality", 92))
    rotate = int(data.get("rotate", 0))
    denoise = int(data.get("denoise", 0))
    sharpen = int(data.get("sharpen", 0))
    brightness = int(data.get("brightness", 0))
    contrast = int(data.get("contrast", 0))
    prefix = data.get("prefix", "IMG_")
    suffix = data.get("suffix", "index")

    frame = post_process_frame(current_frame.copy(), {
        "rotate": rotate, "denoise": denoise, "sharpen": sharpen,
        "brightness": brightness, "contrast": contrast,
    })

    filepath = get_output_filename(fmt, prefix, suffix)
    if save_frame_to_file(frame, filepath, fmt, quality):
        scan_state["scan_count"] += 1
        return jsonify({"success": True, "path": str(filepath),
                         "filename": filepath.name, "width": frame.shape[1], "height": frame.shape[0]})
    return jsonify({"success": False, "message": "保存失败"}), 500


# ========================= 多张连续扫描 =========================

@app.route("/api/scan/start", methods=["POST"])
def api_scan_start():
    if scan_state["is_scanning"]:
        return jsonify({"success": False, "message": "扫描已在进行中"}), 400
    if current_frame is None:
        return jsonify({"success": False, "message": "摄像头未开启"}), 400

    data = request.json or {}
    mode = data.get("mode", "interval")
    interval = int(data.get("interval", 3))
    auto_delay = int(data.get("auto_delay", 3))
    fmt = data.get("format", "jpg")
    quality = int(data.get("quality", 92))
    rotate = int(data.get("rotate", 0))
    denoise = int(data.get("denoise", 0))
    prefix = data.get("prefix", "IMG_")
    suffix = data.get("suffix", "index")
    scan_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    scan_state["mode"] = mode
    scan_state["interval_seconds"] = interval
    scan_state["auto_delay"] = auto_delay
    scan_state["is_scanning"] = True
    scan_state["stop_event"] = threading.Event()
    scan_state["scan_id"] = scan_id
    scan_state["scan_count"] = 0
    scan_state["scan_files"] = []

    scan_opts = {"fmt": fmt, "quality": quality, "rotate": rotate,
                 "denoise": denoise, "prefix": prefix, "suffix": suffix,
                 "scan_id": scan_id}

    def on_scan(frame, count):
        processed = post_process_frame(frame, {"rotate": rotate, "denoise": denoise})
        idx = scan_state["scan_count"] + 1
        preview_path = save_preview(processed, scan_id, idx, fmt)
        scan_state["scan_count"] = idx
        scan_state["scan_files"].append(preview_path)
        scan_state["last_scan_time"] = time.time()
        scan_state["last_scan_path"] = preview_path

    def run_scan():
        if mode == "manual":
            on_scan(current_frame.copy(), 1)
            scan_state["is_scanning"] = False
        else:
            continuous_scan_loop(mode, interval, scan_state["stop_event"], on_scan)
            scan_state["is_scanning"] = False

    scan_state["scan_thread"] = threading.Thread(target=run_scan, daemon=True)
    scan_state["scan_thread"].start()

    return jsonify({"success": True, "scan_id": scan_id, "mode": mode})


@app.route("/api/scan/stop", methods=["POST"])
def api_scan_stop():
    scan_state["stop_event"].set()
    scan_state["is_scanning"] = False
    return jsonify({"success": True, "scan_count": scan_state["scan_count"],
                     "files": scan_state.get("scan_files", [])})


@app.route("/api/scan/manual", methods=["POST"])
def api_scan_manual():
    if current_frame is None:
        return jsonify({"success": False, "message": "无可用帧"}), 404
    data = request.json or {}
    fmt = data.get("format", "jpg")
    quality = int(data.get("quality", 92))
    rotate = int(data.get("rotate", 0))
    denoise = int(data.get("denoise", 0))
    prefix = data.get("prefix", "IMG_")
    suffix = data.get("suffix", "index")
    scan_id = scan_state.get("scan_id", datetime.now().strftime("%Y%m%d_%H%M%S"))

    frame = post_process_frame(current_frame.copy(), {"rotate": rotate, "denoise": denoise})
    idx = scan_state["scan_count"] + 1
    preview_path = save_preview(frame, scan_id, idx, fmt)
    filepath = get_output_filename(fmt, prefix, suffix)
    save_frame_to_file(frame, filepath, fmt, quality)

    scan_state["scan_count"] = idx
    if "scan_files" not in scan_state:
        scan_state["scan_files"] = []
    scan_state["scan_files"].append(str(filepath))

    return jsonify({"success": True, "index": idx, "path": str(filepath),
                     "preview": preview_path, "filename": filepath.name,
                     "width": frame.shape[1], "height": frame.shape[0]})


@app.route("/api/scan/status")
def api_scan_status():
    return jsonify({
        "scanning": scan_state["is_scanning"],
        "mode": scan_state.get("mode", "manual"),
        "scan_count": scan_state["scan_count"],
        "scan_id": scan_state.get("scan_id", ""),
        "files": scan_state.get("scan_files", []),
        "last_scan_time": scan_state.get("last_scan_time", 0),
    })


@app.route("/api/scan/list")
def api_scan_list():
    files = []
    for f in sorted(OUTPUT_DIR.iterdir()):
        if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png", ".bmp", ".gif"):
            stat = f.stat()
            files.append({
                "name": f.name, "path": str(f), "size": stat.st_size,
                "time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
    return jsonify({"files": files, "count": len(files)})


@app.route("/api/scan/preview_list")
def api_scan_preview_list():
    files = []
    for f in sorted(PREVIEW_DIR.iterdir()):
        if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png"):
            files.append({"name": f.name, "path": str(f), "url": f"/api/scan/preview/{f.name}"})
    return jsonify({"files": files, "count": len(files)})


@app.route("/api/scan/preview/<filename>")
def api_scan_preview_file(filename):
    return send_from_directory(str(PREVIEW_DIR), filename)


@app.route("/api/scan/file")
def api_scan_get_file():
    """通过 query 参数 ?path=xxx 下载/查看扫描文件(支持 Windows 反斜杠路径)。"""
    filepath = request.args.get("path", "")
    if filepath and os.path.exists(filepath):
        return send_file(filepath, as_attachment=False)
    return jsonify({"success": False, "message": "文件不存在"}), 404


@app.route("/api/scan/papers_file")
def api_scan_papers_file():
    """查看证件扫描文件 ?name=xxx 或 ?path=xxx"""
    name = request.args.get("name", "")
    path = request.args.get("path", "")
    if path and os.path.exists(path):
        return send_file(path, as_attachment=False)
    if name:
        full = PAPERS_DIR / name
        if full.exists():
            return send_file(str(full), as_attachment=False)
    return jsonify({"success": False, "message": "文件不存在"}), 404


@app.route("/api/scan/delete", methods=["POST"])
def api_scan_delete():
    data = request.json or {}
    paths = data.get("paths", [])
    deleted = 0
    for p in paths:
        try:
            if os.path.exists(p):
                os.remove(p)
                deleted += 1
        except Exception:
            pass
    return jsonify({"success": True, "deleted": deleted})


@app.route("/api/scan/clear", methods=["POST"])
def api_scan_clear():
    data = request.json or {}
    target = data.get("target", "all")
    count = 0
    dirs = []
    if target in ("all", "output"):
        dirs.append(OUTPUT_DIR)
    if target in ("all", "preview"):
        dirs.append(PREVIEW_DIR)
    for d in dirs:
        for f in d.iterdir():
            if f.is_file():
                f.unlink()
                count += 1
    scan_state["scan_count"] = 0
    scan_state["scan_files"] = []
    return jsonify({"success": True, "deleted": count})


# ========================= 多张合成 PDF =========================

@app.route("/api/scan/export_pdf", methods=["POST"])
def api_scan_export_pdf():
    data = request.json or {}
    paths = data.get("paths", [])
    output_name = data.get("output", f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")

    if not paths:
        all_files = sorted(OUTPUT_DIR.glob("*.jpg")) + sorted(OUTPUT_DIR.glob("*.png"))
        paths = [str(f) for f in all_files]

    if not paths:
        return jsonify({"success": False, "message": "无图片可导出"}), 400

    try:
        from PIL import Image as PILImage
        images = []
        for p in paths:
            if os.path.exists(p):
                img = PILImage.open(p)
                if img.mode != "RGB":
                    img = img.convert("RGB")
                images.append(img)
        if not images:
            return jsonify({"success": False, "message": "无有效图片"}), 400

        pdf_path = OUTPUT_DIR / output_name
        images[0].save(str(pdf_path), "PDF", save_all=True, append_images=images[1:])
        return jsonify({"success": True, "path": str(pdf_path), "pages": len(images)})
    except ImportError:
        return jsonify({"success": False, "message": "需要安装 Pillow: pip install Pillow"}), 500
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ========================= 证件扫描 =========================

@app.route("/api/scan/papers", methods=["POST"])
def api_scan_papers():
    if current_frame is None:
        return jsonify({"success": False, "message": "无可用帧"}), 404
    data = request.json or {}
    papers_type = data.get("papers_type", "身份证")
    side = data.get("side", "front")
    fmt = data.get("format", "jpg")
    quality = int(data.get("quality", 92))

    frame = current_frame.copy()
    scan_id = scan_state.get("scan_id", datetime.now().strftime("%Y%m%d_%H%M%S"))

    if papers_type == "身份证":
        if side == "front":
            filename = f"id_card_front_{scan_id}.{fmt.lower()}"
        else:
            filename = f"id_card_back_{scan_id}.{fmt.lower()}"
    elif papers_type == "护照":
        filename = f"passport_{scan_id}.{fmt.lower()}"
    else:
        filename = f"{papers_type}_{scan_id}.{fmt.lower()}"

    filepath = PAPERS_DIR / filename
    save_frame_to_file(frame, filepath, fmt, quality)

    return jsonify({"success": True, "path": str(filepath), "filename": filename,
                     "papers_type": papers_type, "side": side})


@app.route("/api/scan/papers_concat", methods=["POST"])
def api_scan_papers_concat():
    data = request.json or {}
    front_path = data.get("front_path", "")
    back_path = data.get("back_path", "")
    direction = data.get("direction", "vertical")
    fmt = data.get("format", "jpg")

    if not os.path.exists(front_path) or not os.path.exists(back_path):
        return jsonify({"success": False, "message": "证件图片不存在"}), 400

    front = cv2.imdecode(np.fromfile(front_path, dtype=np.uint8), cv2.IMREAD_COLOR)
    back = cv2.imdecode(np.fromfile(back_path, dtype=np.uint8), cv2.IMREAD_COLOR)

    if direction == "vertical":
        max_w = max(front.shape[1], back.shape[1])
        front_resized = cv2.copyMakeBorder(front, 0, 0, 0, max_w - front.shape[1], cv2.BORDER_CONSTANT)
        back_resized = cv2.copyMakeBorder(back, 0, 0, 0, max_w - back.shape[1], cv2.BORDER_CONSTANT)
        concat = np.vstack([front_resized, back_resized])
    else:
        max_h = max(front.shape[0], back.shape[0])
        front_resized = cv2.copyMakeBorder(front, 0, max_h - front.shape[0], 0, 0, cv2.BORDER_CONSTANT)
        back_resized = cv2.copyMakeBorder(back, 0, max_h - back.shape[0], 0, 0, cv2.BORDER_CONSTANT)
        concat = np.hstack([front_resized, back_resized])

    filename = f"idcard_concat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{fmt.lower()}"
    filepath = PAPERS_DIR / filename
    save_frame_to_file(concat, filepath, fmt)
    return jsonify({"success": True, "path": str(filepath), "filename": filename})


@app.route("/api/scan/papers_list")
def api_scan_papers_list():
    files = []
    for f in sorted(PAPERS_DIR.iterdir()):
        if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png"):
            files.append({"name": f.name, "path": str(f), "size": f.stat().st_size})
    return jsonify({"files": files, "count": len(files)})


# ========================= 视频录制 =========================

recording_state = {"is_recording": False, "writer": None, "thread": None, "stop_event": threading.Event()}


@app.route("/api/record/start", methods=["POST"])
def api_record_start():
    if recording_state["is_recording"]:
        return jsonify({"success": False, "message": "已在录制中"}), 400
    if not is_running:
        return jsonify({"success": False, "message": "摄像头未开启"}), 400

    data = request.json or {}
    fmt = data.get("format", "mp4")
    fps = int(data.get("fps", 15))

    prefix = ui_config["output"].get("name_way", {}).get("prefix", "VID_")
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}{now_str}.{fmt.lower()}"
    filepath = OUTPUT_DIR / filename

    fourcc = cv2.VideoWriter_fourcc(*("mp4v" if fmt == "mp4" else "XVID"))
    w = int(video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    writer = cv2.VideoWriter(str(filepath), fourcc, fps, (w, h))

    if not writer.isOpened():
        return jsonify({"success": False, "message": "无法创建视频文件"}), 500

    recording_state["is_recording"] = True
    recording_state["writer"] = writer
    recording_state["filepath"] = str(filepath)
    recording_state["stop_event"] = threading.Event()

    def record_loop():
        while not recording_state["stop_event"].is_set():
            if current_frame is not None:
                recording_state["writer"].write(current_frame)
            time.sleep(1.0 / fps)
        recording_state["writer"].release()
        recording_state["is_recording"] = False

    recording_state["thread"] = threading.Thread(target=record_loop, daemon=True)
    recording_state["thread"].start()

    return jsonify({"success": True, "path": str(filepath)})


@app.route("/api/record/stop", methods=["POST"])
def api_record_stop():
    if not recording_state["is_recording"]:
        return jsonify({"success": False, "message": "未在录制中"}), 400
    recording_state["stop_event"].set()
    time.sleep(0.5)
    return jsonify({"success": True, "path": recording_state.get("filepath", "")})


# ========================= UI Config =========================

@app.route("/api/ui_config", methods=["GET", "POST"])
def api_ui_config():
    global ui_config
    if request.method == "POST":
        data = request.json or {}
        for key, value in data.items():
            if key in ui_config:
                if isinstance(ui_config[key], dict) and isinstance(value, dict):
                    ui_config[key].update(value)
                else:
                    ui_config[key] = value
        return jsonify({"success": True, "config": ui_config})
    return jsonify({"config": ui_config})


if __name__ == "__main__":
    load_config()
    ensure_dirs()
    print(f"GK122 高拍仪 API 服务启动中...")
    print(f"设备配置: {DEVICE_NAME}")
    print(f"推荐分辨率: {config['recommend_resolution']}")
    print(f"输出目录: {OUTPUT_DIR}")
    print(f"访问 http://localhost:5000 打开前端页面")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
