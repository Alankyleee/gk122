import cv2
import yaml
import threading
import time
import os
import base64
from flask import Flask, jsonify, request, Response, send_from_directory
from flask_cors import CORS
from pathlib import Path

BASE_DIR = Path(__file__).parent
CAPTURE_YAML = BASE_DIR / "capture.yaml"
DEVICE_NAME = "GK122"

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
config = None


def load_config():
    global config
    if CAPTURE_YAML.exists():
        with open(CAPTURE_YAML, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        config = data.get(DEVICE_NAME, {})
    else:
        config = {
            "recommend_resolution": [3264, 2448],
            "backup_resolution": [2048, 1536],
            "recommend_fourcc": "MJPG",
            "recommend_light": 0,
            "recommend_contrast": 32,
            "recommend_sharpen": 2,
            "resolution": {
                "doc_scan": [
                    [4608, 3456], [4328, 3246], [4032, 3024],
                    [3668, 2751], [3264, 2448], [2592, 1944],
                    [2048, 1536], [1920, 1080], [1600, 1200],
                ],
                "video_recording": [
                    [2048, 1536], [1600, 1200], [1920, 1080], [1280, 720],
                ],
            },
        }


def list_devices():
    devices = []
    for i in range(10):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            name = f"摄像头 {i}"
            try:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                ret, _ = cap.read()
                if ret:
                    name = f"视频设备 {i}"
            except Exception:
                pass
            devices.append({"index": i, "name": name})
            cap.release()
    return devices


def apply_settings(cap, settings=None):
    if not cap or not cap.isOpened():
        return False

    s = settings or {}
    width = s.get("width", config["recommend_resolution"][0])
    height = s.get("height", config["recommend_resolution"][1])
    fourcc_str = s.get("fourcc", config.get("recommend_fourcc", "MJPG"))
    brightness = s.get("brightness", config.get("recommend_light", 0))
    contrast = s.get("contrast", config.get("recommend_contrast", 32))
    sharpness = s.get("sharpness", config.get("recommend_sharpen", 2))
    saturation = s.get("saturation", 64)

    fourcc = cv2.VideoWriter_fourcc(*fourcc_str)
    cap.set(cv2.CAP_PROP_FOURCC, fourcc)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_BRIGHTNESS, brightness)
    cap.set(cv2.CAP_PROP_CONTRAST, contrast)
    cap.set(cv2.CAP_PROP_SHARPNESS, sharpness)
    cap.set(cv2.CAP_PROP_SATURATION, saturation)
    cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
    return True


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
            if time.time() - last_error_time > 5:
                if error_count > 50:
                    print("摄像头读取错误过多,已停止")
                    break
                last_error_time = time.time()
                error_count = 0
            time.sleep(0.05)
            continue

        current_frame = frame
        frame_count += 1

        ret_jpg, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if ret_jpg:
            current_frame_jpeg = buf.tobytes()

        time.sleep(0.02)


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/devices")
def api_devices():
    devices = list_devices()
    return jsonify({"devices": devices, "count": len(devices)})


@app.route("/api/config")
def api_config():
    return jsonify({
        "device": DEVICE_NAME,
        "config": config,
    })


@app.route("/api/start", methods=["POST"])
def api_start():
    global video_capture, is_running, capture_thread, device_index

    data = request.json or {}
    device_index = int(data.get("index", 0))
    width = int(data.get("width", config["recommend_resolution"][0]))
    height = int(data.get("height", config["recommend_resolution"][1]))

    with capture_lock:
        if video_capture and video_capture.isOpened():
            video_capture.release()
            video_capture = None

        video_capture = cv2.VideoCapture(device_index, cv2.CAP_DSHOW)
        if not video_capture.isOpened():
            return jsonify({"success": False, "message": "无法打开摄像头"}), 400

        apply_settings(video_capture, {"width": width, "height": height})

        actual_w = int(video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

        is_running = True
        if not capture_thread or not capture_thread.is_alive():
            capture_thread = threading.Thread(target=capture_loop, daemon=True)
            capture_thread.start()

    return jsonify({
        "success": True,
        "width": actual_w,
        "height": actual_h,
        "message": "摄像头已开启",
    })


@app.route("/api/stop", methods=["POST"])
def api_stop():
    global is_running, video_capture

    is_running = False
    time.sleep(0.2)

    with capture_lock:
        if video_capture:
            video_capture.release()
            video_capture = None

    return jsonify({"success": True, "message": "摄像头已停止"})


@app.route("/api/status")
def api_status():
    with capture_lock:
        opened = video_capture and video_capture.isOpened()
        w = h = 0
        if opened:
            w = int(video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

    return jsonify({
        "is_opened": bool(opened),
        "width": w,
        "height": h,
        "frame_count": frame_count,
        "running": is_running,
    })


@app.route("/api/settings", methods=["POST"])
def api_settings():
    data = request.json or {}
    with capture_lock:
        if video_capture and video_capture.isOpened():
            apply_settings(video_capture, data)
            w = int(video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            return jsonify({
                "success": True,
                "width": w,
                "height": h,
                "settings": {
                    "brightness": int(video_capture.get(cv2.CAP_PROP_BRIGHTNESS)),
                    "contrast": int(video_capture.get(cv2.CAP_PROP_CONTRAST)),
                    "sharpness": int(video_capture.get(cv2.CAP_PROP_SHARPNESS)),
                    "saturation": int(video_capture.get(cv2.CAP_PROP_SATURATION)),
                },
            })
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
    return jsonify({
        "success": True,
        "image": "data:image/jpeg;base64," + b64,
        "width": current_frame.shape[1] if current_frame is not None else 0,
        "height": current_frame.shape[0] if current_frame is not None else 0,
    })


@app.route("/api/stream")
def api_stream():
    def gen():
        while True:
            if current_frame_jpeg:
                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n"
                       b"Content-Length: " + str(len(current_frame_jpeg)).encode() + b"\r\n\r\n"
                       + current_frame_jpeg + b"\r\n")
            time.sleep(0.05)

    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/api/capture", methods=["POST"])
def api_capture():
    if current_frame is None:
        return jsonify({"success": False, "message": "无可用帧"}), 404

    data = request.json or {}
    quality = int(data.get("quality", 92))
    fmt = data.get("format", "jpg")

    if fmt == "png":
        ext = ".png"
        params = [cv2.IMWRITE_PNG_COMPRESSION, 3]
    elif fmt == "bmp":
        ext = ".bmp"
        params = []
    else:
        ext = ".jpg"
        params = [cv2.IMWRITE_JPEG_QUALITY, quality]

    ret, buf = cv2.imencode(ext, current_frame, params)
    if not ret:
        return jsonify({"success": False, "message": "编码失败"}), 500

    return Response(
        buf.tobytes(),
        mimetype=f"image/{fmt.replace('jpg', 'jpeg')}",
        headers={"Content-Disposition": f'attachment; filename="gk122_capture_{int(time.time())}{ext}"'},
    )


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


if __name__ == "__main__":
    load_config()
    print(f"GK122 高拍仪 API 服务启动中...")
    print(f"设备配置: {DEVICE_NAME}")
    print(f"推荐分辨率: {config['recommend_resolution']}")
    print(f"访问 http://localhost:5000 打开前端页面")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
