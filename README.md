# Evidence-to-decision framework for two-photon radical photoinitiator prioritisation

This repository documents how literature-derived photoinitiator knowledge was converted into model inputs, decision rules and mechanism-matched validation questions. The objective is not to rank molecules by two-photon response alone, but to distinguish optically favourable predictions from candidates that remain defensible after reliability, chemical-role and mechanism checks.

Release: **v3.2** · Snapshot: **2026-08-20**

## At a glance

| Question | What this study did |
|---|---|
| What is the scientific bottleneck? | High predicted two-photon response does not by itself establish radical-generation competence, formulation suitability or reliable extrapolation to a new scaffold. |
| What is the design principle? | Prediction, reliability assessment, mechanism admissibility, portfolio construction and physicochemical assessment are treated as separate evidence layers and connected only at the candidate-decision stage. |
| What was built? | Three traceable knowledge layers, an auditable literature-prior task-weight policy, two six-task molecular models with distinct roles, reliability/risk controls, a lane-specific ZINC22 deployment and mechanism-matched QM evidence tiers. |
| What is the final output? | A 21-representative, QM-assessed candidate portfolio spanning Type-I, Type-II and SET/PET hypotheses. |
| What is not claimed? | The portfolio is not a set of experimentally validated photoinitiators, and the mechanism assignments are not experimental mechanism proofs. |

```mermaid
flowchart LR
    S[44-DOI source pool] --> E[Evidence units with complete citation clusters]
    E --> L1[Layer 1: domain evaluation knowledge]
    L1 --> L2[Layer 2: endpoints and molecular representations]
    L2 --> W[Audited six-task utility prior]
    W --> M[D06 primary model and F06 diagnostic model]
    M --> R[Reliability and risk controls]
    R --> Z[ZINC22: 9,939 candidates]
    Z --> F[2,583 lane-specific families]
    F --> L3[Layer 3: mechanism decisions]
    L3 --> P[21 representatives]
    P --> Q[Lane-matched QM evidence tiers]
```

## The three knowledge layers

The layer labels describe scientific functions, not internal project stages.

### Layer 1 — Domain evaluation knowledge: what should be evaluated?

Literature evidence is represented as individual evidence units rather than merged into a sparse, all-purpose molecular database. Each unit records its source, supported statement, normalized criterion, downstream computational use and claim limit.

- Covers optical response, photochemical role, initiating family, coinitiator dependence, formulation-related considerations and explicit boundary cases.
- The source pool contains 44 unique DOIs; the formalised rule registries use the source subsets and citation clusters recorded for each evidence unit rather than implying that every source generated every rule.
- Each rule exposes a primary source for readability and a complete, deduplicated citation cluster for verification.
- Keeps 19 synthesis-route precedents in a separate registry so route plausibility is not confused with mechanistic evidence or experimental synthesis validation.
- Determines which quantities enter the six-task profile and which chemical roles require admission, exclusion or further review.

Primary records: [`source_registry.csv`](source_registry.csv), [`domain_knowledge_registry.csv`](domain_knowledge_registry.csv), and [`synthesis_route_evidence_registry.csv`](synthesis_route_evidence_registry.csv).

### Layer 2 — Endpoint and representation knowledge: what is predicted and how is a molecule represented?

The project defines a six-task predictive profile comprising `sigma_780`, `sigma_max`, toxicity, solubility, synthetic accessibility and an intersystem-crossing-related energy proxy. These outputs are candidate-profile proxies; they are not direct measurements of photopolymerisation performance.

| Endpoint | Raw unit/scale | Valid labels | Frozen target transform |
|---|---|---:|---|
| `sigma_780` | GM | 209,162 | affine-standardised `log10(1 + y)` |
| `sigma_max` | GM | 209,162 | affine-standardised `log10(1 + y)` |
| toxicity | dimensionless dataset score | 209,162 | affine-standardised identity |
| solubility | µg mL−1 | 127,943 | affine-standardised `log10(1 + y)` |
| synthetic accessibility | dimensionless local 0–1 score | 209,162 | affine-standardised identity |
| `isc_energy` | eV | 129,671 | affine-standardised identity |

Exact forward/inverse formulae, invalid-value handling and source-field mappings are provided in [`endpoint_representation_registry.csv`](endpoint_representation_registry.csv). These definitions describe the frozen deployment assets; strict-clean retraining is reported separately as a sensitivity audit.

- Both final models use the molecular graph and 11 dense RDKit descriptors.
- D06 is the primary predictive model.
- F06 adds 11 photoinitiator-family/topology descriptors and is used as a family-sensitive diagnostic view; D06/F06 disagreement is a reliability signal, not an equal-weight ensemble vote.
- Eight sparse PI-core descriptors are retained in the controlled ablation study but are not inputs to the frozen D06/F06 deployment models.
- The registry distinguishes implementation status from ablation status: all seven five-fold comparisons are complete, but the frozen D06/F06 deployment roles remain unchanged.

