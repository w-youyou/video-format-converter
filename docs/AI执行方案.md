# AI 执行方案（查阅后直接写代码）

> **写代码请只读 `docs/完整需求与执行方案.md`。** 本文是较早的配方稿，其中 `out_time_ms` 当毫秒、`ffprobe --`、杀进程树立刻删文件、硬件加速替换编码器名等条款**已经作废**。冲突时以完整规格为准。
>
> 本文把 `工程规则.md` + `阶段任务.md` 展开成可执行配方。不新增功能、不改阶段顺序、不重开选型。
>
> | 冲突时优先级 | 文件 |
> |---|---|
> | 1 约束 | `docs/工程规则.md` |
> | 2 本阶段做什么 | `docs/阶段任务.md` |
> | 3 怎么实现 | **本文** |
> | 4 已锁定取舍 | `docs/DECISIONS.md` |
> | 5 做到哪了 | `docs/PHASE_STATUS.md` |

---

## 0. 会话启动（每次都做，不要跳）

1. 打开 `docs/PHASE_STATUS.md`，找到**第一个状态不是 `done` 的阶段**（现在全是 `todo`，所以是 **S0**）。
2. 把该行改成 `doing`。
3. 只实现该阶段「本阶段文件 + 任务清单」。清单外一律不做。
4. 按本文对应章节的接口/文案/命令实现。
5. 用本文「验证」命令在本机跑通验收。
6. 验收通过：状态改 `done`，写完成说明；追加 `SESSION_SUMMARY.md`。
7. **停下。** 用户没说「继续下一阶段」就不要开始下一个 S。

禁止：网页 UI、tkinter、CLI 主界面、`shell=True`、UI 线程同步 ffmpeg、主动加 P2、跳阶段、改目录结构。

---

## 1. 产品与锁定栈（禁止再讨论）

**一句话**：给人用的 Windows 桌面客户端——打开就能看懂，能看视频信息与封面，能用 ffmpeg 命令行把视频转成常用格式。

| 层 | 锁定 | 不要用 |
|---|---|---|
| 语言 | Python 3.10+（Windows） | 别的主力语言 |
| UI | PySide6 | tkinter / 网页 / Streamlit / Gradio / Electron |
| 元数据 | `ffprobe` CLI + JSON | 猜文件名；ffmpeg C API |
| 缩略图 | `ffmpeg -frames:v 1` | Qt 多媒体当默认方案 |
| 转换 | `ffmpeg` CLI | `ffmpeg-python` 当核心 |
| 长任务 | `QProcess`（D-02） | UI 线程 `subprocess.run` |
| 短命令 | `app/core/command_runner.py` | `os.system` / `shell=True` |
| 配置 | `%APPDATA%/VideoFormatConverter/settings.json` | 注册表 / 云同步 |
| 单测 | 标准库 `unittest`（不为此加 pytest） | 依赖真视频才能跑的 parse 测试 |
| 打包 | PyInstaller（S9） | 把 ffmpeg 打进仓库或 exe |

许可证：PySide6，不用 PyQt6。

---

## 2. 当前仓库事实

截至本文写入时：

- **没有应用代码**，只有 `docs/` 与 `.cursor/rules/`
- `PHASE_STATUS.md`：S0–S10 全是 `todo`
- 已锁定决策：D-01 PySide6、D-02 QProcess、D-03 砍 P2、D-04 硬件加速可回退、D-05 ffmpeg 外置、D-06 不做的 P2 清单
- 过程文档是模板 + 会话 0；S8 之前不要假装填了实测

下一步：**S0 脚手架**。

---

## 3. 目标目录（按阶段创建，禁止另起炉灶）

