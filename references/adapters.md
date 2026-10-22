# 代码接入、重建与扩展

下列 `<skill>` 与 `<project>` 均替换为绝对路径并正确引用；PowerShell 用 `&` 调用带空格的命令路径。

```powershell
python <skill>/scripts/studio.py --project <project> import-python <绘图脚本.py>
python <skill>/scripts/studio.py --project <project> import-python <绘图脚本.py> --args --season summer
python <skill>/scripts/studio.py --project <project> import-vector <原语言接入清单.json>
python <skill>/scripts/studio.py --project <project> import-svg <图1.svg> <图2.svg>
python <skill>/scripts/studio.py --project <project> import-image <原图.png>
python <skill>/scripts/studio.py --project <project> data <数据.csv>
python <skill>/scripts/studio.py discover <当前绘图目录> --hint <图名>
python <skill>/scripts/studio.py --project <project> template pca
python <skill>/scripts/studio.py --project <project> demo
```

`discover` 仅读取指定文件目录；不搜索其他聊天记录。Notebook 把目标绘图单元与所需导入、变量写成可重放 `.py`，保留原 notebook 路径和单元索引。捕获器拦截 Figure.savefig，故不写原脚本原定图片输出；它不隔离原脚本的其他文件、进程、网络或数据库动作。需要隔离时提取绘图函数，以明确的数据输入运行。

## 本地工作台生命周期

长期编辑窗口用 `python <skill>/scripts/launcher.py --project <project>`，自动复用已有服务；自动测试或不另开浏览器时加 `--no-open`。`studio.py ... serve` 保留前台调试用途，不作为 Codex 会话结束后还需存活的启动入口。

Windows 的隐藏控制台和一次 `CREATE_BREAKAWAY_FROM_JOB` 仍可能留在外层 `KILL_ON_JOB_CLOSE` 进程组。启动器通过本机 `Win32_Process.Create`、`ShowWindow=0` 启动独立服务，日志写到项目 `studio.log`，超过 2 MB 时保留一份上一日志；服务本身不注册系统服务；只有明确启用 `--resume-on-login` 时才添加当前用户 Startup 中该项目唯一的恢复快捷方式。已实测模拟关闭调用者的测试进程组，原服务失联、修复后服务及 URL 保持可用。官方机制见 [Windows 进程组](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects) 与 [Win32_ProcessStartup](https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-processstartup)。

每个项目一个 `.launcher.lock` 防止连续点击启动多个写入进程；操作系统在调用者退出后自动释放锁，保留锁文件不代表占用。`/api/health` 需当前 token / cookie 并返回项目与进程身份，不等待绘图锁，不能把繁忙导出当作服务已停止；普通 HTTP 200 也不能认定是本工作台。启动检查绕过外部代理，只访问已验证的 loopback 地址。启动失败显示原因，不返回过期链接。正常启动同时运行无绘图库依赖的轻量守护（每 4 秒一次健康请求，失败三次再恢复）。掉线后自动打开可见 CMD，沿用 `ensure_studio` 的单项目锁与身份检查，成功后重新打开工作台。失败后最短 60 秒重试，逐步延长到最多 300 秒；持续正常 120 秒后重置退避，防止反复弹窗。后台不启动额外 HTTP 端口，正常检查不写日志；recovery.log 超过 256 KB 保留一份上一日志。

Python 接入会从目标脚本的运行命名空间提取 DataFrame 和等长一维数值/字符串数组，作为候选数据集出现在批量绘图的选择列表。DataFrame 保留其表格列；数组按长度组合，添加明确标记的 row_index 行序号。不会自动把数组名称解释为科学变量角色。最多 10 万行、每个数据集 100 列；复杂数据结构由 Codex 按用户指定的上下文抽取。

Python 绘图依赖是原脚本自己的依赖；先检查现有环境，不自动重写分析方法来绕开缺包。手工 `Figure()` 在 `savefig` 时捕获；重复使用同一 Figure 更换数据多次保存时，按每次输出保存独立快照，同一状态重复保存多个格式会去重。

### 独立用户脚本的类型与输入声明

普通 Matplotlib 图无需引用本 skill。可选声明用于保留图型身份、接入专用选项及打包数据：

```python
fig._fam_chart_type = 'network'  # 使用图型目录中的 kind，仍登记为 original-source
fig._fam_input_files = ['data/nodes.csv', 'data/edges.csv']
# 或在脚本顶层声明 FAM_INPUT_FILES，适用于所有捕获图。
```

