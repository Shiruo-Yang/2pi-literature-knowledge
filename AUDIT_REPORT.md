# Registry completeness and traceability audit

Release: **v1.0** (2026-08-19)

| Registry | Rows | DOI/source coverage | Computational-use coverage | Pending |
|---|---:|---:|---:|---:|
| Sources | 45 | 45/45 DOI | n/a | 16 DOI-only title records |
| Layer 1 domain knowledge | 44 | 44/44 | 44/44 | 18 source titles |
| Layer 2 endpoint/representation | 37 | explicit where available | 37/37 | 9 literature mappings |
| Layer 3 mechanism knowledge | 44 | 44/44 | 44/44 | 18 source titles |
| Candidate/QM map | 16 | n/a | 16/16 routed | 16 unconsolidated result rows |

## Reproducibility checks

- Every Layer 1 and Layer 3 row resolves to a valid `source_id`.
- Every Layer 1, Layer 2, Layer 3, and candidate/QM row records its computational use or route.
- D06/F06 descriptor scope is checked against final feature-table headers.
- Missing source titles and endpoint-level literature mappings remain explicit pending states.
- Numerical evidence retains `text_exact`, `origin_digitized`, or `model_inferred` provenance.
- Mechanism rules and candidate-level QM results remain separate evidence objects.