Primary records: [`endpoint_representation_registry.csv`](endpoint_representation_registry.csv) and [`model_evaluation_registry.csv`](model_evaluation_registry.csv).

### Training-policy bridge — how were the six task losses balanced?

The six losses used a literature-informed, rule-structured utility prior. A targeted 34-paper weighting corpus informed an 11-field competition set; four deterministic role-isolated templates and a rule-based adjudication produced seven weighted-core indicators. `absorption_range` remained a rule-layer spectral-window criterion, and the other six indicator weights were renormalised for Chemprop.

| Task | Unit-sum weight | Chemprop mean-one weight |
|---|---:|---:|
| `sigma_780` | 0.134404 | 0.806421 |
| `sigma_max` | 0.144641 | 0.867845 |
| toxicity | 0.176176 | 1.057055 |
| solubility | 0.186038 | 1.116228 |
| synthetic accessibility | 0.202641 | 1.215843 |
| `isc_energy` | 0.156101 | 0.936609 |

All 12 model–task values match the archived final D06/F06 training specifications. A five-scheme controlled audit found that equal weighting had the lowest observed inner-CV macro RMSE (0.260143) and the deployed literature prior gave 0.262932. The prior is therefore an explicit deployment-utility policy, not a performance optimum. The archived LLM-compatible branch used deterministic fallback for all four role nodes and the adjudicator; no external LLM-generated role score was used.

Primary records: [`TASK_WEIGHT_POLICY.md`](TASK_WEIGHT_POLICY.md), [`task_weight_derivation_registry.csv`](task_weight_derivation_registry.csv), [`task_weight_policy_registry.csv`](task_weight_policy_registry.csv), [`task_weight_model_implementation_registry.csv`](task_weight_model_implementation_registry.csv), [`task_weight_sensitivity_registry.csv`](task_weight_sensitivity_registry.csv) and [`task_weight_node_disclosure_registry.csv`](task_weight_node_disclosure_registry.csv).

### Layer 3 — Mechanistic decision knowledge: how is a candidate routed and assessed?

Literature-derived rules separate candidates into Type-I, Type-II and SET/PET lanes before higher-cost calculations are interpreted.

- Type-I asks whether a chemically meaningful initiating bond supports a cleavage hypothesis.
- Type-II requires an explicit coinitiator or hydrogen-donor/electron-transfer context.
- SET/PET requires donor/acceptor assignment, redox inputs and excited-state localization review.
- Positive, boundary and excluded cases retain different claim ceilings rather than being forced into one global score.
- The final QM registry records candidate-specific evidence, decision status and the strongest allowed interpretation.

Primary records: [`mechanism_decision_registry.csv`](mechanism_decision_registry.csv) and [`representative_qm_evidence_registry.csv`](representative_qm_evidence_registry.csv).

Route evidence uses three defined provenance classes: `direct_route_precedent`, `qualified_close_analogue` and `contextual_or_analogous_support`. The classes support route-plausibility review only and are never used as model inputs or ranking weights.

## What the full study completed

1. Formalised literature evidence into source-linked domain, representation, mechanism and route objects.
2. Converted a literature/rule prior into an explicit six-task utility-weight vector, verified its use in D06/F06 and audited five alternative weighting schemes.
3. Constructed D06 and F06 six-task models and evaluated them on scaffold-disjoint outer tests.
4. Audited reliability through simpler comparisons, strict-clean retraining analysis, independent `sigma_max` evidence, applicability-domain tiers and D06/F06 disagreement.
5. Applied the frozen decision framework to a role-aware ZINC22 candidate space instead of treating the database as a single optical leaderboard.
6. Compressed 9,939 candidates into 2,583 lane-specific families and then 21 representatives: seven per mechanism lane, including primary, novelty and boundary/control roles.
7. Assigned mechanism-matched QM evidence tiers: 20 representatives reached normal neutral minima, one SET/PET representative was excluded after geometry failure, and the surviving cases retained lane-specific claim ceilings.

## Distinct contributions

### 1. Literature knowledge made computationally actionable

The contribution is not the collection of papers itself. It is the traceable conversion of heterogeneous evidence into evaluation criteria, endpoint/descriptor definitions, mechanism rules, boundary cases and route-specific downstream uses.

### 2. Reliability and mechanism jointly control candidate decisions

Predicted scores are not treated as sufficient evidence. Scaffold-disjoint evaluation, independent optical evidence, applicability-domain status, D06/F06 disagreement, family diversity and mechanism admissibility are preserved as separate decision signals.

### 3. Mechanism-matched routing connects screening to QM assessment

Candidates are not sent through one generic QM checklist. Type-I, Type-II and SET/PET hypotheses receive different physicochemical questions, and their outcomes are reported as evidence tiers that can support, retain as exploratory or exclude a candidate.

### What supports the contributions but is not claimed as a standalone innovation

