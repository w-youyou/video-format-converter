# 阶段状态

AI 每次只做表中**从上到下第一个不是 done** 的阶段。完成后改状态，并写完成说明。

状态只能是：`todo` / `doing` / `done`。

| 阶段 | 状态 | 完成说明 |
|---|---|---|
| S0 脚手架 | done | `python -m app.main` 弹出中文标题空白窗，关窗退出 |
| S1 客户端主界面骨架 | done | 四区中文布局；选文件/拖放只填路径；日志默认收起 |
| S2 检测 ffmpeg | done | 启动检测 ffmpeg/ffprobe；缺失显示中文横幅并禁用开始转换 |
| S3 加载视频信息 | done | ffprobe JSON 后台填充信息表；缺字段显示未知；关窗等待 ProbeWorker |
| S4 缩略图 | done | ffmpeg 先 seek 再抽 jpg 封面；失败占位+原因；换文件清旧图 |
| S5 转换主路径 | done | 四预设 argv 为 list；QProcess 转换 sample.mp4 得到可探测的 h264/aac；切后缀/同源/无音轨 MP3 开转前拦住 |
| S6 转换过程体验 | done | stdout 解析 out_time 进度 clamp 99；取消后删残片；覆盖确认；完成后打开文件夹；关窗确认并等待 worker |
| S7 产品优化 P1 | done | 记住设置；输出文件名预览；打开文件+文件夹；完成后体积对比；日志含退出码；拖放多文件/非视频人话；硬件加速砍掉 |
| S8 实测与证据 | done | T01–T13 全通过；4+ 张可读截图；含中文路径与 silent.mp4 |
| S9 打包与 README | done | 完整中文 README（截图+PySide6）；PyInstaller 打出 VideoFormatConverter.exe 可启动；ffmpeg 外置 |
| S10 过程文档收口 | todo |  |
