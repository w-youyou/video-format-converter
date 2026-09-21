# 实测报告

没有真实操作记录视为未完成。截图放到 `docs/screenshots/` 并在对应项下注明文件名。

## 环境

- OS：Windows-10-10.0.19045（Windows 10）
- Python：3.12.10
- ffmpeg 版本：本机 PATH（Gyan.FFmpeg / winget）
- 主测素材（真实视频）：`C:\Users\Administrator\Desktop\096a562ccbca561302f5dd1a4c397227.mp4`
  - 约 5.1 秒 · 720×1280（竖屏）· 视频 hevc · 音频 aac · 约 1.0 MB
- 辅助素材：无音轨 `silent.mp4`（脚本生成）、损坏文件 `broken.dat`；中文路径复制为 `测试 视频.mp4`

## 清单

| ID | 步骤 | 结果（通过/失败） | 证据 | 备注 |
|---|---|---|---|---|
| T01 | 无 ffmpeg 启动 | 通过 | `01_missing_ffmpeg.png` | 横幅+状态提示，主按钮禁用，不崩溃 |
| T02 | 打开真实 mp4，信息+缩略图 | 通过 | `02_main_info_thumb.png` | hevc / 720×1280 / 封面可见；最新浅色 UI |
| T03 | 中文路径、空格路径 | 通过 | `07_chinese_path.png` | 路径含「测试 视频」仍能 probe + 封面 |
| T04 | 转压缩 MP4，可播放 | 通过 | `03_converting_progress.png`；`04_done_with_size.png` | 真实视频转换中有进度；完成后有体积对比 |
| T05 | 转换中取消 | 通过 | 自动化 `t05_cancel` | 状态「已取消」，不完整输出已删除 |
| T06 | 转换中再点开始 | 通过 | 自动化 `t06_double_start` | `started` 信号只触发 1 次 |
| T07 | 输出已存在 | 通过 | 自动化 `t07_overwrite` | 弹出「是否覆盖？」；否=不开始；是=加 `-y` 成功 |
| T08 | 损坏/非视频文件 | 通过 | `06_fail_broken.png` | 人话「无法读取视频信息…」，不崩 |
| T09 | 关闭进行中窗口 | 通过 | 自动化 `t09_close_confirm` | 确认框出现后取消任务并收尾 worker |
| T10 | 连续转两个文件 | 通过 | 自动化 `t10_two_files` | 第二次成功；封面临时路径序号不同不串图 |
| T11 | 切预设后后缀跟着变 | 通过 | 自动化 `t11_suffix` | 后缀与预览同步 |
| T12 | 输出等于源文件被拒绝 | 通过 | 自动化 `t12_same_path` | W34；源文件体积未变；主按钮禁用 |
| T13 | 无音轨提 MP3 开转前拦住 | 通过 | `05_fail_no_audio_mp3.png` | W31；未启动 ffmpeg；开始按钮不可用 |

## 截图索引（至少 4 张）

| 文件 | 说明 |
|---|---|
| `01_missing_ffmpeg.png` | 无 ffmpeg 横幅提示 |
| `02_main_info_thumb.png` | 主界面：真实视频信息表 + 缩略图（最新 UI） |
| `03_converting_progress.png` | 真实视频转换中进度 |
| `04_done_with_size.png` | 完成后体积对比 + 打开文件/文件夹 |
| `05_fail_no_audio_mp3.png` | 无音轨提 MP3 失败提示（开转前） |
| `06_fail_broken.png` | 损坏文件人话错误 |
| `07_chinese_path.png` | 中文带空格路径（同源真实视频） |

## 刷新方式

```powershell
python scripts/capture_screenshots.py
```

使用桌面上的真实 mp4；不把该视频提交进仓库。

## 失败与修复

本次截图已按最新 Codex 浅色 UI + 真实竖屏视频重拍。
