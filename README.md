# 图随我意 v1.0

[完整图文教程](docs/教程.md) · [安装与启动](docs/安装与启动.md) · [故障排查](docs/故障排查.md)

界面支持中文 / English：顶部点击语言按钮立即切换，浏览器记住选择；图中内容与原始数据不翻译。
本目录是可安装的 Codex skill。调用 `$figure-as-my-mind` 接入原代码与数据，或启动本地编辑工作台。完整发行包另含根 README、安装器、唯一 Windows 启动入口、R / Python 示例与分发清单。

安装后的独立依赖可运行 `python scripts/setup.py`。已有项目用 `python scripts/launcher.py --project "项目完整路径"` 打开；项目不存在时建议让 Codex 初始化空项目。不要直接双击 assets/editor.html。

多数模板数据为合成示例。原始数据不回写，图片需先重绘；通用 SVG 不自动获得未声明的统计语义。四语言矢量复现与原生分析重算有不同用途，详见教程。

需要缩放坐标框或编辑 R 分面图时，使用 [ggplot 语义接入](references/ggplot-semantic.md)：保留 R 已计算的坐标和统计量，每个分面先成为独立单图，再建立组图。只有 SVG 的接入不具备这些坐标编辑能力。


多语言坐标接入：R / Python / MATLAB / C 的明确坐标、误差和 XYZ 可通过[统一坐标桥接](references/native-coordinates.md)接入；提供[同一数据的四语言示例](examples/native-coordinates/README.md)。已支持 MATLAB Figure 对象提取和标准 C99 坐标头文件；正常交互不重复启动外部语言。


源码与原创文档采用 [MIT](LICENSE)。完整 GitHub 包包含根 introduction 与七个 GIF；独立 skill 保留图文教程、桥接手册和运行脚本。
