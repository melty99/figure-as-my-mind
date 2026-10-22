# 跨语言原生坐标接入

适用于已有 R、Python、MATLAB 或 C 的计算结果，且需要在工作台修改坐标框、范围、主刻度、点 / 误差、图例 / 数值色带或真实三维视角。保留原语言的输入、计算和统计方法；接入只读取明确的坐标场景，不执行清单中的脚本。

## 选择通路

| 来源 | 推荐 | 适用边界 |
|---|---|---|
| Python / Matplotlib | import-python 捕获真实对象 | 保留既有点、箱线、误差及专门绘图适配 |
| R / ggplot2 | fam_save_ggplot + import-vector | 沿用 ggplot-built-v1 的几何及统计接入范围 |
| R / base 或专用库的明确结果 | bridge_native.R 的 fam_layer / fam_panel / fam_save_native | 显式提供原语言算好的坐标与统计摘要 |
| MATLAB | fam_save_figure.m(fig, sceneFile) | 读取已支持的 Cartesian Figure 对象 |
| C | fam_bridge.h | 标准 C99 写出明确坐标；编译环境由原程序提供 |
| Python / 其他绘图库的明确结果 | native_scene.save_scene | 使用原库计算结果，不按图片猜数值 |

所有通路保留逐元素编辑；不把一般 SVG 说成已经有坐标语义。不支持的曲线几何、模型或特殊坐标需专门适配，不能偷偷换成截图。

## 清单与运行

```json
{
  "version":1, "language":"matlab", "source":"draw.m",
  "inputs":["measurements.csv","fam_save_figure.m"],
  "figures":[{"scene":"figure.scene.json","name":"结果图"}]
}
```

可加 svg 字段保存原外观参考。所有源码、输入、helper、scene 和 SVG 路径均在清单目录内；帮助文件要显式列入 inputs。代码 / 输入 / 场景 / 参考图内容进入来源身份，新数据不会覆盖旧快照。

```powershell
python <skill>/scripts/studio.py --project <project> import-vector import.json
python <skill>/scripts/studio.py --project <project> check-editability --require-axes
# 需要真实三维时另执行
python <skill>/scripts/studio.py --project <project> check-editability --require-3d
```

多面板各自成为独立单图，并新增引用它们的组图；先精修单图，再调整组图。已接入旧项目不自动替换或重建。

## R

```r
source("<skill>/scripts/bridge.R", encoding="UTF-8")
a <- fam_layer("errorbar", x=x, y=y, ids=id, rows=data,
  errors=list(y=se), label="Observed",
  style=list(color="#4477aa", errorColor="#222222", marker="o"))
p <- fam_panel(list(a), x=list(label="Time"), y=list(label="Response"))
fam_save_native(list(p), "figure.scene.json")
fam_manifest("draw.R", figures=list(list(scene="figure.scene.json")),
  inputs=c("data.csv"), file="import.json")
```

使用 bridge.R 时同目录保留 bridge_semantic.R、ggplot_bridge.R 和 bridge_native.R。需要独立重跑的包将这些 helper 同时列入 inputs。fam_layer 可声明点、线、柱、误差、矩阵和曲面；matrix / surface 的 values 是原始矩阵，不能从色块反推。误差可对称向量，也可 list(minus=...,plus=...)。分布统计、PCA、训练等仍由原 R 代码完成，不由 JSON 重算。

## MATLAB

```matlab
addpath('<skill>/scripts');
fam_save_figure(gcf,'figure.scene.json');
% 明确行身份（必须和该系列点顺序一致）
setappdata(h,'FAMSampleIDs',sampleIds);
setappdata(h,'FAMSourceRows',tableRows);
fam_save_figure(gcf,'figure.scene.json');
```

当前支持普通数值 Cartesian 的 line、scatter、errorbar、bar/barh、数值 image 和规则网格 surface，以及 data 单位的 text。支持线型 / 点形、点大小、分组柱位置、柱基线、颜色、空心标记、误差、对数二维轴、轴反向、矩阵 / 点数值色标及真 XYZ。顶视的三维图仍保留 Z。没有显式 FAMSampleIDs 的显示点不擅自当作拟合样本。

