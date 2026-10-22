# R ggplot 的坐标、统计几何和独立分面

适用于已有 R/ggplot 源码和真实数据，用户需要缩放坐标框、改范围、编辑箱体/标注或拆分分面的情况。普通 `import-svg` / 无 scene 的 `import-vector` 仍只提供通用对象编辑，不能恢复坐标或统计参数。

## 接入

保留原 R 源码和输入，在受控输出目录执行纯绘图部分；先排查源脚本副作用。不要将执行上传源码作为浏览器导入的隐式步骤。

```r
source("<skill>/scripts/bridge.R", encoding="UTF-8")
# p 是原 R 绘图代码和真实数据生成的 ggplot 对象
fam_save(p, "plot.svg", width=10, height=8)
fam_save_ggplot(p, "plot.scene.json", width=10, height=8)
fam_manifest("draw.R",
  figures=list(list(svg="plot.svg", scene="plot.scene.json", name="结果图")),
  inputs=c("data.csv"), file="import.json")
```

```powershell
python <skill>/scripts/studio.py --project <project> import-vector import.json
python <skill>/scripts/studio.py --project <project> check-editability --require-axes
```

scene 是 `ggplot_build` 已计算的坐标、统计量、刻度、样式和分面布局。导入器读取 JSON、保留来源快照，用 Python 内核生成可编辑坐标和对象；拖动时不运行 R。原始 SVG 是外观参考；这不是逐像素复刻 R 的所有排版细节。字号/线宽保持物理单位，拆出的单图重新安排留白。原 R 整图标题和 caption 保留在 scene，分面独立图以分面值作标题。

当前支持普通 Cartesian、未变换的连续或离散轴，point、boxplot、text、segment、hline/vline、line/path、bar/col、errorbar、tile。固定比例坐标、横向统计几何、变换后的原始坐标、极坐标、专门几何或连续色带需要单独适配；遇到未支持几何明确拒绝，不用截图或无坐标 SVG 兜底冒充完成。不要把这里的统计汇总值当成原始样本。

## 行身份与箱线样本

`source_ids` 是按图层编号命名的列表，例如 `list("1"=ids)`；ID 顺序必须与该层 `ggplot_build(p)$data[[1]]` 完全对应。特别是 `position_jitter` 会重排分面；核对 PANEL、分类和数值后才传入，不能直接套用原表顺序。没有显式 ID 的散点保留显示编辑，但不作为拟合样本。重复背景层也不参与拟合。

`box_samples=list("2"=list("1:1"=values))` 按“图层→PANEL:group”传入原始数值。导出器用原 R 四分位数核对 lower/middle/upper；匹配后才开放需要样本的箱线画法。原始箱体/须线沿用 R 统计量。需要重算统计或更换变量时仍回到原 R 分析流程。

## 单图再组图

每个分面建立一张独立单图。多分面额外建立按原 row/col 排列、引用单图的组图；不是将完整 SVG 当作一个面板。单图右侧“查看组合图”，组图右侧“单独编辑此子图”，保留当前子图定位。修改单图会更新未被面板独立覆盖的组图设置；组图内独立编辑保持局部作用，不反写单图。导入后默认打开单图。

交付前在真实图上用八向手柄调整坐标框，核对点、箱体、显著性标注和刻度跟随；验证范围、字体、颜色、宽度、保存重开和组图导出。原始源码、数据和 R 计算场景必须通过现有完整性校验。
