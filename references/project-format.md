# 项目状态与复现

`project.fam.json` 与 `settings.json` 保存同一完整项目。顶层包含 version、id、name、figures、groups、datasets、active 和 revision。浏览器保存使用 revision 冲突检查；每 10 次修订保留历史快照，最多 30 份。

figure：id/name/backend/style/native/overrides/axes/provenance。Matplotlib 记录 cache；SVG 记录 svg。source 是 sources 中的相对路径。provenance.kind 区分 original-source / dataset / vector-import / raster-reference / synthetic-demo。

`chartType` 记录用户源码显式声明的图型，用于显示适用的编辑控件；不把真实源码导入图伪装成模板。捕获基线保留此字段，恢复原始图后仍可使用相应控件。源码的 `_fam_input_files` 或 `FAM_INPUT_FILES` 声明相对数据路径，导入时将输入与代码一同快照到 `sources/`，以 SHA256 核对，拒绝超出源码目录的依赖路径。外部脚本和数据后续修改不会覆盖已有快照。

style 的字号以 pt 或 SVG user units 表示，width/height 为英寸。preserveOriginal=true 时字体和外观字段仅应用 edited 中列出的项。一键统一全图格式设置 preserveOriginal=false，继续保留 overrides。画布 `transparent` 是独立展示设置，默认 true；明确设为 false 时保留不透明背景。组图与标题自动布局参数见 [composition.md](composition.md)。

```json
{
  "style": {"fontFamily":"Arial", "fontSize":11, "titleSize":15,
    "labelSize":12, "tickSize":10, "textColor":"#243742", "background":"#ffffff",
    "lineWidth":1.2, "width":6.4, "height":4.8, "grid":false,
    "spines":true, "preserveOriginal":true, "edited":["titleSize"]},
  "native": {"axes":{"0":{"xlabel":"Time", "xlim":[0,10],
    "position":[0.15,0.16,0.76,0.70]}},
    "camera":{"azimuth":-45,"elevation":30,"roll":0,"projection":"ortho","aspect":[1,1,0.7]}},
  "overrides": {"fam-a0-title":{"css":{"fill":"#216e83", "font-weight":"bold"},
    "tx":0,"ty":-8,"rotate":0,"scale":1}}
}
```

overrides 可作用于 SVG leaf 或 group，css 为安全样式属性，attrs 为允许的几何属性，text 修改文本内容，hidden 隐藏对象，tx/ty/rotate/scale 是对象显示变换；pivotX/pivotY 指定旋转缩放中心。create=text/rect/line/circle/ellipse/polygon/path 可创建注释或几何对象。对象移动只修改显示坐标；源数据仍保持原值。

group 包含 width/height（英寸）、labels、labelSize/labelFamily/labelWeight/labelColor、background、transparent、layout={cols,gap}、panels。每个 panel 包含 figure（来源 ID）、x/y/w/h（占组图的比例）、label、labelX/labelY（标签偏移，pt）、settings。settings 允许 style/native/overrides/affine/originalBaseline，覆盖本面板，来源图不变。originalBaseline=true 时先从来源的捕获基线建立图，再应用面板设置，不继承来源已有的展示修改。嵌入 SVG 对象 ID 加 p0-/p1- 前缀，data-original-id 保存来源 ID，所有 clip-path 与 href 同步加前缀避免串图。

group.physicalFonts=true 时 Matplotlib 在面板实际英寸尺寸内重绘，字号/线宽为实际 pt。通用 SVG 仍比例缩放；旧项目缺字段时保持旧的缩放方式。此设置不修改来源图及 panel.settings.style 内保存的原单图尺寸。

dataset 保存 columns 的 numeric/missing 检查、原始行数、sources 的 JSON 数据快照和内容 SHA256。批量默认遇到缺失或非有限数值就停止；显式选择 missingPolicy=omit 时，逐图按实际映射变量进行完整观测筛选，矩阵图则对所选列共同筛选。原表不改、不填补，provenance 保存 sourceRows、rowsUsed、excludedRows（零基行索引）及策略，原语言生成脚本也重放该筛选。没有有效观测时拒绝绘图，不回退成演示数据。不合适映射仍使整批停止，项目保留开始前状态。

完整复现：`python reproduce.py --format svg --ids f-... g-...`。缓存 Matplotlib 对象保留实际数据和 Artist，原设置在复制对象上应用，因此界面编辑不破坏基线。SVG 后处理保留个别对象编辑；组图同样从此管线生成。缓存仅适用于自己创建的项目，不要接受外来 pickle；跨版本迁移使用源码重新接入。

可加 `--output <目标目录>` 将复现结果输出到另一目录；不指定时沿用项目的 `exports/`。原代码重跑用于重新计算，`reproduce.py` 用于准确重放已保存的展示编辑，两者分别保留。

R/MATLAB/C 的 `import-vector` 记录 `provenance.language`，快照原代码及明确声明的辅助文件、CSV 和输入 SHA256；声明中的 SVG 对象可显式绑定 entity/follow 关系，不按外观距离推测。后端仍为 SVG，不能声称具有未映射的原生统计参数。编辑后可用 `studio.py export-code --language r|python|matlab|c` 导出独立场景包；`manifest.json` 保存设置、原输入哈希及 `analysisRecomputed=false`，`scene.tsv` 保存可编辑的矢量结构。`draw.R` / `draw.py` / `draw.m` / `draw.c` 使用对应语言重放完整编辑，原始分析脚本放在 `original/`。详见 [language-export.md](language-export.md)。