双 Y 轴、极坐标、日期 / 类别原始坐标、RGB / 直接索引图像、独立于 Z 的曲面颜色、非规则曲面、未支持 Chart 类型及非线性真三维轴明确拒绝，需原语言专门适配。布局留白、分组柱宽和三维视角的排版可能与原 MATLAB 细节不同；缺失字体按环境替代并记录，不承诺逐像素复刻。导入并不生成任意 MATLAB 原生统计模型的自动 setter。

提取字段参考官方 [ErrorBar 属性](https://www.mathworks.com/help/matlab/ref/matlab.graphics.chart.primitive.errorbar-properties.html)、[Axes 属性](https://www.mathworks.com/help/matlab/ref/matlab.graphics.axis.axes-properties.html)。

## C

```c
#include "fam_bridge.h"
FILE *f=fopen("figure.scene.json","wb");
fam_writer w;
fam_axis xaxis={"Time","linear",0,10,1};
fam_axis yaxis={"Response","linear",0,20,1};
fam_native_begin(&w,f,6.4,4.8);
fam_native_panel(&w,"panel-1","Result",&xaxis,&yaxis,NULL);
fam_native_errorbar(&w,"Observed",x,y,se,se,n,"#4477aa",ids);
int ok=fam_native_end(&w);
fclose(f);
```

头文件仅用标准库，不调用 Python，不安装编译器；示例需原 C99 编译环境。fam_native_xy 提供点、折线、柱；fam_native_xyz 提供真实三维点 / 线；其他已经支持的统一场景字段可用原程序的 JSON 输出实现。字符串使用 UTF-8，JSON 特殊字符被转义，数字按 JSON 小数点写出；非有限数以 null 明示，不能当作零值。

## Python 与场景字段

已有 Matplotlib 优先 import-python；其他库可用 native_scene.save_scene(scene,path)，或以标准 JSON 写出同一协议。版本为 version=1 / kind=fam-native，panels 需要唯一字符串 id。

| 字段 | 内容 |
|---|---|
| width / height / fontFamily / fontSize | 独立面板英寸尺寸与初始字体 |
| panel.x / y / z | label、range、scale、logBase、ticks、tickLabels；二维支持 linear / ln / log2 / log10 / log |
| panel.projection / camera | 2d 或 3d；三维 camera 的 azimuth、elevation、roll、projection（persp/ortho） |
| panel.layers | scatter、line、errorbar、bar、matrix 或 surface |
| layer.x / y / z | 明确的原始数值数组，数量一致；null 表示缺失，保持缺口 |
| sourceIds / rows | 同层唯一的原始行 ID 和原始行；不猜测对应关系 |
| errors | x / y 各自的 minus / plus 非负数组 |
| style | color、edgeColor、faceColor、errorColor、size（点直径 pt）、lineWidth、alpha、marker、lineStyle |
| sizes / colors / edgeColors / colorValues | 显式逐点直径、填充 / 边线颜色或用于色带的数值 |
| values / palette / clim | 矩阵数值、可选颜色表、颜色数值范围；色标为真实独立轴 |
| width / bottom / horizontal | 柱宽、各柱基线与横向柱；与原计算结果对应 |
| panel.annotations | data 坐标下的独立文字，保留原文字与坐标 |

颜色 / 几何均使用明确的数据。非法范围、误差、维度、重复 ID、未知类型与不适配坐标拒绝导入。矩阵坐标须单调且规则网格明确；整体最多两百万数值，超出时分成独立场景，不能静默抽样。

## 可运行示例与性能

[examples/native-coordinates](../examples/native-coordinates/README.md) 使用同一份明确合成 CSV，实际运行 R、Python、MATLAB 和 C，保留各语言原图、源码及场景。示例数据仅用于软件体验。

场景只在接入时转为缓存的原生对象；正常拖动、范围、色标和相机编辑不反复启动 R/MATLAB 或编译 C。矩阵使用一个数值映射集合，避免按格创建大量独立补丁。原始数据、分析代码及场景受完整性校验。完整编辑后的 SVG 场景可继续导出四语言复现包；更换数据 / 模型仍回原语言执行，不能把静态复现称作统计分析翻译。
