# 论文参考模板与真实数据接入

v1.0 开发版当前目录去重为 69 种图型：16 种基础图、8 种保留的论文参考图、13 种新增科研图，12 种结果分析图型，8 种地图图型，以及 12 种新增图型。一个模板只表达一种图型，UpSet 集合矩阵、生存风险表和色标属于主图解释组件。完整目录及合并关系见 [chart-catalog.md](chart-catalog.md)，结果分析模板见 [analysis-templates.md](analysis-templates.md)。界面只用图型名称，不用领域名称。旧论文来源、输入和绘图实现继续保留；新目录由 `scripts/scientific_templates.py` 管理，新建版本 `single-v3`（旧 `single-v2` 保留复现），不覆盖旧版脚本的布局。

## 如何选择与复用

工作台“＋ 模板”按图型名与画法关键词搜索，查看实际预览；不显示领域筛选、期刊标签或论文名。选择后生成可编辑原生图，来源、原代码、示意输入 / 公开摘要数值一并保存。图下“代码与复用 → 原代码与来源”可查看论文链接和完整绘图实现；`sources/*.template-data.json` 保存本版输入。

当前成图与模板预览不显示左下角演示说明，画布默认透明；数据性质和来源继续保留在上述来源信息中。原论文图注的统计定义仍须按来源核对，不因移除展示说明而改变分析方法。

当前目录只有 RECOVERY 森林图使用已核对的公开摘要数值，其余统计和观测输入均为示意；地图的真实 Natural Earth 地理边界与示意观测分开记录，详见 [map-templates.md](map-templates.md)。旧版另一款森林图和 Virchow AUC 对比已从选择页合并移除，既有项目仍可复现。以下来源表保留旧版参考记录，不代表每项仍作为独立模板显示。新增加的 13 种图使用确定性合成输入和明确计算说明，不声称复原原论文图或患者数据。新增图型的方法入口是代码内的参考链接，本次网页连接失败，未将其记作已重新核对的论文来源。

基础批量界面的 X/Y 映射不适合直接生成生存、ROC、共突变等专门图。接真实数据时由 Codex 修改模板函数的数据读取，沿用当前任务确认的统计方案；不可把示意样本继续用于真实研究。`km_estimate`、`roc_values` 和 `bh` 可独立用于满足其输入要求的数据；检查真实研究是否需要不同删失模型、竞争风险、权重、多分类、聚类抽样或不同多重校正，再使用。

| 模板 | 接真实数据所需字段与解释 |
|---|---|
| 生存 | 患者 ID、随访时间、0/1 事件指示、分组、时间单位；风险人数从同一记录计算。当前为右删失 KM 与 log-log Greenwood 区间，无 HR / P 值推算 |
| 森林 | 分组名、效应值、上下区间、效应类型；RR/HR/OR 的参照为 1，均值差参照为 0。当前为 RECOVERY 四个公开 RR 与 95% CI，不是完整年龄分层图 |
| 瀑布 / 泳道 / 个体曲线 | 同一患者 ID、时间、靶病灶变化、治疗持续与事件；区分最佳变化、当前变化和随访充分性，不从单柱认定完整 RECIST 疗效 |
| ROC | 同一记录的二分类标签与预测分数、验证集归属、抽样单位。当前 AUC 从排序曲线计算，阴影为 100 次重抽样的逐点百分位区间；不能当作临床验证 |
| AUC 对比 | 模型、数据集、AUC 与有来源的区间；当前仅抄录四个总体点估计，无捏造误差线。横轴截断到 0.8 已显示，可在坐标框层改为 0–1 |
| 箱线 / 样本点 | 样本 ID、组别、指标值、样本独立性。图注说明 Q1–Q3、中位数、1.5 IQR 须线；点与箱体绑定，图宽和细节可改 |
| 嵌入 | 已计算的二维坐标、细胞注释、样本 / 批次分组。当前高斯簇仅展示布局，轴名说明示意；不能把它当作已执行 UMAP |
| 热图 | 原矩阵、特征 / 样本标签、分组与标准化方式。当前按行以样本 SD 标准化，无假称层次聚类 |
| 火山 | 真实分析输出的效应值与校正 P 值，以及预先确认的阈值。当前示意正态表达用已知方差双侧 Z 检验并作 BH 校正，不代替 RNA-seq 分析 |
| 共突变 | 病例 ID、基因、离散事件类别、样本分组及缺失测定标志。当前灰色为无示意事件，不表示缺失；顶条与矩阵来自相同事件数据 |
| Manhattan | 染色体、位置、表型、P 值与校正策略。当前位置为顺序索引，P 值为示意摘要；不能据此报告真实位点 |
| 筛选流程 | 各步骤人数、排除理由、分配与分析集。当前用逻辑自洽的示意人数，借鉴队列流程表达；不把简图当作完整 CONSORT 报告 |
| 气候 | 情景、时间、集合成员、暴露比例与人口；保持面板组色和单位。当前阴影为集合 5–95 百分位，不写为 SE / CI |
| 材料 | 模型、训练规模、评估误差、材料及重复运行。当前为示意数据；分材料误差杆为六次模拟运行的样本 SD |
| 生态 | 测量温度与响应、模型结果、导数、站点分组和回归计算。当前为示意响应函数及 OLS 的正态近似均值区间，不冒充论文 MMRT 与空间回归 |