```
video-format-converter/
  AGENTS.md
  README.md                      # S9 才写产品 README，S0 不要先写长文
  requirements.txt               # S0：仅 PySide6>=6.6；S9 再核对
  .gitignore                     # S0
  app/
    __init__.py
    main.py                      # S0 空窗；S1 换成 MainWindow
    settings.py                  # S7
    ui/
      __init__.py
      main_window.py             # S1 起
      widgets.py                 # S1 可建：拖放区、信息表、缩略图
    core/                        # 禁止 import PySide6
      __init__.py
      media_info.py              # S3
      command_runner.py          # S2
      which_ffmpeg.py            # S2
      ffprobe_service.py         # S3
      ffmpeg_service.py          # S4 抽帧；S5 转换；S6 进度
      presets.py                 # S5
    workers/
      __init__.py
      probe_worker.py            # S3
      thumb_worker.py            # S4
      convert_worker.py          # S5；S6 解析进度
  assets/                        # S0 .gitkeep；占位图可后补
  tests/
    __init__.py
    test_ffprobe_parse.py        # S3
    test_presets.py              # S5
    test_progress_parse.py       # S6
    fixtures/                    # S8 才生成样例视频
  docs/
    screenshots/                 # S8
```

分层：

- `ui/` **禁止**拼接 ffmpeg 参数，只调 `core` / `workers`
- `core/` **禁止**依赖 PySide6
- `workers/` 可以同时用 PySide6 与 `core`；参数仍由 `core` 构造
- 所有外部命令：`list[str]`，完整 argv 必须能写入日志并复制到终端复现

---

## 4. 公开接口（按阶段实现，签名不要擅自改名）

### 4.1 `app/core/media_info.py`（S3）

```python
from dataclasses import dataclass

@dataclass
class MediaInfo:
    path: str
    filename: str
    size_bytes: int
    duration_sec: float | None = None
    width: int | None = None
    height: int | None = None
    video_codec: str | None = None
    audio_codec: str | None = None
    fps: float | None = None
    bit_rate: int | None = None
    warning: str | None = None
```

### 4.2 `app/core/command_runner.py`（S2）

```python
@dataclass
class CommandResult:
    argv: list[str]
    returncode: int
    stdout: str
    stderr: str
    duration_ms: int

def run(argv: list[str], timeout: float = 30.0) -> CommandResult:
    ...
```

实现要点：

- `subprocess.run(argv, shell=False, capture_output=True, timeout=timeout, text=True, encoding="utf-8", errors="replace")`
- Windows 加 `creationflags=subprocess.CREATE_NO_WINDOW`（没有控制台闪窗）
- 超时：返回或抛出后转成可展示错误，**不要让整个应用崩**
- 禁止 `shell=True`；禁止把 argv 拼成一根字符串再执行

### 4.3 `app/core/which_ffmpeg.py`（S2）

```python
def find_ffmpeg() -> str | None: ...
def find_ffprobe() -> str | None: ...
```

查找顺序（每个可执行文件各自走一遍）：

1. 环境变量 `VFC_FFMPEG` / `VFC_FFPROBE`（存在且文件存在才用）
2. `shutil.which("ffmpeg")` / `shutil.which("ffprobe")`（Windows 会匹配 `.exe`）
3. `C:\ffmpeg\bin\ffmpeg.exe` 与 `C:\ffmpeg\bin\ffprobe.exe`
4. `C:\Program Files\ffmpeg\bin\ffmpeg.exe` 与 `C:\Program Files\ffmpeg\bin\ffprobe.exe`

返回**绝对路径**字符串；找不到返回 `None`。不要自动下载。

### 4.4 `app/core/ffprobe_service.py`（S3）

```python
def build_cmd(ffprobe: str, path: str) -> list[str]:
    return [ffprobe, "-v", "error", "-show_format", "-show_streams", "-of", "json", "--", path]

def parse(stdout: str, path: str, size_bytes: int) -> MediaInfo: ...
```

- 若本机 ffprobe 因 `--` 失败：去掉 `--`，path 放最后；在 `DECISIONS.md` 记 **D-07**
- `parse`：从 `format` / `streams` 取时长、宽高、`codec_name`、`avg_frame_rate`、`bit_rate`
- 缺字段 → `None`，不要抛；部分失败可填 `warning` 人话
- 视频流：`codec_type == "video"` 且不是封面图（若有 `disposition.attached_pic` 则跳过优先选真正视频轨）
- `avg_frame_rate` 形如 `"30000/1001"`：分子/分母，分母为 0 则 `None`

### 4.5 `app/core/presets.py`（S5）

```python
@dataclass(frozen=True)
class Preset:
    id: str
    name: str
    description: str
    suffix: str
    args: list[str]

def all_presets() -> list[Preset]: ...
def get_preset(preset_id: str) -> Preset: ...
```

