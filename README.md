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
pip install -r requirements.txt
python server.py
# 浏览器打开 http://localhost:5000
```

`cv2-enumerate-cameras` 1.3.3+ 用来读取 Windows DirectShow 的真实设备名称。它可以让程序排除
OBS Virtual Camera 等虚拟设备，并把 OpenCV 索引准确映射到 GK122。更新代码后请务必重新执行
上述安装命令。

## 摄像头选择与排障

- “开启 GK122”和“一键启动 GK122”都会按 DirectShow FriendlyName 精确选择 GK122/GK122a，不再误开 OBS。
- 设备列表阶段不会逐个打开摄像头；这与原厂 v1.5.9 的行为一致，也避免探测后驱动来不及重新初始化。
- 后端只有收到真实首帧后才会显示“已连接”；如果设备被微信、OBS、浏览器等程序占用，会直接返回错误。
- 4608×3456 无法出帧时，程序会依次回退到设备配置中的推荐分辨率。
- 取流参数按原厂顺序写入：宽度、高度、自动曝光、MJPG、亮度/对比度/锐度。
- 如果设备列表仍无法显示真实名称，请确认在 `web` 目录执行过 `pip install -r requirements.txt`。
- 失败时打开 `http://localhost:5000/api/diagnostics` 可查看枚举名称、协商分辨率、FOURCC 和逐次读帧结果。

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