导入名称优先采用坐标区标题，其次总标题。`chartType` 不把用户图转换为模板，不改原计算。网络、地图、模型分析等专用规则还需要明确的数据和对象映射；仅声明类型不会从像素推断这些关系。既有 `_fam_template_data` 是适配器沿用的数据协议字段，并非生成模板的接口。不要据此把真实原代码图件的 provenance 写成 template。

输入文件必须是脚本目录内存在的相对路径，保留目录结构；目录外路径和越界符号链接拒绝导入。快照目录的身份同时包含代码及声明输入的哈希，同一代码重新导入新数据不会覆盖旧快照。未声明的任意文件、第三方包、远程数据库不自动打包；先列清重跑所需依赖。原脚本自带的命令行参数仍保留。

网络普通 `ax.text` 标签以唯一的显式节点 ID 匹配，保留它与节点的原数据坐标偏移；`annotate` 的明确数据锚点也可绑定。重复 ID、无映射注释不靠距离猜测。节点布局、拖动和隐藏仍保持关联边与已绑定标签联动。

此项目中的 `examples/user-data-workflow` 提供独立 CSV 和 Python 脚本，先自行计算 57 种图，再按上述声明导入；它不调用模板生成器。修改展示后用 `reproduce.py` 重放完整设置，或用原脚本的 `--target` 沿用原计算拓展变量。批量窗口的通用 X/Y 图生成不替代脚本内的训练、检验或专用统计流程。


### 自动掉线恢复与登录恢复

浏览器的“无法访问此站点”页面不能执行原工作台 JavaScript；恢复由独立本地进程检测工作台服务，而非监控其他网站或浏览记录。检测需连续失败，通常十余秒后打开 CMD，再等待服务就绪。原端口空闲时保留地址和 token，冲突时启动器返回新地址并重新打开浏览器；不强行停止未知进程或卡住的监听者。只恢复已保存内容，未提交的浏览器草稿不能保证恢复。

```powershell
python <skill>/scripts/launcher.py --project <project> --resume-on-login --no-open
python <skill>/scripts/launcher.py --project <project> --recovery-status
python <skill>/scripts/launcher.py --project <project> --disable-recovery
```

登录恢复是 Windows 当前用户的单项目 `.lnk`，不需要管理员权限。不启用该选项时，关机后需再次启动入口。`--disable-recovery` 等待守护退出并移除自己登记的登录快捷方式，保留已运行工作台；需要主动停止工作台时先关闭守护，再核对服务身份后停止。`--no-recovery` 适用于一次性调试与隔离测试，只跳过本次启用，不关闭已有守护。原始图、输入、`project.fam.json` 和 `settings.json` 不由恢复器写入。

配置与状态仅位于该绘图项目的 `.recovery.json`、`.recovery-state.json` 和少量锁文件。锁由操作系统释放，磁盘上存在锁文件不代表仍有进程。同步 / 更新启动器代码后，如需让旧守护加载新代码，先关闭该项目守护再启用；无需停止绘图服务。


## R

```r
source("<skill>/scripts/bridge.R")
fam_save(p, "figure.svg")
fam_save(function() plot(x, y), "base.svg")
# Prefer svglite: fonts remain semantic text.
svglite::svglite("figure.svg", width=6.4, height=4.8)
print(p)
grDevices::dev.off()
p_new <- p + fam_theme("<project>/settings.json", figure_id="f-...")
```

优先用 R 绘制未指定语言的新科研图。`fam_save` 默认使用 svglite，保留可编辑文字；缺少该包时明确提示安装，不静默退回字形路径。使用 `fam_manifest` 生成源代码、SVG、输入文件和数据集声明，然后执行 `import-vector`；它保存代码和输入的独立快照，不执行源码。完整清单和四种语言导出见 [language-export.md](language-export.md)。

需要逐行联查、误差跟随或按组批改时，采用 [publication-tools.md](publication-tools.md) 的 `fam_save_semantic` 协议，复制 `bridge.R` 时必须同时复制 `bridge_semantic.R` 与 `ggplot_bridge.R`。声明唯一 ID、原始行与图层角色；支持直角分面及 identity 点/柱/格子/线段/误差杆。汇总结果先在 R 中计算为有 ID 的结果表，不从图形估算原始行。

原生 R 再绘图需要安装 R、原包和数据；此实现不把 R 图转换为 Matplotlib 来替代统计计算。为 ggplot/ape/ComplexHeatmap 等添加 native 参数时，建立参数 JSON→R setter→SVG 的适配器；所有额外数据操作记录在 provenance 中。

## 其他语言与特殊图型

用户期望三维编辑时先完成[三维接入检查与分层地图适配](3d-adapters.md)，不可仅把二维投影导成 SVG 交付。


