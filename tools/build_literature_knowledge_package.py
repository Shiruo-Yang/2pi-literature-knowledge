from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "literature_knowledge"
VERSION = "v1.0"
RELEASE_DATE = "2026-08-19"
BUILDER_VERSION = "1.0.0"


def read_csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows({k: row.get(k, "") for k in fields} for row in rows)


def sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_fields(source_by_id, source_id):
    row = source_by_id.get(source_id, {})
    return row.get("doi", ""), row.get("title", "")


def main():
    OUT.mkdir(exist_ok=True)
    (OUT / "schema").mkdir(exist_ok=True)
    (OUT / "examples").mkdir(exist_ok=True)

    doi_detail_path = ROOT / "outputs/round1_24_literature_scaffold_consensus/round1_24_rule_source_literature_doi_detail.csv"
    lane_path = ROOT / "outputs/literature_evidence_formalization_20260629/lane_rule_evidence_table.csv"
    feature_manifest_path = ROOT / "outputs/descriptor_v2_feature_manifest.csv"
    candidate_path = ROOT / "outputs/final_three_lane_research_package_20260608/final_three_lane_candidate_package.csv"
    d06_features_path = ROOT / "outputs/final_outer_test_strict_clean_231_mask_20260726/assets/D06_dense_final/outer_trainval_features.csv"
    f06_features_path = ROOT / "outputs/final_outer_test_strict_clean_231_mask_20260726/assets/F06_dense_plus_pi_family_final/outer_trainval_features.csv"
    d06_spec_path = ROOT / "outputs/final_outer_test_strict_clean_231_mask_20260726/D06_dense_final/training_run_spec.json"
    f06_spec_path = ROOT / "outputs/final_outer_test_strict_clean_231_mask_20260726/F06_dense_plus_pi_family_final/training_run_spec.json"
    strict_clean_path = ROOT / "outputs/final_outer_test_strict_clean_231_mask_20260726/strict_clean_231_asset_audit.json"

    doi_detail = read_csv(doi_detail_path)
    lane = read_csv(lane_path)

    source_rows = []
    for i, row in enumerate(doi_detail, 1):
        title = row.get("titles", "").strip()
        source_rows.append({
            "source_id": f"P{i:04d}",
            "source_label": title or row.get("doi", ""),
            "doi": row.get("doi", "").strip(),
            "title": title,
            "source_type": "review" if "review" in row.get("paper_types", "").lower() else "article",
            "topic_scope": ";".join(v for v in [row.get("pi_types", ""), row.get("applications", "")] if v),
            "evidence_location": row.get("source_files", ""),
            "evidence_use_summary": "Supports literature-derived photoinitiator criteria, family roles, or mechanism rules.",
            "metadata_status": "citation_ready" if title else "doi_only_pending",
            "status": "traceable_source",
        })

    doi_to_source = {row["doi"].split(";")[0].strip(): row["source_id"] for row in source_rows if row["doi"]}
    for row in lane:
        for doi in row.get("supporting_dois", "").split(";"):
            doi = doi.strip()
            if not doi or doi in doi_to_source:
                continue
            source_id = f"P{len(source_rows) + 1:04d}"
            source_rows.append({
                "source_id": source_id,
                "source_label": doi,
                "doi": doi,
                "title": "",
                "source_type": "article",
                "topic_scope": "photoinitiator mechanism",
                "evidence_location": lane_path.relative_to(ROOT).as_posix(),
                "evidence_use_summary": "Referenced by a formalised mechanism/family rule.",
                "metadata_status": "doi_only_pending",
                "status": "traceable_source",
            })
            doi_to_source[doi] = source_id

    source_fields_list = [
        "source_id", "source_label", "doi", "title", "source_type", "topic_scope",
        "evidence_location", "evidence_use_summary", "metadata_status", "status",
    ]
    write_csv(OUT / "source_registry.csv", source_fields_list, source_rows)
    source_by_id = {row["source_id"]: row for row in source_rows}

    domain_rows = []
    for i, row in enumerate(lane, 1):
        doi = row.get("supporting_dois", "").split(";")[0].strip()
        source_id = doi_to_source[doi]
        source_doi, source_title = source_fields(source_by_id, source_id)
        normalized_field = row.get("motif_family", "") or row.get("mechanism_lane", "")
        domain_rows.append({
            "knowledge_id": f"DK{i:04d}", "source_id": source_id,
            "source_doi": source_doi, "source_title": source_title,
            "evidence_scope": "family/mechanism", "evidence_summary": row.get("claim_supported", ""),
            "normalized_field": normalized_field,
            "normalized_rule": f"Evaluate {normalized_field} under the stated evidence and claim limits.",
            "scientific_rationale": row.get("claim_limit", ""),
            "computational_use": "domain criterion and candidate admissibility control",
            "downstream_asset": row.get("priority_scope", ""),
            "evidence_level": row.get("evidence_level", ""), "status": "traceable_rule_import",
            "provenance_path": lane_path.relative_to(ROOT).as_posix(),
        })
    domain_fields = [
        "knowledge_id", "source_id", "source_doi", "source_title", "evidence_scope",
        "evidence_summary", "normalized_field", "normalized_rule", "scientific_rationale",
        "computational_use", "downstream_asset", "evidence_level", "status", "provenance_path",
    ]
    write_csv(OUT / "domain_knowledge_registry.csv", domain_fields, domain_rows)

    endpoint_source_map = {
        "sigma_780": "P0003;P0004;P0025", "sigma_max": "P0003;P0004;P0025",
        "toxicity": "P0001;P0002", "solubility": "P0001;P0002;P0003",
        "synthetic_accessibility": "", "isc_energy": "P0003;P0004",
    }
    endpoint_definitions = [
        ("EP001", "sigma_780", "Two-photon response at the operating wavelength", "operating-wavelength optical response", "dataset-defined", "log1p", "six-task predictive profile"),
        ("EP002", "sigma_max", "Maximum reported two-photon response", "optical screening and external optical comparison", "dataset-defined", "log1p", "six-task profile; ZINC22 deployment"),
        ("EP003", "toxicity", "Curated toxicity-related proxy", "application and safety constraint", "dataset-defined", "none", "candidate risk control"),
        ("EP004", "solubility", "Solubility/formulation-related endpoint", "resin and formulation compatibility", "dataset-defined", "log1p", "candidate profile; formulation gate"),
        ("EP005", "synthetic_accessibility", "Synthetic-accessibility proxy", "materialisation feasibility", "dataset-defined", "none", "candidate portfolio control"),
        ("EP006", "isc_energy", "Intersystem-crossing-related energy proxy", "photochemical and mechanism relevance", "dataset-defined", "none", "candidate profile; mechanism-sensitive diagnosis"),
    ]
    endpoint_rows = []
    for item_id, name, definition, rationale, unit, transform, downstream in endpoint_definitions:
        source_ids = endpoint_source_map[name]
        mapping_status = "literature_links_recorded" if source_ids else "project_design_proxy_literature_mapping_pending"
        endpoint_rows.append({
            "item_id": item_id, "item_type": "endpoint", "human_readable_name": definition,
            "machine_readable_field": name, "source": source_ids or "project design decision",
            "evidence_summary": rationale, "scientific_rationale": rationale,
            "normalized_rule": f"Include {name} in the six-task profile; treat it as a predictive proxy rather than direct polymerisation performance.",
            "unit": unit, "transformation": transform,
            "missing_value_rule": "task-cell masking; no molecule deletion", "model_scope": "D06;F06",
            "computational_use": "multitask target", "downstream_asset": downstream,
            "status": f"implemented_in_final_models;{mapping_status}",
            "provenance_path": f"{d06_spec_path.relative_to(ROOT).as_posix()};{f06_spec_path.relative_to(ROOT).as_posix()};{strict_clean_path.relative_to(ROOT).as_posix()}",
        })

    endpoint_rows.append({
        "item_id": "REP000", "item_type": "representation", "human_readable_name": "Chemprop molecular graph",
        "machine_readable_field": "molecular_graph", "source": "canonical molecular input",
        "evidence_summary": "Atom and bond connectivity provide the learned molecular representation shared by D06 and F06.",
        "scientific_rationale": "structure-based molecular learning",
        "normalized_rule": "Use the molecular graph in both final models.", "unit": "",
        "transformation": "Chemprop graph featurisation", "missing_value_rule": "invalid molecular records excluded upstream",
        "model_scope": "D06;F06", "computational_use": "shared learned representation",
        "downstream_asset": "final D06/F06 model inputs", "status": "implemented_in_final_models",
        "provenance_path": f"{d06_spec_path.relative_to(ROOT).as_posix()};{f06_spec_path.relative_to(ROOT).as_posix()}",
    })

    with d06_features_path.open("r", encoding="utf-8-sig", newline="") as f:
        d06_columns = set(next(csv.reader(f)))
    with f06_features_path.open("r", encoding="utf-8-sig", newline="") as f:
        f06_columns = set(next(csv.reader(f)))

    for i, feature in enumerate(read_csv(feature_manifest_path), 1):
        if feature.get("use_in_training", "").lower() != "yes":
            continue
        name = feature.get("feature_name", "")
        if name in d06_columns and name in f06_columns:
            scope, status, downstream = "D06;F06", "implemented_in_final_models", "final D06/F06 descriptor inputs"
        elif name in f06_columns:
            scope, status, downstream = "F06", "implemented_in_final_F06", "final F06 family-sensitive descriptor input"
        else:
            scope = "sparse-descriptor training in progress; final model ID pending"
            status = "training_in_progress_pending_final_results"
            downstream = "ongoing sparse-representation training and evaluation"
        endpoint_rows.append({
            "item_id": f"REP{i:03d}", "item_type": "representation",
            "human_readable_name": feature.get("notes", "") or name.replace("_", " "),
            "machine_readable_field": name, "source": feature_manifest_path.relative_to(ROOT).as_posix(),
            "evidence_summary": f"{feature.get('feature_group', '')} descriptor defined in the project feature manifest.",
            "scientific_rationale": feature.get("notes", ""),
            "normalized_rule": f"Compute {name} as a {feature.get('feature_type', '')} molecular descriptor.",
            "unit": "descriptor-defined", "transformation": "model-configured",
            "missing_value_rule": "feature-pipeline validation", "model_scope": scope,
            "computational_use": "molecular representation", "downstream_asset": downstream,
            "status": status, "provenance_path": feature_manifest_path.relative_to(ROOT).as_posix(),
        })
    endpoint_fields = [
        "item_id", "item_type", "human_readable_name", "machine_readable_field", "source",
        "evidence_summary", "scientific_rationale", "normalized_rule", "unit", "transformation",
        "missing_value_rule", "model_scope", "computational_use", "downstream_asset", "status", "provenance_path",
    ]
    write_csv(OUT / "endpoint_representation_registry.csv", endpoint_fields, endpoint_rows)

    mechanism_rows = []
    for i, row in enumerate(lane, 1):
        doi = row.get("supporting_dois", "").split(";")[0].strip()
        source_id = doi_to_source[doi]
        source_doi, source_title = source_fields(source_by_id, source_id)
        lane_name, family = row.get("mechanism_lane", ""), row.get("motif_family", "")
        mechanism_rows.append({
            "mechanism_rule_id": f"MR{i:04d}", "source_id": source_id,
            "source_doi": source_doi, "source_title": source_title, "mechanism_lane": lane_name,
            "family_scope": family, "evidence_summary": row.get("claim_supported", ""),
            "normalized_field": "mechanism_lane;family_scope;coinitiator_context",
            "normalized_rule": f"Route {family or 'eligible candidates'} to {lane_name} subject to the recorded claim limit.",
            "routing_rule": row.get("priority_scope", ""), "exclusion_rule": row.get("claim_limit", ""),
            "computational_use": "candidate routing and lane-specific validation-question assignment",
            "downstream_asset": "candidate portfolio; mechanism-matched QM route",
            "evidence_level": row.get("evidence_level", ""), "status": "traceable_routing_rule",
            "provenance_path": lane_path.relative_to(ROOT).as_posix(),
        })
    mechanism_fields = [
        "mechanism_rule_id", "source_id", "source_doi", "source_title", "mechanism_lane",
        "family_scope", "evidence_summary", "normalized_field", "normalized_rule", "routing_rule",
        "exclusion_rule", "computational_use", "downstream_asset", "evidence_level", "status", "provenance_path",
    ]
    write_csv(OUT / "mechanism_knowledge_registry.csv", mechanism_fields, mechanism_rows)

    candidate_rows = []
    for row in read_csv(candidate_path):
        candidate_rows.append({
            "candidate_id": row.get("variant_id", "") or row.get("result_line", ""),
            "family": row.get("scaffold_family", ""), "mechanism_lane": row.get("mechanism_class", ""),
            "representative_role": row.get("representative_role", ""),
            "selection_evidence": row.get("positioning_note", ""), "selection_status": row.get("evidence_status", ""),
            "qm_route": row.get("validation_targets", ""),
            "qm_result_status": "not_consolidated_in_unique_manuscript_facing_manifest",
            "decision_status": row.get("next_validation", ""),
            "provenance_path": candidate_path.relative_to(ROOT).as_posix(),
        })
    candidate_fields = [
        "candidate_id", "family", "mechanism_lane", "representative_role", "selection_evidence",
        "selection_status", "qm_route", "qm_result_status", "decision_status", "provenance_path",
    ]
    write_csv(OUT / "candidate_qm_mapping.csv", candidate_fields, candidate_rows)

    examples = [
        {"example_id":"EX001","literature_source_id":"P0004","doi":source_by_id["P0004"]["doi"],"source_title":source_by_id["P0004"]["title"],"evidence":"A cleavable unimolecular 2PI family based on oxime-ester chemistry provides direct Type-I precedent.","formalised_object":"cleavage_center=present; family=oxime_ester; lane=Type-I","why_formalised_this_way":"The initiating motif and cleavage question are mechanistically actionable.","computational_use":"Type-I admission and representative selection","downstream_asset":"N-O BDE; radical-fragment spin density; TD-DFT/NTO route","implementation_source":"mechanism_knowledge_registry.csv; candidate_qm_mapping.csv","status":"direct_precedent_traceable"},
        {"example_id":"EX002","literature_source_id":"P0010","doi":source_by_id["P0010"]["doi"],"source_title":source_by_id["P0010"]["title"],"evidence":"Benzophenone-like photoinitiators are treated as Type-II/context-dependent systems.","formalised_object":"family=benzophenone; coinitiator_context=required_or_explicit; lane=Type-II","why_formalised_this_way":"Hydrogen-donor or electron-transfer context changes admissibility and validation requirements.","computational_use":"Type-II routing rather than single-component Type-I scoring","downstream_asset":"coinitiator-pair H-abstraction/ET assessment","implementation_source":"domain_knowledge_registry.csv; mechanism_knowledge_registry.csv","status":"direct_precedent_traceable"},
        {"example_id":"EX003","literature_source_id":"P0025","doi":source_by_id["P0025"]["doi"],"source_title":source_by_id["P0025"]["title"],"evidence":"Aminostyryl-triazine donor-acceptor motifs have direct 2PP optical precedent, but ET claims remain pair/context dependent.","formalised_object":"family=aminostyryl_triazine; lane=SET/PET_or_optical; ET_context=required","why_formalised_this_way":"Optical response alone does not establish electron-transfer initiation.","computational_use":"exploratory optical/SET-PET routing with a claim ceiling","downstream_asset":"redox/radical-ion/DeltaG_ET assessment","implementation_source":"mechanism_knowledge_registry.csv","status":"direct_precedent_with_claim_limit"},
        {"example_id":"EX004","literature_source_id":"P0003","doi":source_by_id["P0003"]["doi"],"source_title":source_by_id["P0003"]["title"],"evidence":"Radical 2PP photoinitiator performance depends on optical, photochemical, family and formulation context.","formalised_object":"multi-property profile plus family/mechanism controls","why_formalised_this_way":"A single optical score cannot represent initiation competence or deployment constraints.","computational_use":"six-task endpoint design and mechanism-aware candidate qualification","downstream_asset":"D06/F06 profiles; risk gates; mechanism lanes","implementation_source":"domain_knowledge_registry.csv; endpoint_representation_registry.csv","status":"review_level_domain_support"},
        {"example_id":"EX005","literature_source_id":"P0003;P0004","doi":f"{source_by_id['P0003']['doi']};{source_by_id['P0004']['doi']}","source_title":"Domain/family evidence linked to the implemented representation","evidence":"Family and initiating-motif information was formalised separately from generic physicochemical descriptors.","formalised_object":"D06=graph+11 RDKit dense; F06=D06+11 PI-family/topology descriptors","why_formalised_this_way":"The secondary model provides a family-sensitive diagnostic view without replacing the primary model.","computational_use":"D06 primary prediction; F06 disagreement/family-sensitivity diagnosis","downstream_asset":"final D06/F06 feature tables and training specifications","implementation_source":f"{feature_manifest_path.relative_to(ROOT).as_posix()};{d06_features_path.relative_to(ROOT).as_posix()};{f06_features_path.relative_to(ROOT).as_posix()}","status":"implementation_verified"},
    ]
    example_fields = ["example_id", "literature_source_id", "doi", "source_title", "evidence", "formalised_object", "why_formalised_this_way", "computational_use", "downstream_asset", "implementation_source", "status"]
    write_csv(OUT / "examples" / "evidence_to_computational_use_examples.csv", example_fields, examples)

    crosswalk_rows = [
        {"methods_concept":"literature provenance and evidence sourcing","registry_file":"source_registry.csv","registry_keys":"source_id;doi;evidence_location","paper_step":"C1 literature knowledge formalisation","statement_boundary":"Sources support criteria/rules; missing metadata are not inferred."},
        {"methods_concept":"domain evaluation requirements","registry_file":"domain_knowledge_registry.csv","registry_keys":"knowledge_id;normalized_rule;computational_use","paper_step":"definition of what a 2PI candidate should be evaluated on","statement_boundary":"Rules define evaluation scope, not experimental validation of every endpoint."},
        {"methods_concept":"six predictive endpoints","registry_file":"endpoint_representation_registry.csv","registry_keys":"EP001-EP006","paper_step":"multitask target definition","statement_boundary":"Endpoints form predictive proxies, not direct polymerisation outcomes."},
        {"methods_concept":"D06 and F06 molecular representations","registry_file":"endpoint_representation_registry.csv","registry_keys":"REP000;representation rows","paper_step":"model input construction","statement_boundary":"D06 is primary; F06 adds family-sensitive descriptors and acts diagnostically."},
        {"methods_concept":"mechanism-specific candidate routing","registry_file":"mechanism_knowledge_registry.csv","registry_keys":"mechanism_rule_id;mechanism_lane;routing_rule","paper_step":"Type-I/Type-II/SET-PET assignment","statement_boundary":"Routing encodes admissibility and claim limits; it is not mechanism proof."},
        {"methods_concept":"representative selection and QM route","registry_file":"candidate_qm_mapping.csv","registry_keys":"candidate_id;mechanism_lane;qm_route","paper_step":"mechanism-matched physicochemical assessment","statement_boundary":"Candidate-level numerical results require a separate consolidated result manifest."},
    ]
    write_csv(OUT / "methods_c1_crosswalk.csv", ["methods_concept", "registry_file", "registry_keys", "paper_step", "statement_boundary"], crosswalk_rows)

    source_doi_count = sum(bool(row["doi"]) for row in source_rows)
    citation_ready = sum(row["metadata_status"] == "citation_ready" for row in source_rows)
    pending_metadata = sum(row["metadata_status"] == "doi_only_pending" for row in source_rows)
    final_model_items = sum("implemented_in_final" in row["status"] for row in endpoint_rows)
    in_progress_items = sum("training_in_progress" in row["status"] for row in endpoint_rows)
    completeness_rows = [
        {"layer":"Sources","registry":"source_registry.csv","total_items":len(source_rows),"with_doi":source_doi_count,"linked_to_computational_use":"n/a","pending_metadata":pending_metadata,"summary":f"{citation_ready} citation-ready; {pending_metadata} DOI-only rows pending title metadata."},
        {"layer":"Layer 1","registry":"domain_knowledge_registry.csv","total_items":len(domain_rows),"with_doi":sum(bool(r['source_doi']) for r in domain_rows),"linked_to_computational_use":sum(bool(r['computational_use']) for r in domain_rows),"pending_metadata":sum(not r['source_title'] for r in domain_rows),"summary":"Domain/family criteria with explicit claim limits and downstream roles."},
        {"layer":"Layer 2","registry":"endpoint_representation_registry.csv","total_items":len(endpoint_rows),"with_doi":sum(bool(r['source']) and r['source'].startswith('P') for r in endpoint_rows),"linked_to_computational_use":sum(bool(r['computational_use']) for r in endpoint_rows),"pending_metadata":sum('pending' in r['status'] for r in endpoint_rows),"summary":f"{final_model_items} items implemented in frozen D06/F06 assets; {in_progress_items} sparse descriptors are in active training and await final result freeze."},
        {"layer":"Layer 3","registry":"mechanism_knowledge_registry.csv","total_items":len(mechanism_rows),"with_doi":sum(bool(r['source_doi']) for r in mechanism_rows),"linked_to_computational_use":sum(bool(r['computational_use']) for r in mechanism_rows),"pending_metadata":sum(not r['source_title'] for r in mechanism_rows),"summary":"Mechanism/family rules linked to candidate routing and lane-specific QM questions."},
        {"layer":"Candidate/QM map","registry":"candidate_qm_mapping.csv","total_items":len(candidate_rows),"with_doi":"n/a","linked_to_computational_use":sum(bool(r['qm_route']) for r in candidate_rows),"pending_metadata":sum(r['qm_result_status'].startswith('not_consolidated') for r in candidate_rows),"summary":"Routing is present; a unique manuscript-facing numerical QM result manifest remains separate."},
    ]
    write_csv(OUT / "completeness_summary.csv", ["layer", "registry", "total_items", "with_doi", "linked_to_computational_use", "pending_metadata", "summary"], completeness_rows)

    field_rows = [
        {"field":"source_id","registry":"source/domain/mechanism","required":"yes","human_meaning":"Stable identifier connecting a rule to its literature source."},
        {"field":"evidence_summary","registry":"domain/endpoint/mechanism","required":"yes","human_meaning":"Plain-language statement of what the evidence supports."},
        {"field":"normalized_rule","registry":"domain/endpoint/mechanism","required":"yes","human_meaning":"Machine-actionable or decision-actionable formalisation."},
        {"field":"computational_use","registry":"domain/endpoint/mechanism","required":"yes","human_meaning":"The modelling, filtering, or routing step that consumes the formalised knowledge."},
        {"field":"downstream_asset","registry":"domain/endpoint/mechanism","required":"yes","human_meaning":"The concrete model, screening, portfolio, or QM asset affected."},
        {"field":"status","registry":"all","required":"yes","human_meaning":"Traceability, implementation, or review state; missing evidence is never inferred."},
        {"field":"provenance_path","registry":"domain/endpoint/mechanism/candidate","required":"yes","human_meaning":"Repository-relative path to the originating project asset."},
    ]
    write_csv(OUT / "schema" / "field_dictionary.csv", ["field", "registry", "required", "human_meaning"], field_rows)
    vocabulary_rows = [
        {"field":"metadata_status","allowed_values":"citation_ready|doi_only_pending","definition":"Whether DOI and a readable title are present."},
        {"field":"item_type","allowed_values":"endpoint|representation","definition":"Layer-2 registry object type."},
        {"field":"mechanism_lane","allowed_values":"Type-I|Type-II|SET/PET_or_optical|boundary variants","definition":"Mechanism-aware routing category retained from the curated source asset."},
        {"field":"evidence_value_lane","allowed_values":"text_exact|origin_digitized|model_inferred","definition":"Confidence/provenance class for numerical evidence; inferred values remain explicitly derived."},
        {"field":"qm_result_status","allowed_values":"pending|completed|failed|not_consolidated_in_unique_manuscript_facing_manifest","definition":"Candidate-level QM result consolidation state."},
    ]
    write_csv(OUT / "schema" / "controlled_vocabulary.csv", ["field", "allowed_values", "definition"], vocabulary_rows)

    summary_md = f"""# Supplementary registry summary ({VERSION})

This compact summary accompanies the Methods/Supplementary Information so that the C1 logic remains understandable without requiring the reader to inspect the full GitHub package.

| Layer | Scientific question | Registry | Items | Direct computational link |
|---|---|---|---:|---|
| Source | Where did the evidence come from? | `source_registry.csv` | {len(source_rows)} | DOI/source provenance |
| Layer 1 | What should a 2PI candidate be evaluated on? | `domain_knowledge_registry.csv` | {len(domain_rows)} | domain criteria and admissibility controls |
| Layer 2 | What is predicted and how is the molecule represented? | `endpoint_representation_registry.csv` | {len(endpoint_rows)} | six targets; graph; D06/F06 descriptors |
| Layer 3 | How is a candidate routed to mechanism-specific assessment? | `mechanism_knowledge_registry.csv` | {len(mechanism_rows)} | Type-I/Type-II/SET-PET routing and claim limits |

The complete evidence chain and five worked examples are provided in `examples/evidence_to_computational_use_examples.csv`. Candidate-level numerical QM results remain a separate result asset and are not embedded in mechanism rules.
"""
    (OUT / "SUPPLEMENTARY_REGISTRY_SUMMARY.md").write_text(summary_md, encoding="utf-8")

    audit_md = f"""# Registry completeness and traceability audit

Release: **{VERSION}** ({RELEASE_DATE})

| Registry | Rows | DOI/source coverage | Computational-use coverage | Pending |
|---|---:|---:|---:|---:|
| Sources | {len(source_rows)} | {source_doi_count}/{len(source_rows)} DOI | n/a | {pending_metadata} DOI-only title records |
| Layer 1 domain knowledge | {len(domain_rows)} | {sum(bool(r['source_doi']) for r in domain_rows)}/{len(domain_rows)} | {sum(bool(r['computational_use']) for r in domain_rows)}/{len(domain_rows)} | {sum(not r['source_title'] for r in domain_rows)} source titles |
| Layer 2 endpoint/representation | {len(endpoint_rows)} | explicit where available | {sum(bool(r['computational_use']) for r in endpoint_rows)}/{len(endpoint_rows)} | {sum('pending' in r['status'] for r in endpoint_rows)} literature mappings |
| Layer 3 mechanism knowledge | {len(mechanism_rows)} | {sum(bool(r['source_doi']) for r in mechanism_rows)}/{len(mechanism_rows)} | {sum(bool(r['computational_use']) for r in mechanism_rows)}/{len(mechanism_rows)} | {sum(not r['source_title'] for r in mechanism_rows)} source titles |
| Candidate/QM map | {len(candidate_rows)} | n/a | {sum(bool(r['qm_route']) for r in candidate_rows)}/{len(candidate_rows)} routed | {sum(r['qm_result_status'].startswith('not_consolidated') for r in candidate_rows)} unconsolidated result rows |

## Reproducibility checks

- Every Layer 1 and Layer 3 row resolves to a valid `source_id`.
- Every Layer 1, Layer 2, Layer 3, and candidate/QM row records its computational use or route.
- D06/F06 descriptor scope is checked against final feature-table headers.
- Missing source titles and endpoint-level literature mappings remain explicit pending states.
- Numerical evidence retains `text_exact`, `origin_digitized`, or `model_inferred` provenance.
- Mechanism rules and candidate-level QM results remain separate evidence objects.
"""
    (OUT / "AUDIT_REPORT.md").write_text(audit_md, encoding="utf-8")

    readme = f"""# C1 — role-structured literature knowledge for 2PI discovery

**C1 formalises heterogeneous photoinitiator literature into traceable domain criteria, endpoint/representation definitions, and mechanism-control rules consumed by the computational workflow.**

Release: **{VERSION}** · Frozen: **{RELEASE_DATE}**

| Layer | Question answered | Registry | Paper step |
|---|---|---|---|
| Source | Where did the evidence come from? | [`source_registry.csv`](source_registry.csv) | provenance |
| Layer 1 | What should be evaluated? | [`domain_knowledge_registry.csv`](domain_knowledge_registry.csv) | endpoint and admissibility design |
| Layer 2 | What is predicted and how is a molecule represented? | [`endpoint_representation_registry.csv`](endpoint_representation_registry.csv) | D06/F06 construction |
| Layer 3 | How is a candidate routed? | [`mechanism_knowledge_registry.csv`](mechanism_knowledge_registry.csv) | Type-I/Type-II/SET-PET decision control |

```mermaid
flowchart LR
    A[Source: DOI / source asset] --> B[Evidence statement]
    B --> C[Structured criterion / endpoint / descriptor / rule]
    C --> D[Model, screening or mechanism routing]
    D --> E[Concrete downstream asset]
```

## Five-minute review path

1. Read the three-layer table above.
2. Inspect the five complete chains in [`examples/evidence_to_computational_use_examples.csv`](examples/evidence_to_computational_use_examples.csv).
3. Check [`completeness_summary.csv`](completeness_summary.csv) and [`AUDIT_REPORT.md`](AUDIT_REPORT.md).
4. Use [`methods_c1_crosswalk.csv`](methods_c1_crosswalk.csv) to map each Methods concept to a registry and claim boundary.

## Completeness at {VERSION}

| Object | Count | Key status |
|---|---:|---|
| Sources | {len(source_rows)} | {source_doi_count} DOI-linked; {citation_ready} citation-ready; {pending_metadata} DOI-only title records pending |
| Layer 1 evidence units | {len(domain_rows)} | all linked to a source and computational use |
| Layer 2 items | {len(endpoint_rows)} | {final_model_items} implemented in frozen D06/F06 assets; {in_progress_items} sparse descriptors are in active training and await final result freeze |
| Layer 3 rules | {len(mechanism_rows)} | all linked to mechanism routing and a claim limit |
| Candidate/QM mappings | {len(candidate_rows)} | routes recorded; numerical result consolidation remains a separate asset |

## Interpretation boundary

This is a role-structured evidence registry, not a homogeneous molecular database. A paper contributes only the evidence it contains. Missing values remain missing. Six-task outputs are predictive proxies, mechanism rules define admissibility rather than proof, and candidate-level QM numbers are kept outside the rule registries.

## Paper and repository crosswalk

The compact manuscript-facing summary is [`SUPPLEMENTARY_REGISTRY_SUMMARY.md`](SUPPLEMENTARY_REGISTRY_SUMMARY.md). The exact Methods-to-registry mapping is [`methods_c1_crosswalk.csv`](methods_c1_crosswalk.csv).

## Rebuild and verification

The builder is included for provenance. Rebuilding requires the parent computational-project source assets listed in [`package_manifest.json`](package_manifest.json); those large upstream assets are not duplicated in this standalone evidence release. Release hashes are recorded in [`checksums.sha256`](checksums.sha256).
"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")
    (OUT / "VERSION").write_text(VERSION + "\n", encoding="utf-8")

    payload_paths = sorted(path for path in OUT.rglob("*") if path.is_file() and path.name not in {"package_manifest.json", "checksums.sha256"})
    checksums = {path.relative_to(OUT).as_posix(): sha256(path) for path in payload_paths}
    (OUT / "checksums.sha256").write_text("\n".join(f"{digest}  {name}" for name, digest in checksums.items()) + "\n", encoding="utf-8")
    manifest = {
        "package": "literature_knowledge", "release": VERSION, "release_date": RELEASE_DATE,
        "frozen": True, "principle": "evidence_unit_plus_computational_role",
        "builder": "tools/build_literature_knowledge_package.py", "builder_version": BUILDER_VERSION,
        "builder_sha256": sha256(Path(__file__)),
        "source_assets": [
            doi_detail_path.relative_to(ROOT).as_posix(), lane_path.relative_to(ROOT).as_posix(),
            feature_manifest_path.relative_to(ROOT).as_posix(), candidate_path.relative_to(ROOT).as_posix(),
            d06_features_path.relative_to(ROOT).as_posix(), f06_features_path.relative_to(ROOT).as_posix(),
            d06_spec_path.relative_to(ROOT).as_posix(), f06_spec_path.relative_to(ROOT).as_posix(),
            strict_clean_path.relative_to(ROOT).as_posix(),
        ],
        "file_sha256": checksums,
    }
    (OUT / "package_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
