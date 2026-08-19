# C1 — role-structured literature knowledge for 2PI discovery

**C1 formalises heterogeneous photoinitiator literature into traceable domain criteria, endpoint/representation definitions, and mechanism-control rules consumed by the computational workflow.**

Release: **v1.0** · Frozen: **2026-08-19**

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

## Completeness at v1.0

| Object | Count | Key status |
|---|---:|---|
| Sources | 45 | 45 DOI-linked; 29 citation-ready; 16 DOI-only title records pending |
| Layer 1 evidence units | 44 | all linked to a source and computational use |
| Layer 2 items | 37 | 29 implemented in frozen D06/F06 assets; 8 sparse descriptors are in active training and await final result freeze |
| Layer 3 rules | 44 | all linked to mechanism routing and a claim limit |
| Candidate/QM mappings | 16 | routes recorded; numerical result consolidation remains a separate asset |

## Interpretation boundary

This is a role-structured evidence registry, not a homogeneous molecular database. A paper contributes only the evidence it contains. Missing values remain missing. Six-task outputs are predictive proxies, mechanism rules define admissibility rather than proof, and candidate-level QM numbers are kept outside the rule registries.

## Paper and repository crosswalk

The compact manuscript-facing summary is [`SUPPLEMENTARY_REGISTRY_SUMMARY.md`](SUPPLEMENTARY_REGISTRY_SUMMARY.md). The exact Methods-to-registry mapping is [`methods_c1_crosswalk.csv`](methods_c1_crosswalk.csv).

## Rebuild and verification

The builder is included for provenance. Rebuilding requires the parent computational-project source assets listed in [`package_manifest.json`](package_manifest.json); those large upstream assets are not duplicated in this standalone evidence release. Release hashes are recorded in [`checksums.sha256`](checksums.sha256).