必须这 4 个，默认选中第一个：

| id | name | suffix | args |
|---|---|---|---|
| `mp4_compat` | 通用 MP4 | `.mp4` | `-c:v libx264 -preset medium -crf 23 -c:a aac -b:a 128k -movflags +faststart` |
| `mp4_small` | 压缩体积 | `.mp4` | `-c:v libx264 -preset slow -crf 28 -c:a aac -b:a 96k -movflags +faststart` |
| `mp3_audio` | 提取音频 MP3 | `.mp3` | `-vn -c:a libmp3lame -q:a 2` |
| `copy_mux` | 原画转封装 | `.mp4` | `-c copy` |

`args` 存成 `list[str]`，不要一整根字符串。`description` 给普通人看，例如「微信和播放器一般都能打开」。

### 4.6 `app/core/ffmpeg_service.py`（S4 起）

```python
def build_thumbnail_cmd(ffmpeg: str, input_path: str, output_png: str, duration_sec: float | None) -> list[str]: ...

def build_convert_cmd(
    ffmpeg: str,
    input_path: str,
    output_path: str,
    preset: Preset,
    *,
    overwrite: bool = False,
    with_progress: bool = False,
) -> list[str]: ...

def parse_progress_line(line: str) -> int | None:
    """从一行里解析 out_time_ms；没有则 None。"""

def percent_from_out_time_ms(out_time_ms: int, duration_sec: float) -> int:
    """0–100 整数，四舍五入；duration<=0 时不要除零。"""

def humanize_ffmpeg_error(stderr: str) -> str:
    """1～2 句中文。"""
```

**缩略图命令（先 seek 再 decode）：**

```
[ffmpeg, "-ss", <t>, "-i", input, "-frames:v", "1", "-q:v", "3", "-y", output_png]
```

- 有时长：`t = max(duration_sec * 0.1, 0)`，格式用普通小数（例如 `1.23`），不要科学计数法
- 无时长：`t = 1`
- `output_png` 放系统临时目录，文件名可预测：`vfc_thumb_<pid>.png`；换视频或退出时删除旧文件

**转换命令：**

S5 基础（**不要** `-y`，**不要**进度）：

```
[ffmpeg, "-hide_banner", "-i", input, *preset.args, output]
```

S6 起进度：在 `-hide_banner` 后插入 `-nostats`, `-progress`, `pipe:1`。

覆盖：仅当用户在对话框选「是」后 `overwrite=True`，在 `-i` **之前**插入 `-y`（ffmpeg 全局选项必须在 `-i` 前）。

### 4.7 Worker 信号（名称固定）

`ProbeWorker(QThread)`（S3）

- `finished_ok = Signal(object)`  # MediaInfo
- `failed = Signal(str)`

`ThumbWorker(QThread)`（S4，抽帧可能 >1s 必须后台）

- `finished_ok = Signal(str)`  # png 路径
- `failed = Signal(str)`

`ConvertWorker`（S5，**必须 QProcess**；不要在槽函数里 `subprocess.run`）

- `started = Signal()`
- `log_line = Signal(str)`
- `progress = Signal(int)`       # S6 才发 0–100；S5 可以不发
- `finished_ok = Signal(str)`    # 输出路径
- `failed = Signal(str)`         # 人话
- 方法：`start_convert(argv: list[str])`、`cancel()`

Windows：`QProcess` 用 `setProgram(ffmpeg)` + `setArguments(其余)`；合并通道或分别读 stdout（进度）/ stderr（日志）。取消：杀掉**进程树**（子进程），再删不完整输出。

### 4.8 `app/settings.py`（S7）

路径：`Path(os.environ["APPDATA"]) / "VideoFormatConverter" / "settings.json"`

```json
{
  "last_input_dir": "",
  "last_output_dir": "",
  "last_preset_id": "mp4_compat",
  "window_width": 1100,
  "window_height": 720
}
```

读失败用默认值，不要崩。

---

## 5. 主窗口布局与控件（S1 必须按此，不要改成控制台）

窗口标题：`视频格式转换器`  
初始大小：`1100x720`；最小：`960x640`  
1280×720 下控件不能被裁切。

