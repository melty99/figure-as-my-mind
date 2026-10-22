# R 优先与多语言复现

## 两类代码

1. 原生分析/绘图源码：读原数据，执行明确的计算，用 R/ggplot2、Python/Matplotlib、MATLAB 或 C 所选绘图库生成图。新图默认 R，已有项目保留源语言；语言切换基于源数据和模型重建，不按 SVG 外观猜测统计含义。
2. 完整编辑复现代码：`draw.R`、`draw.py`、`draw.m` 或 `draw.c` 使用 scene.tsv 构造 SVG，保留编辑后的几何、字体、文字、颜色、裁切、3D 投影和组图。R 使用 base/utils，Python 使用标准库，MATLAB 使用基础函数，C 使用标准库及系统目录创建函数；R/MATLAB/C 不调用 Python。这一模式适用于所有可导出的图型，但不会重新训练或拟合，也不生成原生 ggplot/Matlab Figure 对象。

同一个包里的 original/ 和 manifest.json 分别保留已有分析源码/声明输入与编辑设置，避免把“代码可运行”误报为“分析自动转换”。C 分析源码可能需要原绘图库；导出 draw.c 的矢量复现不需要那套库。原栅格内容继续是栅格，不承诺全部内容矢量化。

```powershell
python <skill>/scripts/studio.py --project <project> export-code --language r --ids f-... g-...
```

导出 UI 首次选择 R，按项目记住上次语言；纯图片选项禁用代码语言，纯代码选项禁用图片格式和 DPI。选项切换不会修改原观测。代码生成只在导出时进行；拖动与保存继续使用已缓存的场景，不启动外部语言进程。

## 复制 / 导出设置的语言

画布上方“复制设置给 Codex”打开语言选择，可选 R、Python、MATLAB、C。首次默认 R，和代码导出共用当前项目在本浏览器的上次语言偏好。可直接复制提示词与 JSON，或下载 figure-settings-<language>.json；JSON 的 drawingLanguage 记录 r/python/matlab/c。预览按需展开，剪贴板受限时自动选中文本，也可下载文件。

单图携带当前图的保存设置；组图另外携带完整组图与当前子图的合并设置，独立覆盖 / 锁定保持。此步骤只读保存状态，不写科研设置或新增撤销。生成原生代码时遵循所选语言，同时保留原输入和明确的统计方法；不能据此自动翻译未确认的分析模型。界面中英文切换不改变目标语言或图件内容。

## 原语言接入清单

```json
{
  "version":1,"language":"r","source":"draw.R",
  "inputs":["bridge.R","data/measurements.csv"],
  "figures":[{"svg":"raw/scatter.svg","name":"散点图","chartType":"scatter",
    "objects":[{"id":"point-1","data-fam-layer":"data","data-fam-entity":"sample-1"},
               {"id":"error-1","data-fam-layer":"uncertainty","data-fam-follow":"sample-1"}]}],
  "datasets":[{"path":"data/measurements.csv","name":"测量数据"}]
}
```

`language` 为 r/python/matlab/c；图型可省略，未知图保留通用对象编辑。所有路径位于清单目录内，源码后缀与语言对应；头文件、辅助函数及数据显式列入 inputs。图和数据可为对象数组，MATLAB 输出的单个对象也接受。datasets 只接受明确声明的 CSV/TSV，不执行原脚本、联网或自动读取未声明文件。使用 `import-vector` 导入；保留代码和输入的内容哈希，同一代码配不同数据不会覆盖原快照。

数据/误差/标签关系只有在 SVG 本身或 objects 中显式声明后联动；未知 R/Matlab SVG 不靠距离猜测关系。原生统计、重排网络和真正 3D 相机等需要对应语言的数据适配器，不能靠 chartType 标签自动获得。

R 使用 bridge.R 的 fam_save（默认 svglite、透明）及 fam_manifest；需要 ggplot 全局样式时用 fam_theme。使用 base R svg 的字体可能变为路径，只有明确接受时设置 semantic_text=FALSE。R 生成的 textLength/lengthAdjust 在原态保持，明确改变文字、字体、字号时清除固定长度，避免新字被压缩回旧宽度。

MATLAB 按当前版本选择 SVG 导出。exportgraphics 的 SVG 支持从 R2025a 开始；本机验证的 R2022a 使用 saveas SVG。来源：[MathWorks exportgraphics](https://www.mathworks.com/help/matlab/ref/exportgraphics.html)、[MathWorks saveas](https://www.mathworks.com/help/matlab/ref/saveas.html)。R 的语义文字依据 [svglite 文档](https://svglite.r-lib.org/)。Windows R 4.2+ 的复现脚本仅在当前进程设置 UTF-8 字符处理，以支持中文路径，不改变系统或用户配置。

## 场景表

scene.tsv 三列为 kind/name/value。操作顺序包含 figure/open/attr/start/text/close/done，name/value 是 UTF-8 百分号编码；数值、颜色、字体、路径、文本及对象 ID 可修改。所有绘图脚本验证输出文件名，不将其当命令执行。表含裁切与命名空间，嵌入图像保留原字节。manifest.json 记录输出名对应图件、源文件哈希和展示设置。

直接修改场景表不会重新计算数据依赖，因此科研数据变更回原分析脚本；点与误差的互动编辑应在工作台执行，导出保存其最终联动结果。复现 SVG 可以重新 import-svg 编辑，但仅导入它不能恢复原数据、统计模型或三维相机。

项目 examples/multi-language-workflow 提供 R 8 图、MATLAB 2 图及 C 散点/误差/OLS 示例，输入与统计均为明确标识的合成体验数据。它们是原语言实际绘图，和通用场景复现分别验证。


## 原生坐标与轻量交互

除 SVG 接入外，四种语言均可用 [统一坐标场景](native-coordinates.md) 保留坐标框、范围、点与误差、数值颜色和真实 XYZ；MATLAB 有直接读取受支持 Figure 的桥接，C 有标准库头文件，R 有显式几何 helper。场景在接入时转换一次并捕获；正常拖动 / 缩放不重新启动外部语言。需要重新计算统计或换变量时仍回原语言。清单中可仅提供 scene，或另附原 SVG 参考。scene、原 SVG、源码和声明依赖均进入独立内容哈希快照。编辑复现代码继续按上方四语言矢量模式导出，不能把它称为原生分析翻译。
