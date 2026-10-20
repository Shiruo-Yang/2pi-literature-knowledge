# Source traceability and field-use assessments

This is the source-location maintenance layer for the current [manuscript-aligned scientific database](../data/research), whose evidence index and scalar candidates carry the restrictions described here. See [RESEARCH_DATABASE.md](RESEARCH_DATABASE.md) for the public scientific entry points.

Updated 2026-10-20. The base database and raw evidence remain byte-for-byte unchanged. The current entry point is `scripts/open_literature_database.py`, which joins the base to the overlay in memory and enables read-only mode. It retains all 9,257 records and exposes both original information and new assessments. Read `component_use_action`, `numeric_use_status` and `external_evidence_use` before downstream reuse; the view does not delete rows or supply a ready-made training set.

## Scope and outcome

The batch covers the union of 1,399 missing-page records and 122 broad geometry/wavelength warnings: 1,496 distinct records from 58 source identifiers. These are identifiers within the selected corpus, not an independently deduplicated paper count.

| Outcome | All targeted records | Previously missing page |
|---|---:|---:|
| Unique publisher-XML node span, source DOI confirmed | 772 | 772 |
| Unique cached PDF anchor span | 334 | 245 |
| No exact anchor match | 108 | 108 |
| Multiple exact anchor matches | 282 | 274 |

The 334 cached PDF locations are provisional until checked against original PDF extraction and document identity. Only 320 meet that additional requirement; all 245 previously missing-page PDF locations are among these. The effective result is therefore **1,092 source-verified anchor locations**, including **1,017 newly supplied locations**. Fourteen other unique cached locations remain provisional, and 382 originally missing-page records remain unresolved. No first-match selection is used to hide ambiguities.

## Location methods

- Source selection uses the preserved extraction metadata and exact source identifier; it does not search by approximate titles.
- XML parsing reproduces the archived extraction order for article-title, title, paragraph, caption and table-cell elements. Positional node addresses identify the first and last contributing elements. A unique match can span several nodes. Repeated or nested text can yield several matches, which remain unresolved rather than being silently collapsed.
- PDF matching first uses the archived page-separated text. Original PDFs are also read with the existing pypdf environment and with LiteParse 2.0.0, without OCR. An effective PDF location requires a unique same-page-span match in the direct pypdf extraction, an exact recorded DOI found in the first two source pages, and no contradictory unique LiteParse page match. pypdf re-extraction is a source reproducibility check, not an independent measurement or independent parser implementation. LiteParse corroboration is separately reported.
- Source verification for XML requires the recorded DOI in original article metadata. PDF or XML file hashes bind the location to a specific local source file. Fifty-six original files were hashed; two targets could only reuse cached text and did not gain original-source verification. Seven source identifiers did not pass the DOI-binding requirement and their page matches are not promoted.
- Matching normalizes Unicode compatibility forms, letter case and whitespace and removes cached page-marker strings. Punctuation and numbers are not replaced. Anchors shorter than 60 normalized characters are not accepted. Start/end offsets refer to the concatenated normalized extraction text, not PDF coordinates or original byte offsets.
- PDF page numbers are one-based file pages, not printed journal page numbers. XML locations are node addresses, not page numbers. The original `page_hint` is never rewritten.

The 1,017 newly located records have source-verified provenance, not automatically valid numerical values. Their compounds, endpoints, units, experimental conditions and primary-experiment ownership still require their own evidence.

## Field validity and use decisions

The 122 existing context warnings were checked with a narrow same-number rule. Four records place `wavelength_nm=250` in context strings whose original page describes line widths of about 250 nm. Assistant inspection of Pucher et al., DOI `10.1021/ma9007785`, PDF page 9 / printed page 6527 supports withholding that component. The four retained records are listed in `configs/literature_field_use_decisions.json`; their original values and other context fields remain unchanged. The original PDF hash and private rendered-page hash are recorded. The screenshot stays local. This is assistant source-image inspection, not a claim of human-author review.

The other 118 broad warnings remain warnings. They have not been established as correct or erroneous by the narrow rule.