`apply_style.py` 从 runtime/adjustments.py 应用 Matplotlib 全图与 native 格式字段（轴、图例、系列、色标和相机）；R 的 `fam_theme` 应用 ggplot 全图字段。它们不是任意 SVG leaf 编辑、组图和树重建的等价原生表达，完整结果以 `reproduce.py` 为准。新增 native 参数见 [adjustments.md](adjustments.md)。axes/baseline/metadataVersion=2 记录捕获元数据；工作台通过 inspect API 获取实际当前参数。坏设置验证后拒绝写入；并发 revision 冲突同样拒绝。会话内撤销/重做可以恢复已捕获图件，无需重新执行分析。

PNG/TIFF 像素 = 英寸 × DPI，写入 DPI 元数据；PDF 页面使用同一英寸尺寸，SVG 原矢量保留。原图内嵌栅格仍为栅格。DPI 可选 72–1200；尺寸像素积最多 1 亿。

## 语义联动设置

`native.layers={data:{visible:true,locked:false,style:{color:"#216e83"}}}` 保存七层状态。`native.entities={"fam-a0-line-0::p1":{dx:0.05,dy:0.03,errorScaleY:1.2}}` 保存中心展示位移及区间倍率。显式坐标用 `mode:"coordinates",value:[x,y,z]`；柱用 `barValue`。`native.seriesMoves` 保存所属系列的比例位移，`native.bindings` 明确从属关系。原生 apply_style.py 可以重放这些设置；SVG 装饰覆盖和组图仍用 reproduce.py。按 [layers.md](layers.md) 核对坐标与适配边界。

`native.axes[轴索引].labelStyles/tickStyles/spineStyles`、`native.secondaryAxes`、`native.barLayouts` 的完整字段见 [geometry.md](geometry.md)。`geometry.py` 随项目 runtime 复制，供 `apply_style.py` 和 `reproduce.py` 重放。修改布局不写回原始分类或测量值。状态完全未变化时保存不增加 revision。

`native.entities[实体ID].style={color,edgeColor,alpha,fill}` 是单点/观测显示样式，在最终 SVG 中按实体匹配应用，支持数值映射点和 3D 投影点，保留其数据和色标。fill 为 solid 或 none，分别为实心与空心。空心点只改 alpha 时保留空心；选填充色切换为实心。完整重放用 `reproduce.py`，不把这部分 SVG 覆盖宣称为普通 Matplotlib helper 的等价输出。`native.artists[Artist ID]` 控制底层对象颜色和 alpha；逻辑系列用下述 seriesStyles。`native.legends[轴索引]` 支持 textColor/titleColor/faceColor/edgeColor/alpha；`entries[条目索引]={color,edgeColor,alpha,textColor}` 控制单个图例符号与文字，symbolColor/symbolAlpha 可由代码统一设置。图例背景 alpha 和符号 alpha 分开。图例布局调整保留捕获的组合符号、各条文字字体和原有属性。

`native.seriesStyles[逻辑系列ID]={color,edgeColor,alpha,fill,order}` 控制逻辑数据系列。柱图系列 ID 形如 fam-a0-bars-1，对应捕获 BarContainer，该组全部柱共享数据样式；已绑定误差仅共享位置关系，颜色独立。曲线/散点系列保留主要 Artist ID。检查元数据的 semantic.series 和实体 seriesId、图例条目的 seriesId 提供关联；图例文字无法唯一匹配时不建立推测关系。原 `native.artists` 继续用于底层 Artist 属性，不能把单个柱 Artist 当整组。

`order`、实体/图例的 `styleOrder` 是单调递增的展示样式顺序；系列 `orders` 和实体/图例的 `styleOrders` 分别记录 color、edgeColor、alpha、fill 的属性顺序。最近一次用户明确的该属性整组或单点/仅符号操作优先；旧设置缺顺序时为 0。系列改色可以统一此前单点改色，后续单点修改仍独立；只修改整组 alpha 不覆盖独立点颜色。全量准确输出用 reproduce.py。

`native.axes[轴索引].titlePosition=[x,y]` 保存坐标标题在轴框内的位置；`native.legends[轴索引].anchor=[x,y]`、loc 和 borderAxesPad 保存图例拖动位置。原生拖动用 SVG 绘制阶段记录的 legend.layoutBox（72 dpi 物理点）计算锚点，frameon=false 时也不把文字外接框冒充完整布局外框。整图总标题和通用语义 SVG 装饰使用 overrides 的对象平移。

子图的 `native.entities[ID].reset=true`、`native.seriesMoves[ID].reset=true` 和 `overrides[来源对象ID].reset=true` 表示该对象从捕获原始状态开始应用此面板的设置，阻断来源单图的同对象覆盖。对象键使用来源 ID，不能使用组图的 p0-/p1- 前缀。其他对象、系列格式和来源图保持。

`native.axes[轴索引].titleStyles={fontFamily,fontSize,color,fontWeight,fontStyle,horizontalAlignment}` 保存独立坐标标题格式；多行内容保存在 title。`native.legends[轴索引].placement` 记录图内/图外/自定义位置选项，`anchorReset=true` 明确清除来源图或拖动遗留的 bbox 锚点，避免组图深度合并重新继承旧位置。

论文版式、同名分组配色和组图比较结果仍保存为上述 style/native/panel.settings 字段，runtime 包含 research.py。无需新增不可复现的浏览器私有样式；选择性的完整工作流见 [research-workflow.md](research-workflow.md)。

撤销/重做为会话内各最多 10 个快照，同时记录当前子图选择，恢复或重排组图后校验选择范围。保存文件的 revision 历史仍为原来的定期备份。

分布和画法扩展：`native.boxPlots`、`native.boxStyles`、`native.plotVariants`、实体的 `barWidth/boxWidth/errorStyle` 见 [distributions.md](distributions.md)。语义读取返回 distributions（样本可用性、箱体与组件）和 plotTypes；这些派生元数据不修改捕获快照。