对这些图，调整颜色、字体、显示宽度和画布不等于重新统计。修改真实观测或模型需要重新运行原分析；不能把手动挪动图点后的形状称为更新后的统计结果。给批量复用设置时按轴、分组和组件语义匹配，避免把所有曲线 / 所有面板误作同一变量。

## 可迁移的图形特点

以下是对所选样例的设计归纳，并非所有高水平论文的统一规范：

1. 一个面板回答一个比较问题。患者时间、最佳疗效与治疗持续使用不同视图，跨视图保持同一 ID。
2. 组色和点形跨面板保持；连续数值用连续色带，离散事件用离散颜色，其他信息不抢主结论。
3. 不只给柱高：同时展示独立样本、区间、删失、风险人数或事件。明确 n 是患者、细胞、样本还是重复运行。
4. 轴单位、对数尺度、参照值和阈值明确；生存、AUC、P 值、基因组位置不可混用一般数轴的解释。
5. 多面板文字层级一致，图例共享，必要面板保留同样的坐标尺度；不要为了统一而抹去变量或单位差异。
6. 图注解释计算与数据来源。95% CI、SD、SE、5–95 百分位与逐点重抽样区间各自有含义，不相互替换。

## 来源清单

| 原论文与参考位置 | 参考模板 |
|---|---|
| [RECOVERY，NEJM 2021，Fig. 2–3 与正文](https://www.nejm.org/doi/full/10.1056/NEJMoa2021436)；可读收录版为[初步报告](https://pmc.ncbi.nlm.nih.gov/articles/PMC7383595/) | 森林图；KM 表达参考 |
| [DRAGON，Nature Medicine 2026，Fig. 2a–c](https://www.nature.com/articles/s41591-025-04157-w) | 泳道、个体曲线、瀑布 |
| [Virchow，Nature Medicine 2024，Fig. 2b](https://www.nature.com/articles/s41591-024-03141-0) | 公开 AUC 对比 |
| [INSPIRE，Nature Communications 2021，Fig. 1B,D–H](https://www.nature.com/articles/s41467-021-25432-7) | KM、流程表达 |
| [Wilk 等，Nature Medicine 2020，Fig. 1b–d](https://www.nature.com/articles/s41591-020-0944-y/figures/1) | 示意嵌入、箱线样本点 |
| [Shen 等，Cell 2020，Fig. 2C、4A、S3](https://pmc.ncbi.nlm.nih.gov/articles/PMC7254001/) | ROC、注释热图、火山 |
| [TCGA，Nature 2014，Fig. 3c](https://pmc.ncbi.nlm.nih.gov/articles/PMC4231481/) | 共突变矩阵 |
| [COVID-19 HGI，Nature 2021，Fig. 2a](https://pmc.ncbi.nlm.nih.gov/articles/PMC8674144/) | 多表型 Manhattan |
| [Lenton 等，Nature Sustainability 2023，Fig. 2](https://www.nature.com/articles/s41893-023-01132-6) | 六面板情景图 |
| [Merchant 等，Nature 2023，Fig. 3](https://www.nature.com/articles/s41586-023-06735-9) | 材料模型比较 |
| [Alster 等，Nature Communications 2023，Fig. 1–2](https://www.nature.com/articles/s41467-023-41096-x) | 温度响应与回归 |

检索日期 2026-10-08。临床 / 医学参考来自本次网页检索，本地文献索引没有直接支持这些医学图型的论文条目；生态参考同时核对了本地索引中的 Alster 2023 完整条目。部分网页存在访问限制，使用期刊 PDF、图件页或作者原文的 PMC 收录版；未把只读图注的条目声称为已查看原图。工作目录的原图参考资产只供研究核对，插件预览均为新绘制模板，不嵌入原图。

## 基础图型的论文参考与改绘范围

以下是版式参考和可计算的示意输入；除森林图外，没有转录原图坐标或宣称恢复原论文数据。

| 图型 | 原文参考 | 本模板改绘范围 |
|---|---|---|
| 分组柱状图 | [Nature Communications 2021 · Fig. 4d](https://www.nature.com/articles/s41467-021-24838-7) | 柱形、重复点与误差的表示方式改绘为两组并列模板。 |
| 饼图 / 环形图 | [Nature Medicine 2026 · Fig. 1a（构成饼图）](https://www.nature.com/articles/s41591-025-04126-3) | 保留分区配色、白色分隔与外置图例；默认环形版式。 |
| 折线图 | [Nature Communications 2021 · Fig. 1A（单变量响应曲线）](https://www.nature.com/articles/s41467-021-24789-z) | 采用单变量响应曲线的线型与组色；参数与观测为示意值。 |
| 热图 | [Cell 2020 · Fig. 4A](https://pmc.ncbi.nlm.nih.gov/articles/PMC7254001/) | 采用分组色条与以零为中心的热图；无未经计算的聚类树。 |
| PCA 图 | [Cell Discovery 2022 · Fig. 1a](https://www.nature.com/articles/s41421-022-00418-x) | 采用分组得分、灰色质心与连接线；新示意矩阵实际计算标准化 PCA、解释率和质心，非原论文得分。 |
| 系统发育树图 | [Nature 2020 · Fig. 1d](https://www.nature.com/articles/s41586-020-2012-7) | 保留枝长尺度及类群配色；使用明确的示例 Newick，不假造系统发育分析。 |
| VK 图 | [Nature Communications 2022 · Fig. 1](https://www.nature.com/articles/s41467-022-29711-9) | 主图、边缘分布与分组配色改绘；元素比由示例分子式实际计算。 |
| 散点图 | [Nature Communications 2023 · Fig. 1–2（温度响应散点与曲线）](https://www.nature.com/articles/s41467-023-41096-x) | 单独截取散点及拟合表达重建；示例 OLS 拟合不冒称论文分析模型。 |
| 箱线图 | [Nature Communications 2021 · Fig. 1G–H（分布比较）](https://www.nature.com/articles/s41467-021-25432-7) | 采用原文分布比较布局，样本为新示意值。 |
| 小提琴图 | [Nature 2024 · Fig. 1c / Extended Data Fig. 1a](https://www.nature.com/articles/s41586-023-06816-9) | 分布主体加内嵌四分位箱；独立保存真实示意样本。 |
| 直方图 | [Nature Communications 2022 · Fig. 1（边缘密度）](https://www.nature.com/articles/s41467-022-29711-9) | 将边缘分布改为独立直方图变体；明确采用新示意数据和共有分箱，不声称原文分箱。 |
| 气泡图 | [Nature 2024 · Extended Data Fig. 1e（点阵图）](https://www.nature.com/articles/s41586-023-06816-9) | 保留矩阵布局及大小、颜色双编码；两套图例分开。 |
| 森林图 | [New England Journal of Medicine 2021 · Fig. 3](https://www.nejm.org/doi/full/10.1056/NEJMoa2021436) | 转录已核对的四个公开汇总效应值及区间，改绘布局。 |
| 三维曲面图 | [Nature Communications 2021 · Fig. 1B（响应曲面）](https://www.nature.com/articles/s41467-021-24789-z) | 响应曲面表达用明确的独立响应公式改绘；不是 MuSyC 拟合结果。 |
| 三维散点图 | [Nature Communications 2019 · Fig. 1a（降维与轨迹示意）](https://www.nature.com/articles/s41467-019-09670-4) | 保留三维点云及分枝轨迹表达；生成示意 XYZ，不声称已运行 MLLE 或 STREAM。 |
| 等值线图 | [Nature 2024 · Extended Data Fig. 1c（轮廓密度图）](https://www.nature.com/articles/s41586-023-06816-9) | 用明确的高斯混合场改绘等值轮廓；不是 t-SNE 或原文细胞密度。 |

基础新版记录 `templateEdition: paper-v1`。旧基础图仍使用原种子及 `edition="legacy"` 恢复，不替换已有捕获图。自带真实数据的通用批量映射仍走数据绘图入口；不能自动套用示意模板的变换、拟合或检验。

分类色条使用离散 RGB 映射，与连续数值色标独立。柱上的样本点显式声明所属柱：移动、变宽与重排时跟随；可单独移动点。曲线与对应示意观测点显式声明同系列，按系列换色时同步；误差、区间和统计计算仍分别处理。树的比例尺不是末端标签，隐藏末端标签保留尺度。

新版式、12 个新增类型、实际数据示例和科研工具详见 [publication-tools.md](publication-tools.md)。每种类型的视觉参考在界面“科研工具… → 参考样式”，目录记录为 `scripts/design_references.json`。
