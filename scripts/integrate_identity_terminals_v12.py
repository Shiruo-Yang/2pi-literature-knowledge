#!/usr/bin/env python3
"""Extend the source-local identity database with safe contextual identities.

This is an identity-layer update only.  It does not create numerical labels,
training rows, external-validation observations, or screening results.  Names
that resolve to salts, mixtures, counterion-unspecified materials, or obvious
non-chemical tokens are recorded in terminal registries and excluded from the
single-molecule unresolved queue.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rdkit import Chem, rdBase
from rdkit.Chem import rdMolDescriptors

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "outputs" / "literature_kb_condition_identity_linkage_20260906_v11"
TEXT = ROOT / "outputs" / "literature_kb_source_text_identity_recovery_v4_20260906"
OUT = ROOT / "outputs" / "literature_kb_condition_identity_linkage_20260906_v12"

ACCEPTED_COLUMNS = [
    "entity_id", "paper_id", "doi", "source_label", "canonical_name", "canonical_smiles",
    "inchikey", "molecular_formula", "confidence_tier", "identity_status", "identity_channel",
    "source_evidence_id", "source_location", "rendered_page_path", "source_detection_count",
    "external_query_name", "external_pubchem_cid", "external_inchikey", "crosscheck_basis",
    "scientific_use_boundary",
]
MATERIAL_COLUMNS = [
    "entity_id", "paper_id", "doi", "source_label", "source_material_name", "source_definition_count",
    "source_evidence_ids", "source_locations", "rendered_page_paths", "pubchem_query_slug", "pubchem_cid",
    "material_canonical_smiles", "material_inchikey", "material_formula", "component_count",
    "component_smiles", "component_formulas", "component_formal_charges", "net_formal_charge",
    "opposite_charge_components", "rdkit_valid", "external_resolution_basis", "material_identity_status",
    "confidence_tier", "single_graph_model_eligible", "identity_database_action", "required_next_evidence",
    "scientific_use_boundary",
]
TERMINAL_COLUMNS = [
    "entity_id", "paper_id", "doi", "source_label", "terminal_status", "terminal_reason",
    "source_evidence_id", "source_location", "scientific_boundary",
]

def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)

def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def formula(smiles: str) -> str:
    mol = Chem.MolFromSmiles(smiles)
    if not mol:
        raise ValueError(f"invalid SMILES: {smiles}")
    return str(rdMolDescriptors.CalcMolFormula(mol))

def inchikey(smiles: str) -> str:
    mol = Chem.MolFromSmiles(smiles)
    if not mol:
        raise ValueError(f"invalid SMILES: {smiles}")
    return Chem.MolToInchiKey(mol)

def source_rows() -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    entities = read_csv(BASE / "source_local_entity_candidates_enriched.csv")
    by_key = {(r["paper_id"], r.get("normalized_label", "").lower()): r for r in entities}
    candidates = read_csv(TEXT / "source_text_identity_candidates.csv")
    by_entity: dict[str, list[dict[str, str]]] = {}
    for r in candidates:
        by_entity.setdefault(r["entity_id"], []).append(r)
    selected: dict[str, dict[str, str]] = {}
    for eid, rows in by_entity.items():
        rows.sort(key=lambda r: (0 if r.get("candidate_eligibility") == "eligible_external_query" else 1,
                                 int(r.get("page_number", "999") or 999), r["candidate_id"]))
        selected[eid] = rows[0]
    return by_key, selected

def resolve_entity(by_key: dict[tuple[str, str], dict[str, str]], paper: str, label: str) -> dict[str, str]:
    key = (paper, label.lower())
    if key not in by_key:
        raise KeyError(f"missing source entity: {paper}/{label}")
    return by_key[key]

def evidence_for(entity: dict[str, str], candidates: dict[str, dict[str, str]]) -> dict[str, str]:
    row = candidates.get(entity["entity_id"])
    if not row:
        # Some contextual identities were recovered from the source-local
        # entity record and the original page text, rather than the earlier
        # candidate extractor.  Preserve that trace explicitly instead of
        # inventing a structure-extraction evidence row.
        return {
            "candidate_id": f"SRCENTITY-{entity['entity_id']}",
            "page_number": (entity.get("page_hints", "").split(";")[0] if entity.get("page_hints") else ""),
            "source_location": f"PDF page {entity.get('page_hints', '')}; source-local entity text and validated structure anchor",
            "rendered_page_path": "",
        }
    return row

def make_identity(entity: dict[str, str], label: str, name: str, smiles: str,
                  tier: str, channel: str, basis: str, candidates: dict[str, dict[str, str]]) -> dict[str, Any]:
    ev = evidence_for(entity, candidates)
    mol = Chem.MolFromSmiles(smiles)
    if mol is None or not Chem.SanitizeMol(mol, catchErrors=True) == Chem.SanitizeFlags.SANITIZE_NONE:
        raise ValueError(f"RDKit validation failed: {label}")
    smi = Chem.MolToSmiles(mol, canonical=True)
    key = Chem.MolToInchiKey(mol)
    page = ev.get("page_number", "")
    rendered = ev.get("rendered_page_path", "")
    if not rendered and page:
        candidate = TEXT / "source_pages" / entity["paper_id"] / f"page_{int(page):04d}.png"
        if candidate.exists(): rendered = str(candidate)
    return {
        "entity_id": entity["entity_id"], "paper_id": entity["paper_id"], "doi": entity["doi"],
        "source_label": label, "canonical_name": name, "canonical_smiles": smi, "inchikey": key,
        "molecular_formula": formula(smi), "confidence_tier": tier,
        "identity_status": "source_context_structure_identity_accepted",
        "identity_channel": channel, "source_evidence_id": ev["candidate_id"],
        "source_location": ev.get("source_location", f"PDF page {page}; source-text identity context"),
        "rendered_page_path": rendered, "source_detection_count": entity.get("occurrence_count", "0"),
        "external_query_name": "", "external_pubchem_cid": "", "external_inchikey": "",
        "crosscheck_basis": basis,
        "scientific_use_boundary": "Source-local identity linkage only; not a numerical benchmark label, model target, external-validation observation, or screening result.",
    }

def make_material(entity: dict[str, str], label: str, name: str, status: str, reason: str,
                  candidates: dict[str, dict[str, str]], smiles: str = "", components: str = "",
                  formulas: str = "", charges: str = "", count: str = "") -> dict[str, Any]:
    ev = evidence_for(entity, candidates)
    page = ev.get("page_number", "")
    rendered = ev.get("rendered_page_path", "")
    if not rendered and page:
        candidate = TEXT / "source_pages" / entity["paper_id"] / f"page_{int(page):04d}.png"
        if candidate.exists(): rendered = str(candidate)
    key = inchikey(smiles) if smiles else ""
    return {
        "entity_id": entity["entity_id"], "paper_id": entity["paper_id"], "doi": entity["doi"],
        "source_label": label, "source_material_name": name, "source_definition_count": entity.get("occurrence_count", "1"),
        "source_evidence_ids": ev["candidate_id"], "source_locations": ev.get("source_location", f"PDF page {page}"),
        "rendered_page_paths": rendered, "pubchem_query_slug": "", "pubchem_cid": "",
        "material_canonical_smiles": smiles, "material_inchikey": key, "material_formula": formula(smiles) if smiles else "",
        "component_count": count, "component_smiles": components, "component_formulas": formulas,
        "component_formal_charges": charges, "net_formal_charge": "0" if charges and "-1;1" in charges else "",
        "opposite_charge_components": "true" if charges and "-1;1" in charges else "",
        "rdkit_valid": "true" if smiles else "false", "external_resolution_basis": "source_text_and_structure_record" if smiles else "source_text_only",
        "material_identity_status": status, "confidence_tier": "B_material_contextual",
        "single_graph_model_eligible": "no", "identity_database_action": "keep_in_material_registry_only",
        "required_next_evidence": reason,
        "scientific_use_boundary": "Material identity only; not a single-molecule graph, numerical benchmark label, external-validation observation, screening result, or quantum-chemistry input.",
    }

def make_terminal(entity: dict[str, str], label: str, status: str, reason: str,
                  candidates: dict[str, dict[str, str]]) -> dict[str, str]:
    ev = evidence_for(entity, candidates)
    return {"entity_id": entity["entity_id"], "paper_id": entity["paper_id"], "doi": entity["doi"],
            "source_label": label, "terminal_status": status, "terminal_reason": reason,
            "source_evidence_id": ev["candidate_id"], "source_location": ev.get("source_location", ""),
            "scientific_boundary": "Terminal classification only; excluded from single-molecule training and unresolved identity queue."}

def update_entities(rows: list[dict[str, str]], identities: dict[str, dict[str, Any]],
                    materials: dict[str, dict[str, Any]], terminals: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    out = []
    for original in rows:
        row = dict(original); eid = row["entity_id"]
        if eid in identities:
            x = identities[eid]; row.update({"canonical_smiles": x["canonical_smiles"], "inchikey": x["inchikey"],
                "molecular_formula": x["molecular_formula"], "identity_resolution_status": "source_local_identity_accepted",
                "identity_confidence_tier": x["confidence_tier"], "identity_resolution_basis": x["crosscheck_basis"],
                "identity_resolution_provenance": x["identity_channel"], "identity_channel": x["identity_channel"],
                "identity_source_location": x["source_location"], "identity_source_evidence_id": x["source_evidence_id"],
                "entity_status": "source_local_identity_accepted", "structure_status": "complete_rdkit_valid_identity_accepted",
                "scientific_use": "identity_linkage_only_not_numeric_benchmark_truth"})
        elif eid in materials:
            row.update({"identity_resolution_status": "terminal_material_classified", "identity_confidence_tier": materials[eid]["confidence_tier"],
                        "entity_status": "terminal_material_classified", "structure_status": "material_or_counterion_incomplete",
                        "scientific_use": "material_identity_only_not_single_graph_or_numeric_truth"})
        elif eid in terminals:
            row.update({"identity_resolution_status": "terminal_nonchemical_token", "identity_confidence_tier": "terminal_rejected",
                        "entity_status": "terminal_nonchemical_token", "structure_status": "not_a_molecular_identity",
                        "scientific_use": "excluded_from_molecular_database"})
        out.append(row)
    return out

def update_links(rows: list[dict[str, str]], identities: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    out=[]; n=0
    for original in rows:
        row=dict(original); x=identities.get(row["entity_id"])
        if x:
            n+=1; row.update({"resolved_canonical_smiles": x["canonical_smiles"], "resolved_inchikey": x["inchikey"],
                "resolved_molecular_formula": x["molecular_formula"], "identity_resolution_tier": x["confidence_tier"],
                "identity_resolution_status": "source_local_identity_accepted", "identity_resolution_source": x["identity_channel"],
                "link_confidence": "accepted_source_local_identity_link", "link_status": "source_local_identity_link_accepted"})
        out.append(row)
    return out,n

def update_formulations(rows: list[dict[str, str]], identities: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], int, int]:
    out=[]; enriched=0; backed=0
    for original in rows:
        row=dict(original); ids=[x for x in (row.get("source_local_entity_ids", "").split(";") if row.get("source_local_entity_ids") else []) if x in identities]
        if ids:
            enriched+=1; previous=int(row.get("structure_backed_entity_count", "0") or 0)
            oldids=set(x for x in row.get("crosschecked_source_local_entity_ids", "").split(";") if x)
            oldkeys=set(x for x in row.get("crosschecked_source_local_inchikeys", "").split(";") if x)
            oldids.update(ids); oldkeys.update(identities[x]["inchikey"] for x in ids)
            row["structure_backed_entity_count"]=str(previous+len(set(ids))); row["crosschecked_source_local_entity_ids"]=";".join(sorted(oldids)); row["crosschecked_source_local_inchikeys"]=";".join(sorted(oldkeys))
            row["identity_enrichment_status"]="source_local_identity_crosschecked_v12"; row["identity_resolution"]="accepted_source_local_structure_identity"
            row["formulation_status"]="multi_field_identity_and_structure_linked_candidate" if int(row.get("field_group_count", "0") or 0)>=2 else "single_field_identity_and_structure_linked_context"
            if previous==0: backed+=1
        out.append(row)
    return out,enriched,backed

def write_sqlite(path: Path, tables: list[tuple[str,list[dict[str,Any]],list[str]]]) -> None:
    if path.exists(): path.unlink()
    con=sqlite3.connect(path)
    try:
        for name,rows,cols in tables:
            con.execute(f'DROP TABLE IF EXISTS "{name}"')
            con.execute(f'CREATE TABLE "{name}" (' + ', '.join(f'"{c}" TEXT' for c in cols) + ')')
            con.executemany(f'INSERT INTO "{name}" VALUES ({", ".join("?" for _ in cols)})', [[str(r.get(c,"")) for c in cols] for r in rows])
        con.commit()
    finally: con.close()

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("--base-dir",type=Path,default=BASE); ap.add_argument("--text-dir",type=Path,default=TEXT); ap.add_argument("--output-dir",type=Path,default=OUT); args=ap.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for p in args.base_dir.iterdir():
        if p.is_file() and p.name not in {"README_CN.md","run_summary.json","VALIDATION_REPORT.json","integration_manifest.json"}: shutil.copy2(p,args.output_dir/p.name)
    by_key,candidates=source_rows()
    # Source-local identities accepted because the full name or trade name is
    # unambiguous in context and the structure is fixed by a validated anchor.
    specs=[
      ("ZPC-000021","dmaema","DMAEMA","2-(dimethylamino)ethyl methacrylate","C=C(C)C(=O)OCCN(C)C","A_contextual_name_structure"),
      ("ZPC-000021","cq","CQ","camphorquinone","CC12CCC(C(=O)C1=O)C2(C)C","A_contextual_name_structure"),
      ("ZPC-004234","dcca","DCCA","(E)-7-(diethylamino)-2-oxo-2H-chromene-3-carbaldehyde O-acryloyl oxime","C=CC(=O)O/N=C/c1cc2ccc(N(CC)CC)cc2oc1=O","A_contextual_name_structure"),
      ("ZPC-006320","bfc","BFC","2,6-bis(furan-2-ylmethylidene)cyclohexan-1-one","O=C1/C(=C/c2ccco2)CCC/C1=C\\c1ccco1","A_contextual_name_structure"),
      ("ZPC-004253","compound2","compound 2","4-(4′-benzoylphenyl)acetophenone","CC(=O)c1ccc(-c2ccc(C(=O)c3ccccc3)cc2)cc1","A_contextual_name_structure"),
      ("ZPC-004253","compound3","compound 3","4-(4′-benzoylphenyl)acetophenone bromide","O=C(CBr)c1ccc(-c2ccc(C(=O)c3ccccc3)cc2)cc1","A_contextual_name_structure"),
      ("ZPC-001606","dmpt","DMPT","dimethyl-p-toluidine","Cc1ccc(N(C)C)cc1","A_contextual_name_structure"),
      ("ZPC-005809","mtpbp","MTPBP","4-[(4-maleimido)thiophenyl]benzophenone","O=C(c1ccccc1)c1ccc(Sc2ccc(N3C(=O)C=CC3=O)cc2)cc1","A_contextual_name_structure"),
      ("ZPC-000356","bee","BEE","benzoin ethyl ether","CCOC(c1ccccc1)C(=O)c1ccccc1","A_contextual_name_structure"),
      ("ZPC-000336","tea","TEA","triethylamine","CCN(CC)CC","A_contextual_name_structure"),
      ("ZPC-005136","tea","TEA","triethylamine","CCN(CC)CC","A_contextual_name_structure"),
      ("ZPC-001468","tea","TEA","triethylamine","CCN(CC)CC","A_contextual_name_structure"),
      ("ZPC-003968","tea","TEA","triethanolamine","OCCN(CCO)CCO","A_contextual_name_structure"),
      ("zotero_QH8XLKS5","lucirintpol","Lucirin TPOL","Ethyl (2,4,6-trimethylbenzoyl)phenylphosphinate","CCOP(=O)(C(=O)c1c(C)cc(C)cc1C)c1ccccc1","A_contextual_name_structure"),
      ("ZPC-000269","darocur1173","Darocur 1173","2-hydroxy-2-methyl-1-phenylpropan-1-one","CC(C)(O)C(=O)c1ccccc1","A_alias_consensus"),
      ("ZPC-004253","darocur1173","Darocur 1173","2-hydroxy-2-methyl-1-phenylpropan-1-one","CC(C)(O)C(=O)c1ccccc1","A_alias_consensus"),
      ("OA2P-000453","darocur1173","Darocur 1173","2-hydroxy-2-methyl-1-phenylpropan-1-one","CC(C)(O)C(=O)c1ccccc1","A_alias_consensus"),
    ]
    identities={}
    for paper,label,name,canon,smi,tier in specs:
        e=resolve_entity(by_key,paper,label); identities[e["entity_id"]]=make_identity(e,label.upper() if label not in {"lucirintpol","darocur1173"} else ("Lucirin TPOL" if label=="lucirintpol" else "Darocur 1173"),name,smi,tier,"source_context_plus_validated_structure_anchor","explicit source definition and RDKit-valid fixed structure anchor",candidates)
    material_specs=[
      ("zotero_MZLGYQTP","dmdpi","4,4′-dimethyldiphenyliodonium hexafluorophosphate","crosschecked_multicomponent_material_identity","salt has two disconnected charged components","F[P-](F)(F)(F)(F)F.Cc1ccc([I+]c2ccc(C)cc2)cc1","F[P-](F)(F)(F)(F)F;Cc1ccc([I+]c2ccc(C)cc2)cc1","C14H14F6IP;C14H14I+","-1;1","2"),
      ("ZPC-004253","compound4","4-(4′-benzoylphenyl)acetophenone quaternary ammonium bromide","source_defined_salt","bromide salt is not a single neutral molecular graph","[Br-].O=C(C[N+]12CCN(CC1)CC2)c1ccc(-c2ccc(C(=O)c3ccccc3)cc2)cc1","[Br-];O=C(C[N+]12CCN(CC1)CC2)c1ccc(-c2ccc(C(=O)c3ccccc3)cc2)cc1","Br-;C27H27N2O2+","-1;1","2"),
      ("ZPC-004587","hnu","H-Nu 254 commercial cationic photoinitiator material","source_defined_material","commercial material contains a salt and fluorophore component; no single-graph claim","","","","",""),
      ("zotero_4UUBRRGP","eosiny","Eosin Y dianion with counterion unspecified","counterion_unspecified_ionic_material","original table depicts the dye ion without a defined counterion","","","","",""),
      ("ZPC-004762","irgacure754","Irgacure 754 commercial phenyl-glyoxylate material","commercial_mixture_or_trade_material","trade-name material is not treated as one exact structure","","","","",""),
      ("ZPC-004284","litpo61","lithium phenyl(2,4,6-trimethylbenzoyl)phosphinate material","source_defined_salt","lithium salt remains in the material registry and is not a single graph","","","","",""),
    ]
    materials={}
    for item in material_specs:
        paper,label,name,status,reason,smi,comps,forms,charges,count=item
        e=resolve_entity(by_key,paper,label); materials[e["entity_id"]]=make_material(e,label.upper() if label not in {"litpo61","irgacure754","eosiny","hnu","dmdpi"} else label,name,status,reason,candidates,smi,comps,forms,charges,count)
    terminal_specs=[
      ("ZPC-000028","tpip","TPIP","process acronym, not a chemical identity"),("ZPC-000049","pi23","PI 23","citation/type marker, not a chemical identity"),("ZPC-006320","pi2","PI 2","photoinitiator class marker, not a chemical identity"),("OA2P-000080","pi0","PI 0","polyimide abbreviation, not a photoinitiator"),("OA2P-000400","m112","M-112","microscope model identifier, not a chemical identity"),("OA2P-000440","pi4","PI 4","citation/type marker, not a chemical identity"),("ZPC-003094","pi5","PI 5","citation/type marker, not a chemical identity"),("ZPC-000304","pi66","PI 66","citation/type marker, not a chemical identity"),("zotero_AU74BQZ6","pi37","PI 37","citation marker, not a chemical identity"),("OA2P-000087","co2","CO2","laser/source gas, not a photoinitiator"),("OA2P-000132","tea","TEA","TEA CO2 laser acronym, not triethylamine"),("OA2P-000463","tea","TEA","TEA CO2 laser acronym, not triethylamine"),("ZPC-004762","tea","Tea","citation-title token, not triethylamine")]
    terminals={}
    for paper,label,display,reason in terminal_specs:
        e=resolve_entity(by_key,paper,label); terminals[e["entity_id"]]=make_terminal(e,display,"terminal_nonchemical_token",reason,candidates)
    ents0=read_csv(args.base_dir/"source_local_entity_candidates_enriched.csv"); links0=read_csv(args.base_dir/"evidence_entity_links_enriched.csv"); forms0=read_csv(args.base_dir/"formulation_linkage_registry_enriched.csv")
    ents=update_entities(ents0,identities,materials,terminals); links,nlinks=update_links(links0,identities); forms,nforms,nback=update_formulations(forms0,identities)
    oldacc=read_csv(args.base_dir/"accepted_source_identity_registry_v11.csv"); accepted=oldacc+list(identities.values())
    oldmat=read_csv(args.base_dir/"multicomponent_material_registry_v11.csv"); material_rows=oldmat+list(materials.values())
    terminal_rows=list(terminals.values())
    material_terminal_rows=[{"entity_id":r["entity_id"],"paper_id":r["paper_id"],"doi":r["doi"],"source_label":r["source_label"],"terminal_status":"terminal_material_record","terminal_reason":r["material_identity_status"]+": "+r["required_next_evidence"],"source_evidence_id":r["source_evidence_ids"],"source_location":r["source_locations"],"scientific_boundary":"Terminal material classification only; excluded from single-molecule training and unresolved identity queue."} for r in material_rows]
    terminal_identity_rows=terminal_rows+material_terminal_rows
    source_resolved=sum(r.get("entity_type")=="source_local_unresolved" and bool(r.get("resolved_inchikey")) for r in links)
    source_unresolved=sum(r.get("entity_type")=="source_local_unresolved" and not r.get("resolved_inchikey") for r in links)
    accepted_ids={r["entity_id"] for r in accepted}
    accepted_formulations=sum(any(x in accepted_ids for x in (r.get("source_local_entity_ids", "").split(";") if r.get("source_local_entity_ids") else [])) for r in forms)
    old_backed=sum(int(r.get("structure_backed_entity_count", "0") or 0)>0 for r in forms0)
    new_backed=sum(int(r.get("structure_backed_entity_count", "0") or 0)>0 for r in forms)
    write_csv(args.output_dir/"source_local_entity_candidates_enriched.csv",ents,list(ents[0].keys())); write_csv(args.output_dir/"evidence_entity_links_enriched.csv",links,list(links[0].keys())); write_csv(args.output_dir/"formulation_linkage_registry_enriched.csv",forms,list(forms[0].keys())); write_csv(args.output_dir/"accepted_source_identity_registry_v12.csv",accepted,ACCEPTED_COLUMNS); write_csv(args.output_dir/"multicomponent_material_registry_v12.csv",material_rows,MATERIAL_COLUMNS); write_csv(args.output_dir/"terminal_nonchemical_registry_v12.csv",terminal_rows,TERMINAL_COLUMNS); write_csv(args.output_dir/"terminal_identity_registry_v12.csv",terminal_identity_rows,TERMINAL_COLUMNS)
    write_sqlite(args.output_dir/"condition_identity_linkage.sqlite",[("source_local_entity_enriched_v12",ents,list(ents[0].keys())),("evidence_entity_link_enriched_v12",links,list(links[0].keys())),("formulation_linkage_enriched_v12",forms,list(forms[0].keys())),("accepted_source_identity_v12",accepted,ACCEPTED_COLUMNS),("multicomponent_material_v12",material_rows,MATERIAL_COLUMNS),("terminal_nonchemical_v12",terminal_rows,TERMINAL_COLUMNS),("terminal_identity_v12",terminal_identity_rows,TERMINAL_COLUMNS)])
    con=sqlite3.connect(args.output_dir/"condition_identity_linkage.sqlite"); integrity=con.execute("PRAGMA integrity_check").fetchone()[0]; con.close()
    validation={"generated_at_utc":now(),"valid":integrity=="ok" and len(ents)==len(ents0) and len(links)==len(links0) and len(forms)==len(forms0) and len({r['entity_id'] for r in accepted})==len(accepted),"sqlite_integrity":integrity,"row_invariants":{"source_local_entities":len(ents),"evidence_entity_links":len(links),"formulation_clusters":len(forms)},"accepted_identity_rows_total":len(accepted),"new_accepted_identity_rows":len(identities),"material_rows_total":len(material_rows),"terminal_nonchemical_rows":len(terminals),"terminal_identity_rows":len(terminal_identity_rows),"numeric_records_created":0,"model_training_labels_created":0,"external_validation_observations_created":0,"strict_comsol_ready_records_created":0}
    remaining_entities=len(ents)-len(accepted)-len(material_rows)-len(terminals)
    base_summary=json.loads((args.base_dir/"run_summary.json").read_text(encoding="utf-8")); summary={**base_summary,"version":"v12_contextual_identity_and_terminal_classification","built_at":now(),"base_frozen_version":str(args.base_dir.resolve()),"accepted_source_local_identity_links":len(accepted),"new_accepted_source_local_identity_links":len(identities),"source_local_entities_terminal_material":len(materials),"source_local_entities_terminal_material_total":len(material_rows),"source_local_entities_terminal_nonchemical":len(terminals),"remaining_source_local_entities_without_accepted_identity":remaining_entities,"source_local_unresolved_entities":remaining_entities,"source_local_resolved_evidence_links":source_resolved,"source_local_unresolved_evidence_links":source_unresolved,"new_evidence_links_enriched_with_structure":nlinks,"evidence_links_enriched_with_structure":source_resolved,"new_formulation_clusters_enriched":nforms,"newly_structure_backed_formulation_clusters":nback,"structure_backed_formulation_clusters_before":old_backed,"structure_backed_formulation_clusters_after":new_backed,"structure_backed_formulation_clusters":new_backed,"formulation_clusters_with_accepted_source_identity":accepted_formulations,"multicomponent_material_records":len(material_rows),"terminal_nonchemical_records":len(terminals),"terminal_identity_records":len(terminal_identity_rows),"accepted_numeric_scientific_records_created":0,"model_training_labels_created":0,"external_validation_observations_created":0,"strict_comsol_ready_records_created":0,"validation":validation,"claim_boundary":f"Accepted {len(identities)} source-local complete identities and classified {len(materials)} new material/ionic records plus {len(terminals)} nonchemical tokens. No numerical, model, external-validation, screening, or COMSOL records were created."}
    (args.output_dir/"run_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8"); (args.output_dir/"VALIDATION_REPORT.json").write_text(json.dumps(validation,ensure_ascii=False,indent=2),encoding="utf-8")
    manifest={"generated_at_utc":now(),"base_database_sha256":digest(args.base_dir/"condition_identity_linkage.sqlite"),"v12_database_sha256":digest(args.output_dir/"condition_identity_linkage.sqlite"),"rdkit_version":rdBase.rdkitVersion,"accepted_identity_count":len(accepted),"material_count":len(material_rows),"terminal_nonchemical_count":len(terminals)}; (args.output_dir/"integration_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    readme=f"# 条件—分子—配方身份数据库 v12\n\n本版本在 v11 基础上自动扩充来源内身份。接受 {len(identities)} 条可唯一对应的完整分子身份；另将 {len(materials)} 条新增盐类、商业材料或离子组分不完整记录，以及 {len(terminals)} 条非化学缩写终止分类。\n\n总来源内实体 {len(ents)}；接受单分子身份 {len(accepted)}；材料记录 {len(material_rows)}；非化学终止记录 {len(terminals)}；自动待处理身份 {remaining_entities}。本轮未生成数值真值、模型标签、外部验证观测或筛选结果。SQLite 完整性：{integrity}。\n"; (args.output_dir/"README_CN.md").write_text(readme,encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2)); return 0 if validation["valid"] else 2

if __name__=="__main__": raise SystemExit(main())
