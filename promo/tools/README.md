# 宣传片制作管线

这条管线**不含任何素材文件**——画面、字幕、配乐、音效、封面全部由代码生成。
本目录是实际使用的那一套脚本（保留了原样，路径按下方说明改一下即可复用）。

## 依赖

- Node.js ≥ 18（用了内置 `WebSocket`，无需 npm 依赖）
- Chrome / Edge（用于无头渲染）
- ffmpeg（libx264 + AAC）
- Python 3 + numpy + Pillow

## 文件

| 文件 | 作用 |
| --- | --- |
| `cdp.mjs` | 极简 Chrome DevTools Protocol 客户端（Node 内置 WebSocket，零依赖） |
| `rec4.mjs` | 分镜录制器：`Page.startScreencast` 抓帧 + 派发真实鼠标事件驱动页面 UI |
| `withchrome.sh` | 起一个临时无头 Chrome、跑完脚本再关掉（避免长驻进程被回收） |
| `overlays.py` | 用 Pillow 画标题 / 字幕条 / 结尾卡（带 alpha 的 PNG） |
| `music.py` | numpy 合成配乐，并按页面 WebAudio 参数复刻鹈鹕鸣叫 |
| `cover.py` | 合成 B 站封面（1146×717） |
| `encode.py` | 拼帧 + 叠字幕 + 混音 → ffmpeg 出片 |

## 关键设计

页面主循环里 `rdt = min(0.05, 真实帧间隔)`。当渲染低于 20 fps 时该钳位**恒定生效**，
于是"每渲染一帧 = 推进 0.05 s 仿真"——这正好让实时抓帧得到的每一帧都对应相同的仿真时长，
成片速度与真实时间完全一致。因此每帧在编码时统一给 `1/20 s` 的时长即可。

每个镜头单独加载一次页面：既避免长驻进程被回收，也让单段仿真位移远小于一圈赛程
（`index.html` 存在一个"跑满一圈必崩"的缺陷，见 `docs/TEST-REPORT.md` 6.5 节）。

## 复用步骤

1. 改 `rec4.mjs` 顶部的 `PAGE` 常量为你的页面 URL，按需改 `SEGS` 分镜表
   （`url` 是页面的调试参数，`actions` 是要派发的交互，时间以成片秒计）
2. `./withchrome.sh rec4.mjs s1-chase` 逐镜头录制 → `frames/<id>/*.jpg`
3. `python overlays.py` 生成字幕层
4. `python encode.py` 出片（会自动调用 `music.py` 生成配乐）
5. `python cover.py` 出封面

> 注：脚本里的输出路径按 `_video/` 作为工作目录，直接复用请把 `PAGE`、
> `frames/`、`overlays/` 的相对关系一起搬到你的工作目录。