```
+--------------------------------------------------+
| 顶：拖放/选择文件区（「选择视频」+「或把视频拖到这里」） |
+------------------------+-------------------------+
| 左：缩略图（16:9 占位） | 右：信息表（键值对）        |
+------------------------+-------------------------+
| 底：预设、输出路径、浏览、进度、状态                 |
|     主按钮「开始转换」  次按钮「取消」（默认禁用）     |
|     「详细日志」可折叠，默认收起                     |
+--------------------------------------------------+
```

建议对象名（便于测试与后续接线，不强制 QSS 主题）：

| objectName | 类型 | 文案/行为 |
|---|---|---|
| `dropZone` | 自定义 QWidget | 接受拖放；提示「或把视频拖到这里」 |
| `btnSelect` | QPushButton | 选择视频 |
| `thumbLabel` | QLabel | 灰色底 +「暂无封面」；KeepAspectRatio，禁止拉伸 |
| `infoTable` | QTableWidget 或 QFormLayout | 见信息表行 |
| `presetCombo` | QComboBox | 四个中文名 |
| `outputEdit` | QLineEdit | 输出路径 |
| `btnBrowse` | QPushButton | 浏览… |
| `outputPreview` | QLabel | S7 显示最终文件名；S1 可先不建 |
| `progressBar` | QProgressBar | 初始 0 |
| `statusLabel` | QLabel | 请选择视频 |
| `btnPrimary` | QPushButton | 开始转换 |
| `btnCancel` | QPushButton | 取消；默认 disabled |
| `btnToggleLog` | QPushButton | 详细日志（checkable） |
| `logView` | QPlainTextEdit | 只读；默认 `hide()` |
| `missingBanner` | QLabel | S2 缺 ffmpeg 时显示；默认 hide |

信息表预置行（值先是 `—`；S3 起空字段改为 `未知`）：

文件名、路径、大小、时长、分辨率、视频编码、音频编码、帧率、比特率。

文件对话框过滤器（整串按此）：

```
视频文件 (*.mp4 *.mkv *.mov *.avi *.webm *.flv *.wmv);;所有文件 (*.*)
```

主按钮同一时刻只表达一个动作：

| 状态 | 按钮文字 | 点击 |
|---|---|---|
| 空闲且可转 | `开始转换` | 开始 |
| 转换中 | `转换中…` | 无效（S6-T4） |
| 成功后 | `打开所在文件夹` | 打开资源管理器并尽量选中文件（S6） |
| 成功后次按钮 | `打开文件` | S7 才加，系统默认播放器 |

危险操作（取消、覆盖、退出进行中任务）必须二次确认或可撤销。

---

## 6. 中文文案字典（不要改成开发者黑话）

| ID | 使用处 | 文案 |
|---|---|---|
| W01 | 窗口标题 | 视频格式转换器 |
| W02 | 选择按钮 | 选择视频 |
| W03 | 拖放提示 | 或把视频拖到这里 |
| W04 | 缩略图空 | 暂无封面 |
| W05 | 主按钮 | 开始转换 |
| W06 | 主按钮中 | 转换中… |
| W07 | 主按钮完成 | 打开所在文件夹 |
| W08 | 次按钮 | 取消 |
| W09 | 浏览 | 浏览… |
| W10 | 日志开关 | 详细日志 |
| W11 | 初始状态 | 请选择视频 |
| W12 | 已检测到 | 已检测到 ffmpeg，请选择视频 |
| W13 | 缺工具 | 未找到 ffmpeg/ffprobe。请安装后将其加入 PATH，或设置环境变量 VFC_FFMPEG。 |
| W14 | 转换中 | 正在转换… {n}% |
| W15 | 完成 | 转换完成 |
| W16 | 取消 | 已取消 |
| W17 | 文件已存在（S5） | 输出文件已存在，未覆盖。请更换路径或在确认后覆盖。 |
| W18 | 覆盖问句 | 文件已存在，是否覆盖？ |
| W19 | 关闭确认 | 正在转换，确定要退出吗？退出将取消当前任务。 |
| W20 | 无视频轨/损坏 | 无法读取视频信息。请确认这是可播放的视频文件。 |
| W21 | copy 失败 | 该文件不能无重编码转到 MP4，请改用「通用 MP4」。 |
| W22 | 输出占用 | 无法写入输出文件。请关闭正在播放它的程序后重试。 |
| W23 | 硬件回退 | 硬件加速失败，已改用软件编码 |
| W24 | 抽帧失败 | 无法生成封面：{reason} |
| W25 | 缺字段 | 未知 |
| W26 | 未选输出 | 请先选择输出位置 |
| W27 | 拖入多文件 | 一次只能转换一个文件，已使用第一个视频。 |
| W28 | 拖入非视频 | 请拖入视频文件。 |
| W29 | 失败兜底 | 转换失败。可展开「详细日志」查看详情。 |
| W30 | 打开文件（S7） | 打开文件 |