| 系统 | 接入 | 注意 |
| --- | --- | --- |
| Plotly | `fig.write_image(..., format="svg")` | 保留 figure JSON；需要 Kaleido。原生三维 WebGL 部分可能是位图，应保留原相机适配器。 |
| Julia | 当前绘图库的 SVG 输出 | 保留 Julia 源码、Manifest 和数据映射。 |
| MATLAB | SVG 可用时或矢量 PDF 转 SVG | 检查目标版本的输出格式，保留 `.m` 与 MAT 数据。 |
| C | 原程序输出 SVG，使用 `import-vector` 声明 `.c`、头文件和输入 | 保留编译依赖及原计算；编辑后的 C 复现代码使用 ISO C 和标准库。 |
| GIS、网络图、桑基图、环形树、光谱图 | 可含文本/路径的 SVG 或 Matplotlib 图 | 动态数据修改使用原库适配器，图形编辑本身不限制图型。 |
| Canvas/WebGL HTML | 找到生成程序与其参数 | SVG 接入不能恢复 canvas 内对象。抽出参数重新生成语义图，或保留原 WebGL 实时界面并连接项目状态。 |

SVG 导入保留安全 CSS 与嵌入的 PNG/JPEG；移除脚本、外部引用、foreignObject 和动画。字体已变路径的 SVG 无法直接改 font-family：用来源代码导出文本，或创建语义文字层，隐藏原字形层。

## 无源码重建

普通 PNG/JPG 的接入流程为先根据参考重绘类似图，再导入重绘代码进行编辑；不要求自动识别位图内的要素。真实数据缺失时明确记录未知与示意值。通用矢量要素编辑与显式绑定见 [vector-editing.md](vector-editing.md)。

1. 看源图并记录面板、图型、轴尺度、标签、图例、颜色、字体、误差线和三维视角。
2. 找当前任务文件内的数据与计算代码。找不到时将数值标为 unknown，不把示意值与真实值混用。
3. 创建 `reconstructed_figure.py` / 原语言脚本以及 `reconstruction.json`。记录 originalImage、dataSource、knownValues、unknownValues、inferredStructure 与 validation。
4. 用真实数据恢复图。只有演示时才用示意数据并在标题/来源记录中写明。用户要求图上数字化取值时，单独提供像素校准与误差说明，仍不等同原始观测。
5. 导入重建脚本。保留参考层，展示并比较布局；不能把“看起来接近”描述为准确恢复原代码。

## 原生代码回写

原文件保存在 sources 快照；建立 `<stem>_fam.py` / `.R` 和参数 JSON，保留原数据和计算。全图样式使用 helper，文字/图例/点/线的单独属性按语义对应原 Artist/ggplot layer。Matplotlib 语义 ID 示例 `fam-a0-title`、`fam-a0-line-0`、`fam-a0-legend`。任意 SVG leaf 的像素坐标改动未必等同原语言 data-coordinate setter；此时由 SVG 后处理重放精确编辑，并说明原生源码只覆盖已映射的属性。

导出窗口可选择 R、Python、MATLAB 或 C，新的项目默认 R；完整场景复现均包含源代码和已声明的输入。该复现独立于 Python 内核（Python 选项自身除外），不自动把不同语言的统计模型互相翻译。R 或 MATLAB 的未知图层仍是 SVG 对象；专用统计参数及联动需要显式对象/数据映射。原生三维相机需保留原语言适配器，场景包记录当前三维投影。

需要对某脚本出现的变量一键扩展时，先把其绘图过程包装为 `draw(data, target, style)`；列出候选目标变量与类型，用户选择后在相同流程循环。不自动添加显著性检验、换插值算法或挑选预测变量。


## ggplot 坐标与分面接入

SVG 文本/路径可编辑并不代表坐标框和范围可编辑。需要这些能力时读 [ggplot-semantic.md](ggplot-semantic.md)，提供 R 计算场景并执行 `check-editability --require-axes`。分面接入后先编辑独立单图，再进入引用组图；不能用没有 axes 的 SVG 冒充坐标适配完成。


## 四语言原生坐标桥接

R / Python / MATLAB / C 可经 `fam-native` JSON 登记明确的坐标、误差、数值色带和 XYZ，再由 `import-vector` 接入；不必先写一份 SVG。详细支持范围、桥接函数、来源身份与运行示例见 [native-coordinates.md](native-coordinates.md)。Matplotlib 仍优先原生捕获，既有 ggplot 接入保留；一般 SVG 接入及未知几何的限制不变。
