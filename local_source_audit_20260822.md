# Local literature/QM source audit

Date: 2026-08-22

## Purpose

The public literature package previously froze 44 DOI-level sources. A reverse audit of local structured registries, full-text extraction assets and QM comparison assets identified one additional primary paper that was genuinely used in the project but was not represented in the DOI registry: Malval et al., DOI `10.1021/cm200595y`.

This source is now registered as `SRC045` and its three evidence units are recorded in `local_source_evidence_registry.csv`.

## What was checked

- `source_registry.csv`
- `domain_knowledge_registry.csv`
- `mechanism_decision_registry.csv`
- `synthesis_route_evidence_registry.csv`
- task-weight registries and disclosure files
- local full-text extraction files (`outputs/chi2019_thioxanthone_pdf_text.txt`, `outputs/chi2019_tailored_thioxanthone_pdf_text.txt`)
- local QM comparison assets under `tpp_qm_validation/` and `rules/Gaussian/`
- the local Zotero parse manifest at `outputs/zotero_local_pdf_texts_20260630/zotero_local_pdf_parse_manifest.csv`

The raw DOI occurrence scan found 150 DOI-like strings across the workspace. This number is not a source count: many are reference-list citations, malformed legacy tokens, or incidental mentions in copied PDFs. They were not promoted automatically. A DOI was promoted only when a source was connected to a structured evidence object, a full-text extraction asset, a QM comparison asset, or the frozen task-weight/decision workflow.

The Zotero parse manifest contains 345 parsed local PDFs. The sanitized public inventory is `local_pdf_source_inventory.csv`: 4 records overlap the structured public registry and 341 remain explicitly marked `raw_text_only`. This distinction is intentional. Parsing a PDF is not the same as assigning a scientific evidence unit, mechanism rule or model input. The 341 raw-text records must not be described in the manuscript as already learned or structured evidence until they are independently reviewed and linked to downstream computational use.

## Newly frozen source

**SRC045** — Malval et al., “Enhancement of the Two-Photon Initiating Efficiency of a Thioxanthone Derivative through a Chevron-Shaped Architecture.” *Chemistry of Materials* 2011, 23, 3411–3420. DOI: `10.1021/cm200595y`.

The local extracted text confirms:

1. ANTX is an anthracene–thioxanthone hybrid with a chevron-shaped architecture.
2. The study jointly considers 2PA, free-radical initiation, polymerisation and 3D microfabrication.
3. MDEA is used as a hydrogen donor; H-transfer generates α-aminoalkyl radicals that add to acrylate double bonds.

These facts are separated into Layer 1 task-prior input, Layer 2 family/topology representation and Layer 3 Type-II mechanism routing. The original paper is not credited with defining the project's six-task weights or Chemprop descriptors.

## Scope boundary

The 150-string scan is retained as an audit artifact at `outputs/local_all_dois_20260822.txt`. It must not be presented as 150 validated source papers. The formal evidence source pool is now 45 DOI records; all other DOI-like strings remain unpromoted until they are linked to a verified evidence object or full-text/QM asset.
