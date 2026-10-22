# 结果分析图型

这些是图型模板，不按医学、组学、机器学习或来源研究分类。选择页只显示名称、画法与预览；说明和输入保留在“代码与复用”。所有新增模板使用固定种子的示意输入，每个只表达一种图型，图中不加来源脚注。复用真实结果时接入已有分析输出，不由图型名称推断分析过程。

| 标识 | 图型 | 输入与展示规则 |
|---|---|---|
| `precision-recall` | PR 曲线图 | 二元标签与连续得分；示意 AP 按召回率增量加权精确率，合并并列得分 |
| `confusion-matrix` | 混淆矩阵图 | 真实类别与预测类别；行是真实类，列是预测类；可切换计数、行/列归一化及文字显示 |
| `calibration` | 校准曲线图 | 二元标签与预测概率；等宽分箱，横轴为箱内平均预测，纵轴为观察比例，省略空箱 |
| `learning-curve` | 学习曲线图 | 样本量与训练/验证误差；示意数据实际重拟合，保留五组拆分；变化带为折间 ±1 SD，可隐藏 |
| `residual` | 残差图 | 观察值与预测值；残差为观察减预测，示意预测使用独立训练集 |
| `feature-importance` | 特征重要性棒棒糖图 | 特征与重要性分布；示意为验证集置换后的 MSE 增量，误差区间为重复置换的 ±1 SD，保留负值 |
| `shap-beeswarm` | SHAP 蜂群图 | 样本×特征贡献与特征取值；按平均绝对贡献排序，颜色按各特征自身范围缩放，竖向避让不代表新变量 |
| `shap-waterfall` | 贡献瀑布图 | 单个样本的基准与逐项贡献；正负累积，最终预测等于基准加总贡献，与已有普通排序瀑布图区分 |
| `partial-dependence` | 部分依赖图 | 网格、背景记录和预测函数或已有 PDP/ICE；粗线为全部背景的平均，细线为示意个体，非置信带 |
| `decision-boundary` | 决策边界图 | 二维观测、标签及网格预测；示意为实际拟合的二变量逻辑模型，概率色带与 0.5 边界使用同一系数 |
| `enrichment-bubble` | 富集气泡图 | 条目、比例、计数和校正 P；横轴可切换命中比例/计数/富集倍数，面积与计数成正比，颜色为 −log10(校正 P) |
| `enrichment-curve` | 富集曲线图 | 排序指标与命中索引；展示加权累计得分、峰位置与同轴命中刻线，单一图型，不附拼接面板 |

既有 `bubble` 是分类行×列的矩阵气泡，可用于表达比例与连续数值；不再复制一个相同的“组学气泡”卡片。ROC、火山图、热图、PCA、曼哈顿图等沿用现有卡片。

示意 SHAP 数据来自带显式背景均值的线性模型，按 `βj × (xj − E[Xj])` 计算独立背景下的精确贡献。真实非线性模型应导入实际解释结果及其输出尺度，不能沿用这一公式或用任意随机数冒充 SHAP。富集气泡示意输入保留成员集合，实际计算单侧超几何 P 和十个条目的 BH 校正；富集曲线只计算展示的累计得分，不生成未计算的归一化得分或置换 P。

普通字体、坐标、颜色、图例内部编辑、保存、组图与高质量导出均沿用工作台。模板曲线顶点、类别序号和排序位置不作为通用回归的新观测；残差散点与决策图的原始二维观测可以按明确需求参与拟合。

绘图实现为 `scripts/analysis_templates.py`，创建图件后随项目复制到 runtime；源码入口和 `.template-data.json` 同步保存。跨图复用仍通过语义角色匹配，不能以对象 ID 推断变量。

画法参考：[PR/AP](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html)、[概率校准](https://scikit-learn.org/stable/modules/calibration.html)、[PDP/ICE](https://scikit-learn.org/stable/modules/partial_dependence.html)、[SHAP 蜂群](https://shap.readthedocs.io/en/stable/example_notebooks/api_examples/plots/beeswarm.html)、[富集结果可视化](https://yulab-smu.top/biomedical-knowledge-mining-book/enrichplot.html)。参考用于核对图型定义，未嵌入来源研究的图片或数据。
