# AI 入口（先读这个）

本仓库是 **Windows 桌面视频格式转换器** 交付项目。当前阶段是 **S10**（S0–S9 已完成）。

## 推荐：只读这一份完整规格

**`docs/完整需求与执行方案.md`**

里面同时写了需求、锁定方案、接口、文案、S0–S10 逐步任务和验收。打开就能执行。不要再拼多份文档才开工。

## 硬锁定（不要讨论替代方案）

- UI：**PySide6**。禁止网页 / Streamlit / Gradio / tkinter / CLI 主界面
- ffmpeg/ffprobe **必须**命令行；`list[str]`；禁止 `shell=True`；禁止 UI 线程同步跑
- 禁止跳阶段；禁止做当前阶段清单外的功能；禁止主动加 P2
- 界面中文；`app/core/` 禁止 `import PySide6`

## 做完一个阶段后

1. 把 `docs/完整需求与执行方案.md` 第 0.2 节进度表改为 `done`
2. 同步 `docs/PHASE_STATUS.md`
3. 追加 `docs/SESSION_SUMMARY.md`
4. **停下**。除非用户明确说继续下一阶段
