# 四语言可编辑坐标示例

observations.csv 是六条合成软件体验数据，不代表真实研究。四份源程序使用同一数值；不会进行未声明的统计检验。请在可写副本中运行，保留其与 scripts 的相对目录，或按下方复制所需桥接文件。

- R：`Rscript draw.R`。需要 R、svglite、jsonlite；首次运行复制 bridge 系列 helper 到本例 helpers/，并在清单中登记。保留旧 ggplot 语义路线，另提供 base / 专用库计算结果的显式坐标路线。
- Python：`python draw.py`。需要 Matplotlib；已有 Matplotlib 脚本通常直接用 import-python。本例同时写同一语义 JSON，演示其他绘图库计算结果的接入。
- MATLAB：在此目录运行 `draw_matlab`，或 `matlab -batch draw_matlab`。首次复制 fam_save_figure.m 到 helpers/；它读取原 Figure 的误差点和 XYZ 数据。
- C：使用原有 C99 编译器，例 `cc -std=c99 -O2 draw.c -o draw` 后运行 `draw`；Windows 编译命令按本机编译器调整。随附 fam_bridge.h 与 scripts 中同版；读取 CSV 后原生输出 SVG 和坐标场景，不调用 Python。

每份程序写出 `<language>-import.json`、原 SVG 和场景，使用 `studio.py --project <新项目> import-vector <清单>` 接入，再 `check-editability --require-axes`。工作台可改坐标框、范围、字体、点与误差外观；三维面板另可改视角。多面板各自独立，再引用组图。

R/Python/MATLAB 示例在源码中按相对路径寻找桥接；复制到其他位置时，把相应 helper 放在 helpers/。清单会保留这些依赖，来源快照可继续在原语言中运行。Python 的原分析依赖仍是 Matplotlib；GUI 的 native scene 内核不是任意外部统计包的替代。C 只需要本例头文件。

原数据与计算始终保留；四语言“完整编辑复现”代码包按最终 SVG 场景重放，不自动翻译原统计模型。详细字段与边界见 [统一坐标接入](../../references/native-coordinates.md)。