格式化（S3）：

- 大小：`12.3 MB`（1024 进制，保留 1 位小数；<1024B 显示 B）
- 时长：`HH:MM:SS`（例如 `00:01:23`）
- 分辨率：`1920×1080`（乘号用 `×` 不是 `x`）
- 帧率：`30 fps`（整数则不要 `30.0`；非整数保留 2 位）
- 比特率：`2.1 Mbps`（来自 bps）

长路径：界面省略，`setToolTip` 给全文。

---

## 7. ffmpeg 命令模板（必须 list[str]，路径原样传入）

**探测：**

```
ffprobe -v error -show_format -show_streams -of json -- <path>
```

**抽帧：**

```
ffmpeg -ss <t> -i <input> -frames:v 1 -q:v 3 -y <tmp.png>
```

**转换（S5）：**

```
ffmpeg -hide_banner -i <input> <preset.args...> <output>
```

**转换（S6+）：**

```
ffmpeg -hide_banner -nostats -progress pipe:1 -i <input> <preset.args...> <output>
```

有覆盖：

```
ffmpeg -y -hide_banner -nostats -progress pipe:1 -i <input> ... <output>
```

进度：从 stdout 读 `out_time_ms=` 或 `out_time=`，用 `MediaInfo.duration_sec` 算百分比。解析失败 → 进度条 busy（`setRange(0,0)`），不要卡在 0。

`copy_mux` 非 0 退出：用 W21，不要丢原始 stderr 给用户当唯一说明（原始内容进日志）。

---

## 8. 线程与进程（写错就是假死）

| 任务 | 方式 | 阶段 |
|---|---|---|
| which / 版本探测 | `command_runner.run`，短超时 | S2 |
| ffprobe | `ProbeWorker`，禁止 UI 线程 | S3 |
| 抽帧 | `ThumbWorker` | S4 |
| 转换 | `ConvertWorker` + `QProcess` | S5 |
| 进度 | 读 QProcess stdout | S6 |
| 取消 | 杀进程树 + 删不完整输出 | S6 |

转换中：禁用主按钮与文件选择；启用取消。窗口必须仍可拖动。

UI 槽函数里出现 `subprocess.run([...ffmpeg...])` = 不合格，记 `AI_FEEDBACK.md`。

---

## 9. 硬件加速（仅 S7-T4，提前不要做）

仅预设 `mp4_compat` / `mp4_small` 尝试。顺序：`h264_nvenc` → `h264_qsv` → `h264_amf`。

建议探测：`ffmpeg -hide_banner -encoders` 的输出里是否出现上述名字（短命令，走 runner）。不要在 S2–S6 接这条路径。

失败：自动用软件编码重跑同一输出；状态栏 W23。记入 D-04（已有则核对真实性）。无独显机器必须仍能成功。

禁止：界面出现点了不能用的「GPU」开关。

---

## 10. 分阶段配方

每一节都是「打开就能干」。做完验收 → 更新状态 → 停。

验证默认在项目根、PowerShell：

```powershell
python -m app.main
python -m unittest discover -s tests -v
```

### S0 脚手架

**目标**：`python -m app.main` 弹出空白中文标题窗。

**创建文件**：`requirements.txt`、`.gitignore`、`app/__init__.py`、`app/main.py`、`app/ui/__init__.py`、`app/core/__init__.py`、`app/workers/__init__.py`、`assets/.gitkeep`、`tests/__init__.py`

**S0-T1** `requirements.txt` 只写：

```
PySide6>=6.6
```