- Use of ZINC22 and the number of screened molecules.
- Use of Chemprop, graph neural networks, RDKit descriptors or QM calculations by themselves.
- The six task-weight numbers by themselves; they are an explicit and audited implementation policy, not a performance-optimised discovery claim.
- A single global multi-property score.
- Experimentally validated photopolymerisation performance.

## Evidence and current status

| Component | Evidence available | Current interpretation |
|---|---|---|
| Literature evidence | 44 unique DOI sources with complete title/year/journal metadata | Existing knowledge organised by evidence unit and computational role |
| Frozen models | D06/F06 task-level outer tests and independent `sigma_max` evaluation | D06 is primary; F06 disagreement is diagnostic |
| Task-weight policy | Complete derivation, six exact weights, 12 model-task configuration matches, five sensitivity schemes and five deterministic-fallback disclosures | Implemented utility prior; equal weighting had slightly lower inner-CV macro RMSE, so no performance-optimality claim |
| Strict-clean re-evaluation | Six-task outer-test comparison complete; replacement gate remains open | Sensitivity/retraining audit, not a replacement deployment model |
| Descriptor ablation | 7 of 7 scheduled five-fold experiments complete; validation-set hashes matched in all 35 fold/configuration checks | `dense_plus_pi_core` had the lowest observed macro RMSE (0.284826 ± 0.055743); this does not replace D06/F06 or establish statistical superiority |
| ZINC22 application | 9,939 candidates → 2,583 families → 21 representatives | Lane-specific portfolio construction, not a cross-lane leaderboard |
| QM assessment | 20 neutral minima passed; one geometry-failed exclusion; lane-specific evidence tiers assigned | Minimal computational closure with conservative claim ceilings |

## Five-minute verification path

1. Read the three layers and contributions above.
2. Inspect five complete source-to-use chains in [`examples/evidence_to_computational_use_examples.csv`](examples/evidence_to_computational_use_examples.csv).
3. Map manuscript concepts to repository evidence using [`manuscript_repository_crosswalk.csv`](manuscript_repository_crosswalk.csv).
4. Check row counts, pending items and claim boundaries in [`AUDIT_REPORT.md`](AUDIT_REPORT.md) and [`completeness_summary.csv`](completeness_summary.csv).

## Repository map

| File | What can be verified |
|---|---|
| [`source_registry.csv`](source_registry.csv) | DOI, title, year, journal and evidence use |
| [`domain_knowledge_registry.csv`](domain_knowledge_registry.csv) | source → evidence → normalized evaluation criterion → downstream use |
| [`endpoint_representation_registry.csv`](endpoint_representation_registry.csv) | six endpoints, graph representation and descriptor implementation/evaluation status |
| [`TASK_WEIGHT_POLICY.md`](TASK_WEIGHT_POLICY.md) | human-readable derivation, implementation, sensitivity and disclosure summary |
| [`task_weight_derivation_registry.csv`](task_weight_derivation_registry.csv) | complete evidence-to-six-weight transformation chain |
| [`task_weight_policy_registry.csv`](task_weight_policy_registry.csv) | exact six-task and Chemprop-scaled weights with D06/F06 matches |
| [`task_weight_model_implementation_registry.csv`](task_weight_model_implementation_registry.csv) | 12 task-by-model archived configuration checks |
| [`task_weight_sensitivity_registry.csv`](task_weight_sensitivity_registry.csv) | five completed grouped-scaffold weighting schemes |
| [`task_weight_node_disclosure_registry.csv`](task_weight_node_disclosure_registry.csv) | deterministic fallback, prompt hashes and no-external-LLM boundary |
| [`mechanism_decision_registry.csv`](mechanism_decision_registry.csv) | Type-I/Type-II/SET-PET routing, context and claim limits |
| [`synthesis_route_evidence_registry.csv`](synthesis_route_evidence_registry.csv) | route precedent kept separate from mechanism evidence |
| [`model_evaluation_registry.csv`](model_evaluation_registry.csv) | frozen outer tests, strict-clean comparison, external optical evidence and descriptor ablation |
| [`screening_workflow_summary.csv`](screening_workflow_summary.csv) | ZINC22 deployment, family compression, representative selection and novelty QC |
| [`representative_qm_evidence_registry.csv`](representative_qm_evidence_registry.csv) | 21 representatives, QM evidence tiers, decisions and candidate-specific limits |
| [`LITERATURE_INTEGRATION_CLOSURE.md`](LITERATURE_INTEGRATION_CLOSURE.md) | Frozen literature-curation criteria and the v3.2 evidence-maintenance boundary |

## Interpretation boundary

The supported repository-level claim is a **literature-grounded, reliability-audited and mechanism-constrained computational prioritisation workflow** that produces a **QM-assessed candidate portfolio**. Experimental polymerisation, printing and formulation validation remain a separate evidence layer.

## Versioning and validation

`VERSION`, `package_manifest.json` and `checksums.sha256` freeze this snapshot. Run `python scripts/validate_release.py` from the repository root to verify checksums and screen the public files for absolute local paths or internal working labels.
