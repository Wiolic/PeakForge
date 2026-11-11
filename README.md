<p align="center"><img src="src/peakforge/assets/peakforge.png" width="88"></p>

<h1 align="center">PeakForge</h1>

<p align="center"><b>从 XPS 原始数据到可投稿的 Origin 图，几分钟完成。</b><br>
免费 · 开源 · 中文界面 · 鼠标操作即可 · 也可以直接交给 AI 分析</p>

<p align="center"><b>Developed by Eggy &amp; Claude Opus 5.5</b></p>

<p align="center"><a href="README_en.md">English</a> ·
<a href="#为什么选择-peakforge">为什么选择</a> ·
<a href="QUICKSTART.md"><b>Quickstart（零基础上手）</b></a> ·
<a href="#读懂结果">读懂结果</a> ·
<a href="docs/METHODS.md">方法说明</a> ·
<a href="src/peakforge/docs/图形界面使用指南.md">界面指南</a> ·
<a href="src/peakforge/docs/零基础XPS拟合教程.md">拟合教程</a> ·
<a href="src/peakforge/docs/XPS基础讲义.md">XPS 基础讲义</a> ·
<a href="#免责声明">免责声明</a></p>

![PeakForge 主界面](docs/images/gui_main.png)

---

## 为什么选择 PeakForge

很多实验室分析 XPS 的流程是：在仪器软件（如 Thermo **Avantage**、PHI **MultiPak**）里分峰 → 把数据导成 Excel/文本 → 打开 Origin 重新作图、逐条调颜色和图例 → 换一个样品再来一遍。PeakForge 把这条链缩短成**一个窗口、几次点击**。

| | PeakForge | 以 Avantage 为代表的常规流程 |
|---|---|---|
| **费用与许可** | 免费、开源（MIT），任何 Windows 电脑都能装 | 商业软件，通常需要许可，常常只装在仪器电脑上 |
| **数据格式** | PHI `.spe`、VAMAS `.vms`、CSV/TXT、Excel 一处打开；同一测量的 `.spe` 与 `.vms` 读出完全一致 | 各厂商软件主要面向自家格式，跨仪器、跨测试中心的数据需要转格式 |
| **出图** | **一键生成 Origin 工程 `.opju`** 和带 (a)(b)(c)(d) 编号的组合图：每个谱区一张排好版的图（数据点、背景、包络、各组分填充、图例、谱区与样品标注），可继续在 Origin 里修改 | 导出数据后在 Origin 里手动重建每张图 |
| **配色** | 24 套成体系的配色（单色渐变 / 多色对比 / 柔和期刊 / 色盲友好），图、Origin、导出图片统一 | 逐条手动设置 |
| **批量** | 一个样品调好的模型一键套用到全部样品（可固定峰宽和线形），自动生成堆叠对比图 | 通常逐个样品重复操作 |
| **元素覆盖** | 内置 Li–U 全部 90 种元素、169 个能级的峰位与自旋轨道分裂；任何元素都能“自动找峰”起步 | 视软件与版本而定 |
| **拟合可信度** | 内置诊断：参数是否顶到边界、参数强相关、**去掉每个组分后的 ΔBIC（这个组分数据到底支不支持）**、多起点稳定性 | 视软件与版本而定，通常需要用户自行判断 |
| **可追溯** | 原始数据只读保存；每个谱的模型和结果存为可读的 JSON；随时重算 | 依赖软件内部文件 |
| **AI 协作** | 内置 MCP 接口：用一句中文让 AI（Claude、Codex 等）完成导入、校准、拟合、诊断、导出；界面实时显示 AI 的每一步 | 无 |
| **语言** | 中文 / 英文一键切换 | 多为英文 |

**速度参考**（普通笔记本，实测）：Ir 4f 带不对称线形的三态分峰 0.5–4 秒；一个 5 谱区样品从预设开始全部拟合约 3 秒；15 个谱区一次导出成排好版的 Origin 工程约 13 秒。