Literal scalar checking additionally flags 33 targeted records whose stored single scalar cannot be found literally in its attached anchor. This check does not equate alternate numeric spellings or infer values from figures, so absence is a reason to withhold numerical reuse pending review, not proof the number is wrong. The other 1,286 scalar-presence matches do not certify the endpoint; 177 records are nonscalar or empty and are not assessed by this check.

One record, `UKB-a6c8d717e10cbd5fa3cc`, carries original page hint 6, whereas its anchor is uniquely reproduced on PDF page 1 of DOI `10.1038/lsa.2016.133`. Its scalar is also absent from that anchor. Both the original hint and recovered anchor location remain visible; locating the abstract does not recover the claimed value or justify moving that value to page 1.

## Overlay fields

| Field | Meaning |
|---|---|
| `evidence_id`, `paper_id` | Exact preserved record ID and source identifier |
| `original_page_hint` | Unchanged previous hint |
| `locator_status`, `match_count` | Raw anchor-match result, separate from original-source verification |
| `locator_type`, `locator_start`, `locator_end` | PDF file page range or XML positional node range |
| `normalized_start`, `normalized_end` | Zero-based start and exclusive end in normalized concatenated text |
| `source_sha256`, `anchor_sha256` | Original file and preserved anchor fingerprints |
| `method` | XML-node or cached/direct PDF-page matching method |
| `secondary_parser_check` | LiteParse corroboration, non-reproduction or primary ambiguity; non-reproduction is not a proved contradiction |
| `original_pdf_recheck` | Whether direct pypdf extraction independently reproduces the archived page location |
| `source_binding`, `evidence_metadata_doi_agrees` | DOI observation in the original file and agreement with the evidence row |
| `effective_locator_status` | Location accepted for provenance use or left provisional/unresolved |
| `original_page_relation` | Original hint within/outside recovered anchor span, or not comparable |
| `scalar_anchor_check` | Literal scalar present, not found, or not applicable; never a measurement certificate |
| `semantic_assessment`, `action` | Broad-context warning or narrow geometry conflict and proposed use restriction |
| `replacement_value`, `replacement_field` | Empty: no numerical correction or endpoint reassignment is made |

The overlay SQLite, CSV tables, summary and manifest are under `data/literature/traceability`. Field-use decisions are explicit JSON under `configs`, separate from automatic diagnostics. The complete source text and private file paths are excluded from public exports.

## Reproduce and inspect

The builder uses the existing Python 3.11 environment with LiteParse and an existing pypdf Python environment. Supply actual local paths; no environment installation or network call is performed by the workflow:

```sh
python scripts/improve_literature_traceability.py --base data/literature/literature.sqlite --archive PRIVATE_ARCHIVE/literature.sqlite --workspace ORIGINAL_WORKSPACE --output NEW_PUBLIC_STAGING --private-output NEW_PRIVATE_STAGING --pdf-python EXISTING_PYPDF_PYTHON
python scripts/verify_literature_traceability.py --folder NEW_PUBLIC_STAGING --private NEW_PRIVATE_STAGING --base data/literature/literature.sqlite --archive PRIVATE_ARCHIVE/literature.sqlite
```

The independent verifier does not import the builder. It reconstructs XML node addresses, rechecks source/cache hashes, confirms all anchor matches and offsets, tests original PDF page-span agreement, checks literal-value flags and table mirrors, and verifies that the base database is unchanged. Nine matching tests and seven current-view tests cover ambiguities, cross-page spans, scalar boundaries, preserved rows and read-only access.

Public query example (standard library only):

```python
from pathlib import Path
from scripts.open_literature_database import connect
db = connect(Path.cwd())
rows = db.execute("""
    SELECT evidence_id, doi, page_hint,
           recovered_locator_type, recovered_locator_start, recovered_locator_end,
           component_use_action, numeric_use_status
    FROM current_evidence
    WHERE effective_location_status = 'source_verified_location_only'
""").fetchall()
```

Original flags remain historical facts. Read the current view to see new provenance and use restrictions together; do not interpret a smaller unresolved-location queue as a new count of validated measurements.