**S0-T2** `.gitignore` 至少：`.venv/`、`__pycache__/`、`*.pyc`、`.idea/`、`.vscode/`、`dist/`、`build/`、`*.spec`、`tmp/`、`.DS_Store`、输出视频（`*.mp4` 不要全局忽略截图；忽略 `tests/fixtures/*.mp4` 或 `output/`）、不要忽略 `docs/screenshots/*.png`

建议追加：`.venv/`、`venv/`、`Thumbs.db`

**S0-T3** `app/main.py`：`QApplication` + 空 `QMainWindow`，标题 W01，大小 1100x720，最小 960x640，`if __name__ == "__main__"` 调 `main()`。

**不要做**：菜单关于、主题、托盘、打包、业务控件、README 长文。

**验证**：

```powershell
python -m pip install -r requirements.txt
python -m app.main
```

- 弹出「视频格式转换器」
- 关窗后进程退出

**文档**：`PHASE_STATUS` S0=done；`SESSION_SUMMARY` 一节。

**建议提交说明**（仅当用户要求提交）：`feat(S0): 用 PySide6 拉起可关闭的空白主窗口`

---

### S1 客户端主界面骨架

**依赖**：S0 done。  
**文件**：创建 `app/ui/main_window.py`；`app/main.py` 改用 `MainWindow`；可选 `app/ui/widgets.py`。

按第 5 节四区做完。**不要**调 ffmpeg。

- 信息表九行，值 `—`
- 预设四项中文（只是 UI）
- 主按钮「开始转换」；取消禁用；进度 0；状态 W11
- 选择文件：只填路径/文件名，不 probe
- 拖放：`setAcceptDrops`，本阶段只显示路径
- 缩略图灰底 + W04，KeepAspectRatio
- 日志默认看不见

**验证**：人手点「选择视频」、拖一个本地文件；拉窗口到 1280x720 看是否裁切；点「详细日志」应能展开。

**建议提交**：`feat(S1): 搭四区中文主界面并支持选文件与拖放`

---

### S2 检测 ffmpeg / ffprobe

**文件**：`which_ffmpeg.py`、`command_runner.py`；改 `main_window.py`。

启动后检测：

- 都找到：状态 W12；日志里写绝对路径（日志仍默认收起）；主按钮仍应在「还没有视频」时禁用
- 缺一：显示 W13（横幅或状态栏），主按钮禁用，不崩

**不要做**：自动下载；把 ffmpeg 提交进仓库。

**验证**：

- 正常 PATH：启动看到 W12
- 临时改名/移出 PATH 或清环境后再开：出现 W13 且不崩

**建议提交**：`feat(S2): 启动时检测 ffmpeg 并用中文提示缺失`

---

### S3 加载并显示视频信息

**文件**：`media_info.py`、`ffprobe_service.py`、`probe_worker.py`；改主窗口；`tests/test_ffprobe_parse.py`。

选文件/拖放 → Worker probe → 填表。UI 线程禁止阻塞。

- 拿不到的字段：`未知`，禁止空白崩
- 非视频/损坏：仍显示文件名、路径、大小；其它未知；状态 W20
- 单测：最小 JSON fixture，不依赖真视频

**验证**：

```powershell
python -m unittest tests.test_ffprobe_parse -v
```

再手工选一个 mp4：时长/分辨率/编码有真实值；probe 期间可拖动窗口。

**建议提交**：`feat(S3): 用 ffprobe JSON 在后台填充视频信息表`

---

### S4 缩略图

**文件**：`ffmpeg_service.py`（本阶段只要 `build_thumbnail_cmd`）；`thumb_worker.py`；probe 成功后自动抽帧。

- 成功：QPixmap，保持比例居中
- 失败：占位 + W24，信息表不动
- 换文件：先清旧图，防串图
- tmp 在系统临时目录；退出或加载新视频时删旧文件

**不要做**：Qt Multimedia 当默认抽帧。

**验证**：普通 mp4 能看到画面；抽帧时窗口不卡；坏文件有文案。

**建议提交**：`feat(S4): 用 ffmpeg 先 seek 再抽一帧做封面`

---

### S5 转换主路径（P0 核心）

**文件**：`presets.py`；扩展 `ffmpeg_service.build_convert_cmd`；`convert_worker.py`；底部真正可用；`tests/test_presets.py`。

