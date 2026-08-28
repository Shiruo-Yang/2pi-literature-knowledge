#!/usr/bin/env python3
"""Create a conservative, page-anchored pre-audit for Pucher et al. 2009."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/literature_fulltext_review_20260828_v1/pucher_2009_targeted_audit"

FIELDS = [
    "audit_id", "review_id", "source_id", "doi", "pi_label", "value_type",
    "raw_value", "raw_unit", "normalized_value", "normalized_unit", "context_lock",
    "page_hint", "figure_or_table", "evidence_anchor", "evidence_class",
    "audit_status", "allowed_use", "limitation",
]


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def row(audit_id: str, pi: str, value_type: str, raw: str, raw_unit: str, norm: str,
        norm_unit: str, context: str, page: str, fig: str, anchor: str,
        evidence_class: str, allowed: str, limitation: str) -> dict[str, str]:
    return {
        "audit_id": audit_id,
        "review_id": "LFR-3158e70b3e31efdc",
        "source_id": "ZPC-000028",
        "doi": "10.1021/ma9007785",
        "pi_label": pi,
        "value_type": value_type,
        "raw_value": raw,
        "raw_unit": raw_unit,
        "normalized_value": norm,
        "normalized_unit": norm_unit,
        "context_lock": context,
        "page_hint": page,
        "figure_or_table": fig,
        "evidence_anchor": anchor,
        "evidence_class": evidence_class,
        "audit_status": "assistant_pre_audit_pending_user_confirmation",
        "allowed_use": allowed,
        "limitation": limitation,
    }


def main() -> None:
    rows: list[dict[str, str]] = []
    sigma_context = "open-aperture z-scan; 800 nm; PI solution 1.0e-2 M in THF; Table 1"
    sigma_anchor = "Table 1 reports TPA cross sections measured at 800 nm in THF; the text states all calculated sigma values are given in Table 1."
    sigma_values = [
        ("O3K", "<10", "GM", "<10", "page 6 Table 1; table footnote c defines 1 GM"),
        ("M3K", "165", "GM", "165", "page 6 Table 1"),
        ("B3K", "238", "GM", "238", "page 6 Table 1"),
        ("P3K", "256", "GM", "256", "page 6 Table 1; page 6 text calls P3K the highest amino-based derivative"),
        ("M2K", "261", "GM", "261", "page 6 Table 1; footnote e warns the broad signal may cause error"),
        ("M3P", "23", "GM", "23", "page 6 Table 1"),
        ("R1", "318", "GM", "318", "page 6 Table 1; literature reference PI"),
        ("R2", "314", "GM", "314", "page 6 Table 1; literature reference PI"),
    ]
    for index, (pi, raw, unit, norm, detail) in enumerate(sigma_values, start=1):
        rows.append(row(
            f"PAUD-{index:03d}", pi, "sigma2", raw, unit, norm, unit, sigma_context,
            "6", "Table 1", sigma_anchor + " " + detail, "text_exact_table_candidate",
            "photophysical comparison within the reported 800 nm THF measurement context",
            "Must retain the 800 nm/THF/z-scan context; do not treat sigma2 alone as initiation efficiency.",
        ))
    rows.extend([
        row("PAUD-009", "H3K", "sigma2", "no signal detected", "qualitative", "", "", sigma_context,
            "6", "Table 1 and surrounding text", "The text states no signal could be detected for H3K at the given wavelength.",
            "text_exact_qualitative", "qualitative boundary/context only", "No numeric sigma2 value should be imputed."),
        row("PAUD-010", "M3P+", "sigma2", "no reliable numeric value", "qualitative", "", "", sigma_context,
            "6", "Table 1 and surrounding text", "The text says poor solubility allowed only very low concentrations with poor signal-to-noise and only an assumption of a higher value than M3P.",
            "text_exact_qualitative", "qualitative boundary/context only", "Do not convert the authors' assumption into a numeric value."),
        row("PAUD-011", "all PIs", "PI_loading", "6.3e-6", "mol PI/g resin", "6.3e-6", "mol PI/g resin",
            "ETA/TTA 1:1; same molar PI concentration for direct activity comparison",
            "7", "TPIP Structuring Tests", "For all studies the same molar PI concentration of 6.3e-6 mol PI/g resin was employed; this corresponds to 0.2 wt% of M3K.",
            "text_exact_context", "matched-series activity comparison only", "0.2 wt% is explicitly tied to M3K; it is not a universal wt% for every PI."),
        row("PAUD-012", "all PIs", "PI_loading", "1.6e-6; 1.6e-7", "mol PI/g resin", "1.6e-6; 1.6e-7", "mol PI/g resin",
            "ETA/TTA 1:1; lower-concentration repeat tests",
            "7", "TPIP Structuring Tests", "The tests were repeated with lower molar PI concentrations of 1.6e-6 and 1.6e-7 mol PI/g resin, corresponding to 0.05 and 0.005 wt% of M3K.",
            "text_exact_context", "concentration-response context only", "The corresponding wt% values are again stated for M3K, not all molecular weights."),
        row("PAUD-013", "B3K", "processing_window_lower_bound", "5", "uW", "5", "uW",
            "ETA/TTA 1:1; 6.3e-6 mol PI/g resin; system A TPIP screening",
            "8", "conclusion/TPIP discussion", "B3K is described as having the broadest ideal structuring process window at laser intensities as low as 5 uW.",
            "text_exact_operating_window", "context_only; not a polymerization threshold", "This is the lower end of an ideal processing window, not necessarily the lowest power that polymerizes."),
        row("PAUD-014", "B3K", "complex_structure_power", "11", "uW", "11", "uW",
            "ETA/TTA 1:1; 6.3e-6 mol PI/g resin; system A; feed rate 1 mm/min",
            "8", "Figure 7", "A laser power of 11 uW at a feed rate of 1 mm/min allowed structuring of dragonfly and dinosaur sculptures.",
            "text_exact_application_context", "application demonstration only", "Not a universal threshold and not a matched per-PI threshold."),
        row("PAUD-015", "B3K", "line_width", "250", "nm", "250", "nm",
            "ETA/TTA 1:1; system B 780 nm, ~150 fs, 100 MHz, NA 1.4; feed rate 10-25 um/s",
            "8-9", "Figure 7", "The paper reports line widths of about 250 nm for the system B woodpile structures.",
            "text_exact_application_context", "voxel/linewidth validation context only", "Must not be mixed with system A data or treated as a molecular property."),
        row("PAUD-016", "all PIs", "laser_context", "800; ~130; 1", "nm; fs; kHz", "800; ~130; 1", "nm; fs; kHz",
            "system A; 100x objective; NA 0.95",
            "4", "Laser Device", "System A operates at 1 kHz, 800 nm and ~130 fs; the beam is focused with a 100x objective of NA 0.95.",
            "text_exact_context", "protocol lock for system A", "Power plane and scan protocol remain necessary for any threshold use."),
        row("PAUD-017", "all PIs", "laser_context", "780; ~150; 100", "nm; fs; MHz", "780; ~150; 100", "nm; fs; MHz",
            "system B; 100x oil objective; NA 1.4; power measured before objective",
            "4", "Laser Device", "System B provides 780 nm, ~150 fs pulses at 100 MHz, uses a 100x oil immersion objective with NA 1.4, and reports power before the objective.",
            "text_exact_context", "protocol lock for system B", "System B cannot be pooled with system A without preserving protocol identity."),
        row("PAUD-018", "B3K/P3K/M3K family", "synthesis_route", "83-97", "% yield", "83-97", "% yield",
            "new amine-donor-containing derivatives; key terminal aryl alkynes; Scheme 1/2",
            "5", "Schemes 1-2", "The paper describes Sonogashira/deprotection and Wittig-type one-pot routes to terminal aryl alkyne precursors, and reports final B3K/P3K products in high yields of 83-97%.",
            "text_exact_route_precedent", "family-level synthesis precedent", "A route precedent does not prove that an unseen candidate is synthesizable without its own substrate and purification check."),
        row("PAUD-019", "ketone-based PIs", "mechanism_prior", "efficient ISC and triplet-state H abstraction", "qualitative", "", "",
            "photophysical discussion in solution; not a molecule-specific direct mechanistic measurement for every PI",
            "6", "mechanism discussion", "Low emission is rationalized by efficient intersystem crossing to a triplet state, followed by hydrogen abstraction from the solvent.",
            "mechanistic_interpretation", "family-level mechanism context only", "The paper itself says different initiation mechanisms may be responsible; do not generalize to every candidate."),
    ])
    write_csv(OUT / "pucher_evidence_audit.csv", rows, FIELDS)
    summary = {
        "source_id": "ZPC-000028",
        "review_id": "LFR-3158e70b3e31efdc",
        "doi": "10.1021/ma9007785",
        "numeric_sigma2_rows": 8,
        "qualitative_sigma2_boundary_rows": 2,
        "context_rows": 7,
        "route_rows": 1,
        "final_relative_core_status": "candidate_needs_pi_alignment_and_user_confirmation",
        "final_comsol_status": "not_ready",
        "threshold_status": "no_text_exact_polymerization_threshold_accepted; 5 uW retained as operating-window context_only",
        "promotion_status": "hold_unverified",
    }
    (OUT / "pucher_source_decision.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Pucher 2009 定向来源审计",
        "",
        "本报告是基于本地全文的结构化预审，不替代最终人工签核。所有记录仍保留 pending 状态。",
        "",
        "## 审计结论",
        "",
        "- 表 1 明确给出了 800 nm、THF、开放光阑 Z 扫描条件下的多组双光子吸收截面候选值，其中 8 个为数值记录，H3K 和 M3P+ 只保留定性边界。",
        "- 全部光引发剂在 TPIP 活性比较中使用相同摩尔浓度和 ETA/TTA 1:1 树脂，但明确写出的 wt% 是以 M3K 为基准，不能直接当成所有分子的统一质量百分比。",
        "- 5 uW 是 B3K 的理想加工窗口下限描述，不应直接改写成聚合阈值；11 uW 是复杂结构示范功率，也不是普适阈值。",
        "- B3K/P3K 的 83–97% 收率可作为家族级合成路线先例，但不能证明未见候选一定可按同一路线合成。",
        "- 当前不能升级为最终相对核心记录，因为还需要把每个光引发剂、双光子截面、具体配方和对应活性结果逐一对齐，并由人工确认表格与图示。",
        "",
        "## 允许的暂时用途",
        "",
        "- 双光子吸收截面：可作为 800 nm/THF/z-scan 条件锁定下的候选光学观测。",
        "- 共同摩尔浓度和 ETA/TTA 1:1：可作为系列内比较的上下文锁。",
        "- B3K/P3K 路线：可作为合成家族先例。",
        "- 5 uW、11 uW、250 nm：只能作为加工条件或应用示范，不作为分子固有性质或普适阈值。",
        "",
        "## 下一个人工核验动作",
        "",
        "1. 对照原始表 1，确认每个 PI 标签与 sigma2 数值的列位置。",
        "2. 对照图 5，记录每个 PI 在相同摩尔浓度下的理想加工窗口，而不是只保留 B3K。",
        "3. 明确区分 800 nm 系统 A、600 nm 调谐测试和 780 nm 系统 B。",
        "4. 确认是否存在可以从图 5 读取的真正聚合阈值；若只能读取加工质量等级，则保留为 context_only。",
        "",
    ]
    (OUT / "pucher_targeted_audit.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
