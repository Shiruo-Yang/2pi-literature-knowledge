# Panel 1：同一篇真实文献的三层计算化使用

日期：2026-08-22  
用途：主图 Panel 1 的真实来源卡与结构化提取底稿

## 1. 选定真实来源

**Malval et al.** “Enhancement of the Two-Photon Initiating Efficiency of a Thioxanthone Derivative through a Chevron-Shaped Architecture.” *Chemistry of Materials* **2011**, 23, 3411–3420. DOI: [10.1021/cm200595y](https://doi.org/10.1021/cm200595y).

本项目已有本地原文抽取文件：`outputs/chi2019_thioxanthone_pdf_text.txt`。ACS 页面核对了题名、作者、期刊、页码、年份和 DOI；原文抽取用于页码/章节定位。

**为什么选它：** 这篇论文同时提供了可追溯的分子身份（ANTX，anthracene–thioxanthone chevron architecture）、2PA 光学证据、配方/共引发剂语境、自由基生成路径、聚合应用和结构—光物理—反应性关系。它适合作为“同一来源被分三层使用”的示例，但论文原文没有提出本项目的六任务权重或 PI 描述符；这两项属于我们的结构化计算映射。

## 2. 原文证据与结构化映射

| 颜色 | 图中功能 | 原文证据（页/章节） | 结构化提取 | 在本项目中的真实计算用途 | 证据边界 |
|---|---|---|---|---|---|
| **绿色** | task-prior / 权重输入 | Abstract；Introduction p. 3411–3412；Results “Two-Photon Initiating Properties” | 论文同时评价 2PA、自由基光引发效率、聚合阈值/转化和 3D 微结构加工，而不是只报告一个光谱峰；因此被编码为 optical response + radical initiation + application/formulation 的联合证据 | 作为 Layer 1 的领域先验输入，支持六任务中光学、光化学/ISC 代理、配方/应用相关任务的保留与相对重要性讨论；实际六任务权重来自项目的文献先验规则和权重实验，不声称由本论文单独给出 | **不是**本文直接给出六任务权重；是“原文评价维度 → 项目先验权重构建”的证据输入 |
| **紫色** | descriptor / 分子表示构建 | Abstract；Scheme 1；Introduction p. 3412；Results p. 3414–3417 | ANTX 是 anthracene–thioxanthone hybrid，采用 chevron-shaped architecture；文中讨论 conjugation、thioxanthone fragment、nπ*/ππ* character、dipole/transition features 和 radical-anion localisation | 生成可追溯的 PI-family/topology 结构化对象：`family=thioxanthone`；`hybrid=anthracene_thioxanthone`；`architecture=chevron`；`conjugation=extended_but_non-linear`；`initiating_motif=thioxanthone_carbonyl`；可映射到 F06 的 family/topology descriptors 与 D06/F06 分歧诊断 | 这些是从原文结构/光物理事实建立的**项目描述符映射**；原文没有使用 Chemprop、F06 或本项目 descriptor 名称 |
| **黄色** | mechanism / molecular profile | Introduction p. 3411；Results “Free Radical Photoinitiating Ability of ANTX” p. 3415；Fig. 5–7 discussion | 论文明确将 thioxanthone 作为 hydrogen abstractor，并使用 MDEA 作为 hydrogen-donor/co-initiator；H-transfer 产生 α-aminoalkyl radicals，随后加成 acrylate；同时比较 TX、ANTH 和 ANTX 的转化表现 | 机制决策层：`family=thioxanthone` → Type-II lane；要求保留 coinitiator/H-donor context；候选画像记录 `role=photoinitiator`、`coinitiator=MDEA`、`resin=acrylate formulation`、`mechanism=H-abstraction/Type-II`；后续 QM 问题对应 triplet/reactivity、H-transfer 或 donor-context assessment | 该映射支持 mechanism-specific routing，不等同于对项目 ZINC22 候选的实验机制证明 |

## 3. 原文短引（用于图中小字；总引文长度控制）

以下为从 ACS 原文抽取的短语，建议只在图中作为证据标签，不要放成长段引文：

1. “a new hybrid anthracene–thioxanthone (ANTX) system” （Abstract）
2. “two-photon polymerization threshold of ANTX is five times lower” （Abstract）
3. “MDEA … is used as hydrogen donor reactant” （Results, p. 3415）

图中其余内容用释义，不直接复制原文段落：论文报告 ANTX 的 2PA 增强、MDEA 参与的氢转移自由基生成，以及在丙烯酸酯配方中的聚合表现。

## 3A. Panel 中使用的最终压缩表述

图中三个证据框不放整段原文，只放以下结构化摘要。每个框底部用小字号标注 `Malval et al., Chem. Mater. 2011, DOI: 10.1021/cm200595y`；页码和原文锚点保留在本文件及 `local_source_evidence_registry.csv`。

### Molecular identity

**ANTX**  
anthracene–thioxanthone  
chevron-shaped architecture

来源定位：Abstract；Scheme 1；Introduction p. 3412。

### Property / application evidence

enhanced two-photon response  
reduced polymerisation threshold  
3D microfabrication demonstrated

来源定位：Abstract；Results, “Two-Photon Initiating Properties”; Fig. 7。

### Experimental / mechanistic context

MDEA as hydrogen donor  
H-transfer pathway  
Type-II photoinitiation context

来源定位：Introduction p. 3411；Results, “Free Radical Photoinitiating Ability of ANTX”, pp. 3415–3416。

### 三个框与三层的连接

- **Molecular identity → Layer 2:** family/topology descriptor construction。
- **Property / application evidence → Layer 1:** literature-prior task selection and weighting input。
- **Experimental / mechanistic context → Layer 3:** Type-II admission, coinitiator context and QM-question routing。

这里的三类摘要是本项目对原文的标准化表达，不是论文原句；原始文本证据、页码和 DOI 由 registry 追溯。

## 4. 可直接放入 panel 的三条箭头文字

### 绿色：原文 → task prior

`2PA response + radical initiation + polymerisation/application evidence`  
→ `literature-derived task-prior input`  
→ `six-task weighting and endpoint retention`

### 紫色：原文 → descriptor object

`anthracene–thioxanthone / chevron / extended conjugation / thioxanthone carbonyl`  
→ `family and topology representation`  
→ `PI-family descriptors and D06–F06 diagnostic comparison`

### 黄色：原文 → mechanism profile

`thioxanthone + MDEA H-donor + H-transfer to α-aminoalkyl radical`  
→ `Type-II, coinitiator-dependent molecular profile`  
→ `lane-specific admission and QM question`

## 5. 图中必须保留的“证据边界”标签

建议在三条箭头末端加小字：

> **Original paper:** reports molecular, photophysical, formulation and mechanistic evidence.  
> **Structured computational use:** converts these evidence units into task priors, family/topology descriptors and mechanism-routing rules.  
> **Not claimed:** the paper did not define our six-task weight vector or our Chemprop descriptor set.

中文图注可写：

> 原文提供领域证据；任务权重、描述符和机制分流是本研究对该证据的可追溯计算化使用，而非原文直接提出的模型组件。

## 6. 与本项目资产的对应关系

| 结构化对象 | 项目资产 | 对应方式 |
|---|---|---|
| thioxanthone family / donor context | `literature_knowledge/domain_knowledge_registry.csv`；`mechanism_decision_registry.csv` | 作为 Type-II family/admissibility 证据；不是单一高 sigma 值的充分条件 |
| anthracene–thioxanthone chevron architecture | `endpoint_representation_registry.csv` 中 PI-family/topology 表示 | 作为 F06 family-sensitive 输入的来源链示例 |
| 2PA + initiation + formulation evidence | 六任务 prior/weight registry 与权重敏感性实验资产 | 支持任务保留和先验权重构建；实际向量必须引用最终 weight 配置文件 |
| MDEA H-transfer / α-aminoalkyl radical | Type-II candidate routing 和 lane-specific QM manifest | 支持 coinitiator/H-donor 条件与后续物理化学问题定义 |

## 7. 不应在图中写的表述

- “The paper assigned the six task weights.”（错误）
- “The paper generated our PI descriptors.”（错误）
- “The paper proved the mechanism of every selected candidate.”（错误）
- “ANTX is a validated lead from our ZINC22 screen.”（错误）

应改为：

- “One source, three computational roles.”
- “Source-linked task-prior input.”
- “Source-derived family/topology representation.”
- “Mechanism-context routing to Type-II assessment.”

## 8. 建议图题

**Panel 1 | One source, three computational roles.** A real primary study of an anthracene–thioxanthone photoinitiator is decomposed into source-linked evidence units. Green: the paper’s joint evaluation of optical response, radical initiation and polymerisation informs the project’s literature-prior task weighting. Purple: the reported hybrid architecture and thioxanthone motif are formalised as family/topology representation features. Yellow: the MDEA-assisted hydrogen-transfer pathway is encoded as a Type-II, coinitiator-dependent molecular profile and routed to a mechanism-matched physicochemical question. The coloured mappings are computational uses in this study, not claims that the source paper defined the present model or proved the mechanism of every screened candidate.