启用主按钮条件：**有视频 + 有 ffmpeg + 有输出路径**。

默认输出：源文件同目录，`{stem}_转换{suffix}`。可浏览更改。

点开始：禁用主按钮与选文件；启用取消（取消逻辑可 S6 接完，**按钮状态本阶段就要对**）。

成功：状态 W15；至少恢复可再转并提示路径（打开文件夹可 S6）。  
失败：stderr 末尾翻成 1～2 句中文 +「可展开日志看详情」。  
已存在：本阶段直接失败 W17，**不要** `-y`。

单测：四个预设 `build_convert_cmd` 返回 `list`、不是一根 shell 字符串、含输入输出路径。

**不要做**：百分比、硬件加速、打包。

**验证**：短 mp4 → 通用 MP4，用系统播放器打开；转换中可拖窗；故意失败不崩。

```powershell
python -m unittest tests.test_presets -v
```

**建议提交**：`feat(S5): 用 ffmpeg CLI 完成后台转换主路径`

---

### S6 转换过程体验

**扩展**：命令加 `-nostats -progress pipe:1`；解析进度；覆盖框；打开文件夹；关闭确认；`tests/test_progress_parse.py`（至少 3 段样例文本）。

- 状态：`正在转换… 37%`，有时长尽量估剩余时间
- 取消：杀进程树，删不完整输出，状态 W16，可立刻再转
- 转换中再点开始：无效
- 已存在：`QMessageBox` W18；否=不开始；是=加 `-y`
- 完成后主按钮 W07：`QDesktopServices` 或 `explorer /select,`
- 再选新文件：按钮回到「开始转换」
- 转换中关窗：确认 W19，确认则先取消再退

**验证**：进度会动；取消后能再转；覆盖文案与行为一致。

```powershell
python -m unittest tests.test_progress_parse -v
```

**建议提交**：`feat(S6): 解析 ffmpeg 进度并支持取消与覆盖确认`

---

### S7 产品优化（P1 六项全做，不要加 P2）

| ID | 做什么 | 对人的好处（写入 DECISIONS） |
|---|---|---|
| S7-T1 | `settings.py` 记住目录/预设/窗体大小 | 第二次打开不用重选 |
| S7-T2 | 底部实时最终文件名 | 转之前就知道文件叫什么 |
| S7-T3 | 「打开文件」+「打开文件夹」 | 马上能检查画质 |
| S7-T4 | NVENC/QSV/AMF，失败回退 | 有独显更快；没独显也能用 |
| S7-T5 | 日志默认收起，含完整命令与退出码 | 普通人不受干扰，出问题能排 |
| S7-T6 | 多文件只取第一个视频，其它人话 | 拖放不会莫名其妙失败 |

**不要做**：批量队列、剪辑、字幕、云、Agent、托盘常驻。

**验证**：关窗重开预设和目录还在；无独显软件编码仍成功。

**建议提交**：`feat(S7): 记住设置并在硬件加速失败时回退软件编码`

---

### S8 实测与证据

**没有截图 = 没测。** 图放 `docs/screenshots/`，小 png，不提交视频。

无素材则生成 2 秒彩条（不要把生成的大视频提交进 git）：

```powershell
New-Item -ItemType Directory -Force tests/fixtures | Out-Null
ffmpeg -f lavfi -i testsrc=duration=2:size=1280x720:rate=30 -f lavfi -i sine=frequency=1000:duration=2 -shortest tests/fixtures/sample.mp4
Copy-Item tests/fixtures/sample.mp4 "tests/fixtures/测试 视频.mp4"
```

按 `TEST_REPORT.md` 跑 T01–T10，填通过/失败/证据文件名。至少 4 张图：信息+缩略图、转换中进度、完成后能播放、一次失败提示。失败当场修，写入「失败与修复」再复测。

**建议提交**：`docs(S8): 补齐 T01-T10 实测记录与截图`

---

### S9 打包与 README

中文 `README.md` 必须含：一句话介绍、主界面截图、Windows + Python 版本、安装 ffmpeg、`python -m app.main`、P0 全写 / P1 只写已做、目录说明、`docs/` 链接、已知限制。

`requirements.txt` 与真实 import 一致。

