# 全自动文献字段证据注册表

本目录只做一件事：把解析后的文献字段证据和数值候选自动整理成原有研究可以继续使用的 JSONL/CSV 文件。流程不设置人工复核步骤。

本次生成 1008 条字段证据记录，其中 694 条来自全文字段锚点，314 条来自数值候选抽取；补充数值 CSV 共 314 条。

## 主要文件

- `literature_field_evidence_registry.jsonl`：逐条字段证据的机器交换格式，每行一条记录。
- `literature_field_evidence_registry.csv`：同一注册表的表格格式。
- `supplementary_literature_field_evidence.csv`：可作为补充材料的完整字段证据表。
- `supplementary_numeric_evidence.csv`：可作为补充材料的数值和实验条件表。
- `literature_field_coverage.csv`：按文献汇总字段覆盖情况。
- `automatic_field_evidence_summary.json`：记录数量、字段分布、输入校验和。

## 字段范围

包括双光子吸收截面、光引发剂用量、聚合阈值候选、实验条件、体素/线宽信息、三重态/系间窜越线索和光引发机理线索。缺失数值保持为空，不用程序补写。

## 说明

这是自动采集层，不是人工核验层。它可以直接扩充原有文献数据库和生成补充 CSV；后续模型或统计程序应同时读取 `automatic_status`、`confidence_class` 和 `automatic_reason`。