**什么时候仍然要用 Avantage / CasaXPS / MultiPak？** 发表前的**交叉核对**（强烈建议，见[免责声明](#免责声明)）；需要厂商专属的透射函数与灵敏度因子库做严格定量时；深度剖析、成像、角分辨等 PeakForge 0.1 尚未覆盖的功能。

### 导出效果

PeakForge 直接生成的组合图（`figures/combined.png`）。示例为真实测量的 IrTaOx 电催化剂（样品名已匿名：A 反应前、B 反应后），Ir 4f 用“冰川”配色、O 1s 用“泻湖”配色；B 的 Ir⁰ 峰位与线形固定为 A 的拟合值，B 的 O 1s 含 Nafion 醚氧峰：

![组合图示例](docs/images/panel_example.png)

同一批拟合导出的 Origin 工程（`.opju`，每个谱区一张图，可在 Origin 中继续编辑）：

![Origin 导出](docs/images/origin_export.png)

---

## 功能一览

- **读取**：PHI MultiPak/SmartSoft `.spe`、VAMAS `.vms`（ISO 14976）、CSV/TXT、Excel；识别 `Fe2p3`、`Fe 2p3/2`、`Pt4f7` 等各种谱区写法。
- **荷电校准**：C 1s 的 C–C 自动定到 284.8 eV（可改），或手动输入。
- **背景**：Shirley、Smart、线性、Tougaard；端点可在图上拖动，自动避开邻峰拖尾。
- **线形**：高斯、洛伦兹、伪 Voigt、GL/SGL（CasaXPS 记法）、Voigt、Doniach–Šunjić（金属不对称峰）、LA 不对称线形。
- **约束**：每个参数可设上下限、固定，或联动（如“Ir³⁺ 的半峰宽 = Ir⁴⁺ 的半峰宽”）；自旋轨道双峰的间距与面积比自动带入。
- **全元素**：Li–U 共 90 种元素、169 个能级。没有预设的元素用“通用：自动找峰”——自动识别各化学态的主峰、去掉双峰的伴峰、按残差补肩峰；多重态复杂的能级（如 Ce 3d、Ni 2p）自动改用自由单峰。
- **预设库**：C 1s 污染碳、O 1s 氧化物、O 1s 氧化物 + Nafion、Ir 4f（氧化态按相对 Ir⁰ 的位移放置）、Ta 4f、Pt 4f、Au 4f；调好的模型可以存成自己的预设。
- **诊断、批量、定量**：见上表；定量的灵敏度因子可在表格里改成你仪器的值。
- **导出**：Origin `.opju`（本机有 Origin 时直接生成；没有时生成数据 + 一个脚本，在 Origin 里运行一行即可）、PNG/TIFF/SVG/PDF、Excel（含各组分参数、拟合质量、定量、曲线数据、软件信息与免责声明）。

---

## 上手

**完全不会编程？请看 [Quickstart（快速上手）](QUICKSTART.md)**：安装、只用鼠标的 10 步流程、以及把分析交给 AI 的做法，全程不需要命令行。

概括：
1. 安装 Python 3.12（勾选 *Add python.exe to PATH*）→ 下载本仓库 ZIP → 双击 `installer.py` → 桌面出现 PeakForge。
2. **鼠标路线**：新建工程 → 导入数据 → 自动荷电校准 → 选预设或“通用：自动找峰” → 拟合 → 拟合诊断 → 导出 Origin。
3. **AI 路线**：PeakForge 里点 **Agent → 一键连接 AI 到这个文件夹** → 在 Claude 桌面版 Code 标签打开该文件夹 → 用中文描述任务。

---

## 读懂结果

只需要基本的 XPS 理论知识就能看懂：

| 指标 | 含义 | 怎么看 |
|---|---|---|
| **残差 RMS (%)** | 拟合曲线与数据之差，占峰高的百分比 | < 2–3 % 通常良好；残差图上出现成片的鼓包，说明漏了组分或背景不对 |
| **χ²ᵣ** | 按计数噪声归一的残差（“≈”表示噪声由数据估计） | 接近 1 说明拟合误差与计数噪声相当；高计数谱 RMS 很小时也常 ≫ 1，见[方法说明](docs/METHODS.md#4-噪声模型加权与-χᵣfitpy) |
| **±1σ** | 参数的统计不确定度 | 不确定度和数值本身相当时，这个参数基本没被数据确定 |
| **顶到边界** | 参数停在你设定的上/下限 | 说明约束在“强行”决定结果，需要重新考虑范围或模型 |
| **强相关参数** | 两个参数此消彼长（\|r\| > 0.95） | 例如两个重叠峰的面积，单独报告其中一个要谨慎 |
| **ΔBIC（去掉组分）** | 去掉某个组分后模型变差多少 | > 10 强烈支持；2–10 有一定支持；< 2 数据不支持这个组分；“local minimum” 表示当前解不是最优，多起点重拟合 |
| **多起点稳定性** | 从不同初值拟合，占比的波动 | 波动大（> 3 %）说明结果依赖初值 |

**建议的习惯**：自旋轨道间距和面积比保持文献值；同一化学态在不同样品间用相同的半峰宽和线形（批量应用时固定）；报告价态占比时同时给出诊断结论；**发表前与常用软件交叉核对**。

---

## 配色

24 套配色以自然景观命名，分 6 个色族，每个色族 4 套；每套标注类型（单色渐变适合同一元素的价态系列，多色对比适合互不相关的组分，柔和期刊适合打印，色盲友好基于 Okabe–Ito）。也可以从任意一套出发调色，保存为自己的配色。

| 色族 | 配色 |
|---|---|
| 水域 Waters | 冰川 Glacier（默认）· 峡湾 Fjord · 泻湖 Lagoon · 深海 Abyss |
| 森林 Forests | 苔原 Moss · 松林 Pinewood · 竹林 Bamboo · 雨林 Rainforest |
| 大地 Earth | 沙漠 Desert · 峡谷 Canyon · 黄土 Loess · 恶地 Badlands |
| 天穹 Skies | 晨曦 Dawn · 暮色 Dusk · 极光 Aurora · 薄暮 Twilight |
| 山岩 Stone | 玄武 Basalt · 花岗 Granite · 板岩 Slate · 高地 Highland |
| 原野 Fields | 薰衣草田 Lavender · 草甸 Meadow · 秋野 Autumn · 草原 Prairie |

![24 套配色](docs/images/palettes.png)

---

## 常见问题

- **没有 Origin 能用吗？** 可以。导出时会生成 PNG/TIFF/SVG/PDF 和 Excel；Origin 部分会生成数据和脚本，以后在装了 Origin 的电脑上，打开 Origin → 窗口 → 脚本窗口，粘贴 `run -pyf "…/build_origin.py"`（导出文件夹里的说明文件里有完整路径）即可得到 `.opju`。
- **数据会上传吗？** 不会。PeakForge 完全在本机运行。只有你主动使用 AI 助手时，你发给 AI 的内容才会经过 AI 服务。
- **结果和 Avantage 不一样？** 背景端点、线形、约束、荷电参考的任何差异都会改变结果。先把这些设成一致再比较；仍有差异时以你能解释的物理模型为准。
- **CSV/Excel 的列没识别对？** 用“文件 → 按列映射导入表格…”：选能量列（结合能或动能）、强度列（cps 或 counts，可填每点采集时间）和谱区名，存成模板，以后同样格式的文件直接套用。
- **出错了怎么反馈？** “帮助 → 导出诊断包…”会生成一个 zip（日志、版本、工程与模型 JSON，**不含原始数据**），可附在 GitHub issue 里；“帮助 → 检查工程…”会列出模型或工程文件中的错误与警告。
- **灵敏度因子（RSF）对吗？** 内置值是 Scofield 截面的近似值，只适合粗略定量。请在“元素定量”表格里改成你仪器的 RSF。

---

## 给会编程的用户

```bash
pip install "git+https://github.com/Wiolic/PeakForge.git"
peakforge gui                                  # 图形界面
peakforge init D:/xps/proj --name IrTaOx       # 命令行
peakforge add D:/xps/proj data/*.spe
peakforge charge D:/xps/proj
peakforge fit D:/xps/proj --region "Ir 4f" --deep
peakforge export D:/xps/proj --formats png xlsx origin --theme fjord
peakforge add D:/xps/proj lab.csv --template mylab   # 用工程中保存的列映射模板
peakforge validate D:/xps/proj                 # 检查工程、模板、模型、预设
peakforge diag D:/xps/proj                     # 诊断包（不含原始数据）
peakforge formats                              # 支持的文件格式
peakforge mcp                                  # MCP 服务器（stdio）
```

工程文件夹：`<名称>.xpsproj`（样品、荷电位移、设置）· `data/raw/`（原始数据，只读）· `models/`（每个谱的模型与结果，JSON）· `presets/`（工程专用预设）· `output/`（全部导出，可随时删除重建）。

开发：`python -m pytest -q`（含 169 个能级的逐一拟合测试）；能级表由 `tools/build_orbitals.py` 生成。

---

## 免责声明

本软件仅用于科研辅助。分峰结果取决于背景、线形、约束与初值的选择，可能存在系统偏差。**发表或据此下结论之前，请与 CasaXPS、Thermo Avantage、PHI MultiPak 等常用 XPS 软件的分析结果进行比对**，并由使用者自行判断其合理性。作者不对使用本软件得到的任何结果承担责任。内置的峰位、自旋轨道分裂和灵敏度因子为近似的手册值，只用于给拟合提供初值。

Avantage、MultiPak、CasaXPS、Origin 是其各自所有者的商标；PeakForge 与它们没有关联。

## 许可

MIT License · **Developed by Eggy & Claude Opus 5.5**
