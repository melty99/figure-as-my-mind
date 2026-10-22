# Figure as My Mind · 图随我意

[English](#english) · [简体中文](#简体中文)

## English

**Connect plotting code with visual editing.**

Figure as My Mind is an installable Codex skill and a local workbench for scientific figures. Keep your R, Python, MATLAB or C source code and data, edit text, axes, legends and layouts in the browser, and export images and settings for reproduction.

[English tutorial: seven GIF examples](introduction.en.md) · [Chinese tutorial](introduction.md) · [Installation guide (Chinese)](skills/figure-as-my-mind/docs/安装与启动.md) · [Detailed manual (Chinese)](skills/figure-as-my-mind/docs/教程.md) · [Troubleshooting (Chinese)](skills/figure-as-my-mind/docs/故障排查.md) · [MIT license](LICENSE)

![Resize the plotting area independently in width and height](docs/media/en/01-axes-resize.gif)

### Quick start

You need **Python 3.10 or later**. Extract the full repository package and run these commands from the directory containing `start.py`:

```powershell
python start.py --setup
python install_skill.py
python start.py
```

These commands install dependencies into the tool's own runtime, install the skill, and launch the workbench. On Windows, you can subsequently double-click **启动图随我意.cmd**, the single user-facing launcher. On macOS or Linux, use `python start.py`.

The workbench starts empty. Click **Templates** in the left panel to explore a chart type, or ask Codex to import your own source code. Use the language button at the top to switch the interface to English. Start with the [English illustrated tutorial](introduction.en.md), which uses English workbench recordings.

The first dependency installation requires internet access. This package does not include Python, R, MATLAB, system fonts or preinstalled dependencies. Prepare the corresponding runtime or compiler for native R, MATLAB or C plotting. For browser export requirements and the Playwright Chromium fallback when Chrome/Edge is unavailable, see the [installation guide (Chinese)](skills/figure-as-my-mind/docs/安装与启动.md).

#### Invoke the skill in Codex

The installer defaults to `~/.agents/skills/figure-as-my-mind` and refuses to overwrite an existing directory. Reopen your Codex conversation after installation and send:

```text
Use $figure-as-my-mind.
Import the plotting source code and data I provide, keeping the original language and statistical methods.
Keep the axes frame, text, data marks, error bars, legends and panels editable with their relationships intact.
Check the required editing capabilities, then return a link to the workbench.
```

Provide the source code and data in the same task. Before updating, back up the previous skill outside the skills directory and keep your projects. You can also install the `skills/figure-as-my-mind` subdirectory from the GitHub repository; no GitHub account or remote URL is assumed by this package.

#### Full package or lightweight skill?

Both contain the same editing engine and all chart templates. The full package also includes the repository launcher, installer, runnable repository examples, bilingual introductions, demonstration GIFs and video. The lightweight ZIP contains the self-contained skill, its documentation, templates and runtime scripts; it does not include the root launcher or demonstration media.

For a first installation, use the full package and the commands above. For the lightweight version, see its [English README and quick start](skills/figure-as-my-mind/README.md#english). Neither package includes personal research projects or raw cruise data.

### Seven practical examples

The [English tutorial](introduction.en.md) follows actual workbench operations. Its chapter text, captions and workbench recordings are in English.

| Example | What you can change |
| --- | --- |
| Resize the plotting area | Widen, flatten, narrow or stretch the axes frame; data marks and error bars follow the coordinate mapping |
| Axis limits | Lower and upper limits, major tick intervals/counts, and linear or logarithmic scales |
| Legends | Move or scale the whole legend; edit entry order, layout and colors |
| Panel refinement | Link common font sizes while editing another panel's colorbar independently |
| Synchronized rotation | Rotate compatible native 3D panels together while retaining their individual styles |
| Reusable settings | Choose R, Python, MATLAB or C, then copy settings for Codex |
| Export | SVG, PDF, PNG or TIFF; transparency, dimensions, DPI and reproduction code |

[Watch the approximately 54-second video (Chinese demonstration, with music)](docs/media/demo-bgm.mp4) · [Music attribution](docs/media/music-credit.txt) · [English GIF collection](docs/media/en/README.md)

### Start from data

The repository includes synthetic CSV data. The Python example gives you native coordinate editing, data marks and linked error components:

```powershell
python skills/figure-as-my-mind/scripts/studio.py --project projects/quickstart import-python examples/quickstart/plot.py
python start.py --project projects/quickstart
```

For R/ggplot, export both the SVG and the computed coordinate scene:

```powershell
Rscript examples/quickstart/plot_semantic.R
python skills/figure-as-my-mind/scripts/studio.py --project projects/quickstart-r import-vector examples/quickstart/import-semantic-r.json
python start.py --project projects/quickstart-r
```

The R example requires `ggplot2`, `jsonlite` and `svglite`. See the [example notes (Chinese)](examples/quickstart/README.md) and [synthetic 3D composition (Chinese)](examples/spatial-demo/README.md). Source-code import executes the script; review your plotting script and its side effects before importing it.

### Import routes and capabilities

| Source | Recommended route | Capabilities |
| --- | --- | --- |
| Matplotlib | `import-python` | Native coordinates, series, error components, legends and supported 3D figures |
| R/ggplot | SVG plus a `fam_save_ggplot` scene, then `import-vector` | Coordinate and statistical components for supported geometries; independently editable facets |
| Other R plots, MATLAB or C | Explicit coordinate bridge or SVG manifest | Controls based on the declared coordinates, identities and relationships |
| Plain SVG | `import-svg` | Text, paths and appearance; undeclared statistical relationships are not inferred |
| PNG/JPG | Redraw from the image as a reference, then import the result | The image is a reference, not a source of original observations |

When the skill is enabled, new scientific figures default to R if no language is specified, retaining editable semantics from the source. Existing analyses keep their original language and methods. **Four-language vector reproduction replays the appearance; it does not automatically translate statistical models.**

### Save and reuse

Edits are saved automatically. Reopen the same `--project` path to continue. Compositions retain independent panel settings; layer locks and linked-edit locks help prevent unwanted changes. The workbench supports ten steps of undo/redo, multiple selection, copy/paste, settings JSON, image export and project packages.

Original observations and source code are retained. Moving or hiding display elements does not write changes back to the input data; fits and correlations continue to use the original captured observations. Specialized statistical objects and 3D cameras require explicit adaptation.

The library contains **78 chart types**, including statistical charts, PCA, forest plots, networks, chord diagrams, UpSet plots, machine-learning analysis plots and maps. Examples and templates are for exploration, not new research evidence.

### Repository structure

```text
README.md                       English + 简体中文 README
introduction.md                 Chinese tutorial and GIFs
introduction.en.md              English tutorial and English GIFs
docs/media/                     Demonstration GIFs, video and attribution
skills/figure-as-my-mind/        Installable skill and editing engine
examples/                       Synthetic CSV, R/Python and 3D examples
start.py                        Cross-platform launcher
install_skill.py                Installer that refuses to overwrite
启动图随我意.cmd                Single Windows launcher
tools/validate_release.py       Distribution checks
LICENSE                         MIT license
```

Run `python tools/validate_release.py` to check the distribution. `package_plugin.py` builds the full ZIP with a file-hash manifest. Personal projects, session tokens, dependency directories, recording projects and development logs are excluded.

### Release and license

Current release: **v1.0 / 1.0.0**. Windows is the primary tested platform. Cross-platform command entry points are included; equivalent browser acceptance testing on other operating systems is not claimed.

Source code and original documentation use the [MIT license](LICENSE). Demonstration music, map data and other assets retain their respective terms in the [third-party notices](THIRD_PARTY_NOTICES.md). No official affiliation with other brands is claimed.

[GitHub release and validation notes (Chinese)](docs/github-release.md) · [Changelog (Chinese)](CHANGELOG.md)

## 简体中文

**把“用代码画图”和“在图上修改”连接起来。**

可安装的 Codex skill 与本地科研绘图工作台。保留 R / Python / MATLAB / C 的源码与数据，在浏览器里调整文字、坐标、图例和布局，再导出图片与复现设置。

[七个 GIF 上手示例](introduction.md) · [English introduction](introduction.en.md) · [安装与启动](skills/figure-as-my-mind/docs/安装与启动.md) · [完整教程](skills/figure-as-my-mind/docs/教程.md) · [排错](skills/figure-as-my-mind/docs/故障排查.md) · [MIT](LICENSE)

![坐标框宽高独立调整](docs/media/01-axes-resize.gif)

### 快速开始

需要 **Python 3.10+**。解压仓库，在包含 `start.py` 的根目录运行：

```powershell
python start.py --setup
python install_skill.py
python start.py
```

依次完成局部依赖安装、skill 安装和启动。Windows 之后双击唯一的 **启动图随我意.cmd**；macOS / Linux 使用 `python start.py`。首次工作台为空，可点击左侧“＋ 图型模板”体验，或让 Codex 接入自己的源码。

首次安装需要联网；本包不携带 Python、R、MATLAB、系统字体和依赖目录。需要原生 R / MATLAB / C 作图时，另准备对应运行环境。没有 Chrome / Edge 时，按[安装说明](skills/figure-as-my-mind/docs/安装与启动.md)安装 Playwright Chromium。

#### 在 Codex 中调用

安装器默认放入 `~/.agents/skills/figure-as-my-mind`，拒绝覆盖已有目录。重新打开会话后发送：

```text
使用 $figure-as-my-mind。
请把我提供的绘图源码和数据接入工作台，保留原语言和统计方法。
坐标框、文字、数据与误差、图例和子图需要保持可编辑的关联。
先验证所需的编辑能力，再返回可打开的工作台链接。
```

将源码与数据附在该次任务中。更新前先把旧 skill 备份到 skills 目录之外，保留自己的项目。也可从 GitHub 仓库的 `skills/figure-as-my-mind` 子目录安装；本包不预填未知的 GitHub 账户或远端地址。

### 七个操作示例

[introduction](introduction.md) 按实际工作台操作展开：

| 小节 | 修改效果 |
| --- | --- |
| 坐标框缩放 | 拉宽、压扁、收窄、拉高，数据与误差随坐标重新映射 |
| 坐标轴范围 | 上下限、主刻度间隔 / 数量、线性与对数尺度 |
| 图例 | 整体移动、缩放，条目排序、排版与颜色 |
| 子图精修 | 共同字号联动，另一子图色标独立编辑 |
| 同步旋转 | 兼容原生 3D 子图一起转，各自样式仍保留 |
| 复用设置 | 选择 R / Python / MATLAB / C，复制设置给 Codex |
| 导出 | SVG / PDF / PNG / TIFF、透明背景、尺寸、DPI 与代码 |

[观看约 54 秒配乐演示](docs/media/demo-bgm.mp4) · [音乐署名](docs/media/music-credit.txt)

### 从数据开始

附带合成 CSV。Python 路线可直接体验原生坐标、数据与误差组件：

```powershell
python skills/figure-as-my-mind/scripts/studio.py --project projects/quickstart import-python examples/quickstart/plot.py
python start.py --project projects/quickstart
```

R / ggplot 推荐同时导出 SVG 和已计算的坐标场景：

```powershell
Rscript examples/quickstart/plot_semantic.R
python skills/figure-as-my-mind/scripts/studio.py --project projects/quickstart-r import-vector examples/quickstart/import-semantic-r.json
python start.py --project projects/quickstart-r
```

R 示例需要 `ggplot2`、`jsonlite`、`svglite`。参见[示例说明](examples/quickstart/README.md)和[合成三维组图](examples/spatial-demo/README.md)。源码导入会执行脚本，先检查自己的绘图脚本及其副作用。

### 接入方式与能力

| 来源 | 推荐入口 | 能力 |
| --- | --- | --- |
| Matplotlib | `import-python` | 原生坐标、系列、误差、图例和支持的 3D |
| R / ggplot | SVG + `fam_save_ggplot` 场景，再 `import-vector` | 支持几何的坐标 / 统计组件，独立分面 |
| R 其他画法 / MATLAB / C | 显式坐标桥接或 SVG 清单 | 按声明的坐标、身份与关联开放控件 |
| 普通 SVG | `import-svg` | 文本、路径与外观；不虚构未声明统计关系 |
| PNG / JPG | 先参考重绘，再接入结果 | 图片是参考，不能直接拆成真实观测 |

启用 skill 后，新科研图未指定语言时优先 R，从源码阶段保留可编辑语义。已有分析沿用原语言和方法。**四语言矢量复现准确重放画面，不代表统计模型自动互译。**

### 保存与复用

修改自动保存，再次用同一 `--project` 可继续编辑。组图保留面板独立设置；图层锁和联动锁避免误改。支持 10 步撤销 / 重做、多选和复制粘贴、设置 JSON、图片与项目包导出。

原始观测与源码保留，展示移动 / 隐藏不回写数据；拟合与相关仍使用原始捕获观测。特殊统计对象和三维相机需要明确适配。

内置 **78 种图型**，包括统计图、PCA、森林图、网络图、弦图、UpSet、机器学习分析图和地图等。示例与模板供体验，不是新的研究证据。

### 仓库结构

```text
README.md                       English + 简体中文 README
introduction.md                 中文操作示例与 GIF
introduction.en.md              English tutorial with English GIFs
docs/media/                     GIF、演示视频与配乐署名
skills/figure-as-my-mind/        可安装 skill 与运行内核
examples/                       合成 CSV、R/Python 和三维示例
start.py                        跨平台启动入口
install_skill.py                无覆盖安装器
启动图随我意.cmd                唯一 Windows 启动按钮
tools/validate_release.py       发布前检查
LICENSE                         MIT
```

运行 `python tools/validate_release.py` 验证发布内容；`package_plugin.py` 生成带哈希清单的完整 ZIP。不附带个人项目、会话 token、依赖目录、录屏工程和开发日志。

### 发布信息

当前 **v1.0 / 1.0.0**。Windows 是主要实测平台；其他系统保留跨平台命令入口，尚未宣称经过同等浏览器验收。

源码与原创文档采用 [MIT](LICENSE)。演示配乐、底图与其他素材按[第三方说明](THIRD_PARTY_NOTICES.md)各自授权。本项目不声明任何其他品牌的官方关联。

[GitHub 发布与验证](docs/github-release.md) · [版本说明](CHANGELOG.md)