```powershell
python -m pip install pyinstaller
pyinstaller --noconfirm --windowed --name 视频格式转换器 app/main.py
```

**不把 ffmpeg 打进包。** README 写清本机需要 ffmpeg。核对 D-05。用 exe 走一遍主路径；失败如实写限制。

仓库无巨大视频、无 `.venv`。

**建议提交**：`feat(S9): 补充面向使用者的 README 并用 PyInstaller 打窗口程序`

---

### S10 过程文档收口

- 每个已做阶段在 `SESSION_SUMMARY.md` 至少一节，禁止终章编造
- D-01～D-06 真实（D-07 若发生了也要有）
- `AI_FEEDBACK.md` 至少 5 条真实审查（F-00/F-01 预置不够，要有开发中真实例子）
- 对照 `工程规则.md` 第 14 节 DoD 打勾
- 提交信息按阶段，不要 `update`
- 自己不看代码，按 README 把一个视频转出来

**建议提交**：`docs(S10): 收口决策、会话总结与 AI 审查记录`

---

## 11. 阶段做完后的文档最小集

每个阶段结束必须：

1. `PHASE_STATUS.md`：该阶段 `done` + 一两句完成说明
2. `SESSION_SUMMARY.md` 追加一节（用已有模板：目标 / 实际完成 / 工具 / AI 做了 / 我做了 / 验证 / 未解决）

按需：

- 有取舍 → `DECISIONS.md`
- AI 写错（尤其是本文第 12 节那些）→ `AI_FEEDBACK.md`

**不要**在 S8 之前把 `TEST_REPORT` 全部填成「通过」。

---

## 12. AI 常见错误（出现就拒绝并记 F-xx）

| 错误 | 正确 |
|---|---|
| Streamlit / Gradio / tkinter / 网页当主界面 | PySide6 |
| 按钮槽里 `subprocess.run` 转码 | QProcess / QThread |
| `shell=True` 或 `os.system` | `list[str]` |
| `core` 里 `import PySide6` | core 纯 Python |
| UI 里拼接 ffmpeg 参数 | 只调 `ffmpeg_service.build_*` |
| 默认 `-y` 覆盖 | S5 拒绝；S6 对话框 |
| 抽帧先 `-i` 再 `-ss` | 先 `-ss` 再 `-i` |
| 缺字段抛异常或空白 | `未知` |
| 错误只 `print` | 中文状态栏 + 下一步 |
| 主动做批量/剪辑/Agent | 拒绝，属 P2 |
| 一次做完 S0–S10 | 只做当前阶段 |
| 用英文界面 | 中文 |
| 把命令当主操作暴露在首页 | 放进默认收起的日志 |

---

## 13. 单测最小范围

| 文件 | 阶段 | 必须覆盖 |
|---|---|---|
| `tests/test_ffprobe_parse.py` | S3 | 完整 JSON；缺字段；无视频流 |
| `tests/test_presets.py` | S5 | 四预设 argv 为 list、含 `-i`、输入输出、无 `shell` 拼接 |
| `tests/test_progress_parse.py` | S6 | `out_time_ms=`；`out_time=HH:MM:SS.micro`；无关行返回 None |

不强制 CI。没有 pytest 依赖。

---

## 14. DoD（S10 对照勾，现在不要提前全勾）

见 `docs/工程规则.md` 第 14 节。正式交付前每一条都必须真的做过。

P0 = S0–S6。P1 至少 3 项，本方案要求 S7 六项都做。P2 不准出现在界面上当摆设。

---

## 15. 新对话复制块

```
先读 AGENTS.md，再读 docs/PHASE_STATUS.md、docs/工程规则.md、docs/阶段任务.md、docs/AI执行方案.md、docs/DECISIONS.md。
只做 PHASE_STATUS 里第一个未 done 的阶段，按 AI执行方案对应章节的接口/文案/验证执行。
UI 锁定 PySide6；转码只用 ffmpeg/ffprobe 命令行 list[str]。
禁止网页/tkinter/CLI，禁止 UI 线程跑 ffmpeg，禁止 shell=True，禁止跳阶段，禁止加 P2。
阶段验收通过后更新 PHASE_STATUS 与 SESSION_SUMMARY，然后停下。
```
