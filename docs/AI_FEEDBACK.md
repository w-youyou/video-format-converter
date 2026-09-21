# 对 AI 生成结果的审查与反馈

记录「AI 给了什么 → 为什么不能直接用 → 我怎么改」。不是表扬信。完成后至少 5 条真实记录。

## 模板

```
### F-编号
- 现象：
- 问题：
- 处理：
- 规则：
```

## 预置拒绝项（开发中若再出现，直接记一条）

### F-00 预置：客户端选型
- 现象：AI 可能建议 Streamlit / Gradio / tkinter / 纯 CLI 以求更快出活
- 问题：需求明确：界面选型与客户端关联为 0 则不考虑
- 处理：拒绝并固定 PySide6
- 规则：以后禁止再提这些方案当主界面

### F-01 预置：在 UI 线程跑 ffmpeg
- 现象：AI 常用 `subprocess.run` 直接写在按钮槽函数里
- 问题：窗口假死，无法取消，不像给人用的软件
- 处理：必须 QProcess / QThread
- 规则：禁止 UI 线程同步外部进程

### F-02 规格把 out_time_ms 当成毫秒
- 现象：执行方案写「用 out_time_ms 与总时长算百分比」，单测也准备手写毫秒 fixture
- 问题：很多 ffmpeg 版本里该字段实际是微秒；按毫秒算进度永远约 0%，测试和实现一起错
- 处理：优先解析 `out_time=HH:MM:SS`；`out_time_us` 次之；`out_time_ms` 仅兜底并按微秒试算；S6 用真视频核对
- 规则：禁止把 `out_time_ms` 一律当毫秒；禁止只测手写毫秒 fixture

### F-03 规格给 ffprobe 加了 `--`
- 现象：`ffprobe ... -- <path>` 当 POSIX 选项终止符
- 问题：ffmpeg 系不支持 `--`，会报未知选项，探测直接失败
- 处理：默认去掉 `--`，path 放最后。list[str] 无注入风险
- 规则：禁止给 ffmpeg/ffprobe 加 `--`

### F-04 硬件加速写成替换编码器名
- 现象：预设是 `-c:v libx264 -crf 23`，计划把 libx264 换成 h264_nvenc
- 问题：NVENC 不认 `-crf`（要用 `-cq`），QSV 要用 `-global_quality`，命令必然失败，永远回退等于白做
- 处理：硬件加速降为可选；若做必须独立完整 args。S7 必做改为完成后体积对比
- 规则：禁止在 x264 参数上替换编码器名

### F-05 kill 后立刻删输出
- 现象：取消流程写「杀进程树，删不完整输出」
- 问题：Windows 上句柄未释放，`os.remove` 抛 PermissionError，T05 会挂。ffmpeg 也不 fork
- 处理：terminate → waitForFinished → kill → wait，再删文件；PermissionError 则短等重试
- 规则：禁止 kill 后不 wait 就删文件

### F-06 建议 MergedChannels / 无残行 buffer
- 现象：未规定 stdout/stderr 分离和按行缓冲
- 问题：进度在 stdout、错误在 stderr；合并后难解析。块到达时最后一行常不完整，进度会跳或丢
- 处理：禁止 MergedChannels；stdout 残行 buffer 按 `\n` 切
- 规则：进度解析不得在合并通道的噪声里捞

### F-07 关窗只处理转换中
- 现象：closeEvent 只写了「转换中确认」
- 问题：ProbeWorker/ThumbWorker 运行时销毁会 `Destroyed while thread is still running`；选中大文件立刻关窗可复现
- 处理：closeEvent 统一等所有 worker 收尾
- 规则：禁止在 QThread 仍 running 时销毁窗口

### F-08 日志命令不能复制到终端
- 现象：R08 要求「能复制到终端复现」，但执行用 list，日志若原样空格拼接会断
- 问题：含空格/中文的路径直接复制跑不通
- 处理：展示用 `subprocess.list2cmdline`，执行仍 list
- 规则：禁止拿展示字符串去 shell=True 执行

### F-09 中文 exe 名与固定缩略图路径
- 现象：PyInstaller `--name 视频格式转换器`；缩略图 `vfc_thumb_<pid>.png`；PNG 上还加了 `-q:v 3`
- 问题：中文 exe 在部分环境/CI 编码麻烦；QPixmap 路径缓存导致换视频串图；`-q:v` 对 PNG 无效
- 处理：exe 名 `VideoFormatConverter`；临时 jpg + 自增序号；窗口标题保持中文
- 规则：打包名用 ASCII；封面路径每次必须不同

### F-10 切预设不改输出后缀
- 现象：默认 `{stem}_转换{suffix}`，但用户可先选路径再改预设
- 问题：选「提取音频 MP3」仍写 `.mp4`，ffmpeg 按扩展名选 muxer，失败或生成怪文件
- 处理：切预设只替换后缀，保留目录和主干；S7 预览立刻跟上
- 规则：禁止输出扩展名与当前预设不一致就开转

### F-11 未校验输出等于输入
- 现象：浏览对话框可以选中源文件本身
- 问题：ffmpeg 边读边写，源视频报废，不可逆
- 处理：开转前 `abspath` + Windows `normcase`；相同则 W34，不启动
- 规则：禁止对源文件路径开转

### F-12 进度能到 100% 却还在转
- 现象：按 out_time/duration 算出 100，但 moov/faststart 还要几秒
- 问题：用户以为卡死
- 处理：百分比 clamp 到 99，只有 finished_ok 置 100
- 规则：转换中禁止显示 100%

### F-13 无音轨提 MP3 要失败了才解释
- 现象：S5-T6 只在 ffmpeg 失败后用 W31
- 问题：S3 已有 audio_codec，却让用户白等一次失败
- 处理：选中「提取音频 MP3」且 audio_codec 为 None 时立刻提示并禁用开始
- 规则：能在点开始前拦住的，不要等转码失败

