# gk122

GK122 高拍仪前端调用代码，基于反编译得力高拍仪 v1.5.9 提取的摄像接口开发。

## 项目结构

- `web/` — 前端代码 + Python Flask 后端
  - `index.html` — 纯前端方案（浏览器 getUserMedia 直接调用 UVC 摄像头）
  - `server.py` — Python Flask 后端（OpenCV + DirectShow）
  - `capture.yaml` — GK122 设备配置
  - `static/index.html` — 后端 API 调用前端页面
- `src2/` — 反编译的 Python 源码
  - `algorithm/video/dshow/` — DirectShow COM 接口
  - `pyapp/api/` — 摄像头核心类 DeliCapture

## 快速使用

### 方案一：纯前端
直接用浏览器打开 `web/index.html`

### 方案二：Python 后端
```bash
cd web
pip install flask flask-cors opencv-python pyyaml
python server.py
# 浏览器打开 http://localhost:5000
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | /api/devices | 枚举视频设备 |
| POST | /api/start | 开启摄像头 |
| POST | /api/stop | 停止摄像头 |
| GET  | /api/stream | MJPEG 视频流 |
| GET  | /api/frame | 单帧 JPEG |
| POST | /api/capture | 拍照下载 |
| POST | /api/settings | 设置图像参数 |
| POST | /api/rotate | 旋转画面 |
