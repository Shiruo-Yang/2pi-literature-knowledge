#!/usr/bin/env python3
"""Build an automatic next-action queue for unresolved source-local identities."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from rdkit import Chem, rdBase


ROOT = Path(__file__).resolve().parents[2]

TRIAGE_COLUMNS = [
    "priority_rank", "priority_score", "entity_id", "paper_id", "doi",
    "source_label", "occurrence_count", "text_decision_status",
    "text_confidence_tier", "text_inchikey", "text_fragment_count",
    "candidate_rows", "candidate_channels", "single_fragment_rows",
    "multifragment_rows", "wildcard_rows", "rdkit_valid_rows",
    "exact_text_fragment_rows", "exact_text_fragment_channels",
    "distinct_complete_candidate_inchikeys", "recommended_next_action",
    "triage_class", "automatic_acceptance_eligible", "reason",
    "scientific_use_boundary",
]

EVIDENCE_COLUMNS = [
    "entity_id", "paper_id", "doi", "source_label", "candidate_channel",
    "structure_candidate_id", "page_number", "raw_recognized_smiles",
    "canonical_smiles", "inchikey", "fragment_count", "contains_wildcard",
    "rdkit_parse_ok", "recognition_confidence", "pairing_status",
    "expected_text_inchikey", "expected_fragment_match_count",
    "expected_matching_fragment_smiles", "other_fragment_smiles",
    "source_location", "molecule_crop_path", "rendered_page_path",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--identity-dir", type=Path, required=True)
    parser.add_argument(
        "--accepted-registry", type=Path,
        help="Accepted identity CSV. If omitted, use the highest numbered registry in identity-dir.",
    )
    parser.add_argument(
        "--terminal-registry", type=Path,
        help="Optional terminal classification CSV. Its entity IDs are excluded from the unresolved queue.",
    )
    parser.add_argument("--text-decisions", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--candidate-dir", action="append", default=[], metavar="NAME=PATH",
        help="Candidate registry directory; may be repeated.",
    )
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: Iterable[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_named_paths(values: list[str]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(value)
        name, raw_path = value.split("=", 1)
        path = Path(raw_path)
        if name in result or not path.is_dir():
            raise ValueError(value)
        result[name] = path
    return result


def resolve_accepted_registry(identity_dir: Path, explicit: Path | None) -> Path:
    if explicit:
        if not explicit.is_file():
            raise FileNotFoundError(explicit)
        return explicit
    candidates = list(identity_dir.glob("accepted_source_identity_registry_v*.csv"))
    if not candidates:
        raise FileNotFoundError("no accepted source identity registry")
    def version(path: Path) -> int:
        match = re.search(r"_v(\d+)\.csv$", path.name)
        return int(match.group(1)) if match else -1
    return max(candidates, key=version)


def fragment_matches(smiles: str, expected_key: str) -> tuple[list[str], list[str]]:
    if not smiles or not expected_key:
        return [], []
    molecule = Chem.MolFromSmiles(smiles)
    if molecule is None:
        return [], []
    matches: list[str] = []
    others: list[str] = []
    for fragment in Chem.GetMolFrags(molecule, asMols=True, sanitizeFrags=True):
        value = Chem.MolToSmiles(fragment, canonical=True, isomericSmiles=True)
        if "*" not in value and Chem.MolToInchiKey(fragment) == expected_key:
            matches.append(value)
        else:
            others.append(value)
    return matches, others


def truthy(value: str) -> bool:
    return str(value).strip().lower() in {"true", "yes", "1"}


def main() -> int:
    args = parse_args()
    candidate_dirs = parse_named_paths(args.candidate_dir)
    entities = read_csv(args.identity_dir / "source_local_entity_candidates_enriched.csv")
    accepted_registry = resolve_accepted_registry(args.identity_dir, args.accepted_registry)
    accepted = {
        row["entity_id"] for row in read_csv(accepted_registry)
    }
    terminal_rows = read_csv(args.terminal_registry) if args.terminal_registry else []
    terminal = {row.get("entity_id", "") for row in terminal_rows if row.get("entity_id", "")}
    unresolved = [
        row for row in entities
        if row.get("entity_id") not in accepted and row.get("entity_id") not in terminal
    ]
    text = {row["entity_id"]: row for row in read_csv(args.text_decisions)}
    by_entity: dict[str, list[dict[str, Any]]] = defaultdict(list)
    evidence_rows: list[dict[str, Any]] = []
    input_hashes: dict[str, str] = {
        "identity_entities": sha256(args.identity_dir / "source_local_entity_candidates_enriched.csv"),
        "accepted_identities": sha256(accepted_registry),
        "text_decisions": sha256(args.text_decisions),
    }
    if args.terminal_registry:
        input_hashes["terminal_registry"] = sha256(args.terminal_registry)
    for channel, directory in candidate_dirs.items():
        path = directory / "refined_structure_candidates.csv"
        if not path.is_file():
            continue
        input_hashes[f"candidate_{channel}"] = sha256(path)
        for row in read_csv(path):
            entity_id = row.get("entity_id", "")
            if entity_id in accepted:
                continue
            text_key = text.get(entity_id, {}).get("inchikey", "")
            smiles = row.get("canonical_smiles", "")
            matches, others = fragment_matches(smiles, text_key)
            enriched = dict(row)
            enriched["candidate_channel"] = channel
            enriched["expected_fragment_match_count"] = len(matches)
            by_entity[entity_id].append(enriched)
            evidence_rows.append(
                {
                    "entity_id": entity_id,
                    "paper_id": row.get("paper_id", ""),
                    "doi": row.get("doi", ""),
                    "source_label": row.get("source_label", ""),
                    "candidate_channel": channel,
                    "structure_candidate_id": row.get("structure_candidate_id", ""),
                    "page_number": row.get("page_number", ""),
                    "raw_recognized_smiles": row.get("raw_recognized_smiles", ""),
                    "canonical_smiles": smiles,
                    "inchikey": row.get("inchikey", ""),
                    "fragment_count": row.get("fragment_count", ""),
                    "contains_wildcard": row.get("contains_wildcard", ""),
                    "rdkit_parse_ok": row.get("rdkit_parse_ok", ""),
                    "recognition_confidence": row.get("recognition_confidence", ""),
                    "pairing_status": row.get("pairing_status", ""),
                    "expected_text_inchikey": text_key,
                    "expected_fragment_match_count": len(matches),
                    "expected_matching_fragment_smiles": ";".join(matches),
                    "other_fragment_smiles": ";".join(others),
                    "source_location": row.get("source_location", ""),
                    "molecule_crop_path": row.get("molecule_crop_path", ""),
                    "rendered_page_path": row.get("rendered_page_path", ""),
                }
            )

    triage: list[dict[str, Any]] = []
    for entity in unresolved:
        entity_id = entity["entity_id"]
        rows = by_entity.get(entity_id, [])
        text_row = text.get(entity_id, {})
        wildcard = [row for row in rows if truthy(row.get("contains_wildcard", "")) or "*" in row.get("canonical_smiles", "")]
        valid = [row for row in rows if truthy(row.get("rdkit_parse_ok", ""))]
        multifragment = [row for row in rows if int(row.get("fragment_count", "0") or 0) > 1]
        single = [row for row in rows if int(row.get("fragment_count", "0") or 0) == 1]
        exact = [row for row in rows if int(row.get("expected_fragment_match_count", 0)) == 1]
        exact_channels = sorted({row["candidate_channel"] for row in exact})
        complete_keys = sorted({
            row.get("inchikey", "") for row in single
            if row.get("inchikey", "") and row not in wildcard
        })
        text_fragments = int(text_row.get("fragment_count", "0") or 0)
        occurrence_count = int(entity.get("occurrence_count", "0") or 0)

        if len(exact_channels) >= 2:
            action = "label_guided_component_recovery"
            triage_class = "adjacent_structure_recoverable"
            eligible = "candidate_after_three_scale_reidentification"
            reason = "independent text identity occurs exactly once inside repeated multifragment panel crops"
            score = 500 + 20 * len(exact_channels) + min(occurrence_count, 50)
        elif text_fragments > 1 or text_row.get("decision_status") == "provisional_external_match_multicomponent":
            action = "build_explicit_salt_or_multicomponent_representation"
            triage_class = "salt_or_multicomponent"
            eligible = "no"
            reason = "text identity is explicitly multicomponent and must not be coerced into one molecular graph"
            score = 400 + min(occurrence_count, 50)
        elif wildcard:
            action = "recover_source_defined_repeat_unit_or_complete_substituent"
            triage_class = "wildcard_or_polymer_structure"
            eligible = "no"
            reason = "candidate contains an attachment point or incomplete substituent"
            score = 300 + min(occurrence_count, 50)
        elif len(complete_keys) > 1:
            action = "resolve_competing_complete_panel_structures"
            triage_class = "competing_structures"
            eligible = "no"
            reason = "more than one complete molecular topology is associated with the source label"
            score = 250 + 10 * len(complete_keys) + min(occurrence_count, 50)
        elif len(complete_keys) == 1 and text_row.get("inchikey"):
            action = "run_three_scale_single_structure_concordance"
            triage_class = "single_structure_needs_concordance"
            eligible = "candidate_after_three_scale_and_text_agreement"
            reason = "one complete topology and a text anchor exist but the strict multiscale gate is incomplete"
            score = 220 + min(occurrence_count, 50)
        elif rows:
            action = "improve_panel_pairing_or_source_definition"
            triage_class = "structure_candidate_not_uniquely_linked"
            eligible = "no"
            reason = "structure candidates exist but no unique complete identity can be linked"
            score = 150 + min(occurrence_count, 50)
        else:
            action = "acquire_fulltext_structure_panel_or_explicit_name"
            triage_class = "no_structure_candidate"
            eligible = "no"
            reason = "no source-panel molecular structure candidate is currently registered"
            score = 100 + min(occurrence_count, 50)

        triage.append(
            {
                "priority_score": score,
                "entity_id": entity_id,
                "paper_id": entity.get("paper_id", ""),
                "doi": entity.get("doi", ""),
                "source_label": entity.get("raw_label", ""),
                "occurrence_count": occurrence_count,
                "text_decision_status": text_row.get("decision_status", ""),
                "text_confidence_tier": text_row.get("confidence_tier", ""),
                "text_inchikey": text_row.get("inchikey", ""),
                "text_fragment_count": text_fragments,
                "candidate_rows": len(rows),
                "candidate_channels": ";".join(sorted({row["candidate_channel"] for row in rows})),
                "single_fragment_rows": len(single),
                "multifragment_rows": len(multifragment),
                "wildcard_rows": len(wildcard),
                "rdkit_valid_rows": len(valid),
                "exact_text_fragment_rows": len(exact),
                "exact_text_fragment_channels": ";".join(exact_channels),
                "distinct_complete_candidate_inchikeys": len(complete_keys),
                "recommended_next_action": action,
                "triage_class": triage_class,
                "automatic_acceptance_eligible": eligible,
                "reason": reason,
                "scientific_use_boundary": (
                    "Identity triage only; not numerical evidence, a model label, an external-validation "
                    "observation, a screening decision, or a COMSOL input."
                ),
            }
        )

    triage.sort(key=lambda row: (-int(row["priority_score"]), row["paper_id"], row["entity_id"]))
    for rank, row in enumerate(triage, start=1):
        row["priority_rank"] = rank
    evidence_rows.sort(key=lambda row: (row["entity_id"], row["candidate_channel"], row["page_number"]))
    write_csv(args.output_dir / "unresolved_identity_triage.csv", triage, TRIAGE_COLUMNS)
    write_csv(args.output_dir / "unresolved_candidate_evidence.csv", evidence_rows, EVIDENCE_COLUMNS)

    class_counts = dict(Counter(row["triage_class"] for row in triage))
    action_counts = dict(Counter(row["recommended_next_action"] for row in triage))
    validation = {
        "generated_at_utc": utc_now(),
        "valid": len(triage) == len(unresolved) and not ({row["entity_id"] for row in triage} & accepted),
        "errors": [],
        "counts": {
            "unresolved_input_entities": len(unresolved),
            "triaged_entities": len(triage),
            "candidate_evidence_rows": len(evidence_rows),
            "accepted_entities_excluded": len(accepted),
            "terminal_entities_excluded": len(terminal),
        },
    }
    if not validation["valid"]:
        validation["errors"].append("unresolved_entity_coverage_or_accepted_exclusion_failed")
    summary = {
        "generated_at_utc": utc_now(),
        "workflow": "current_unresolved_source_identity_automatic_triage",
        "triage_class_counts": class_counts,
        "recommended_action_counts": action_counts,
        "automatically_recoverable_component_entities": sum(
            row["triage_class"] == "adjacent_structure_recoverable" for row in triage
        ),
        "input_hashes": input_hashes,
        "rdkit_version": rdBase.rdkitVersion,
        "scientific_boundary": (
            "This queue prioritizes identity evidence only and cannot promote experimental values "
            "or downstream scientific-use records."
        ),
        "validation": validation,
    }
    (args.output_dir / "run_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (args.output_dir / "VALIDATION_REPORT.json").write_text(
        json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if validation["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
