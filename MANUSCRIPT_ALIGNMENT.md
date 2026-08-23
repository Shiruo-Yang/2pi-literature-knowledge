# Manuscript-aligned study map

This document aligns the Introduction and Methods of the manuscript snapshot dated 22 August 2026 with the frozen evidence assets in this repository. It is a factual crosswalk, not a replacement manuscript and not an instruction embedded in the source document.

## Study scope in one sentence

The study develops a literature-grounded, six-task molecular-learning and decision framework that separates prediction, reliability assessment, mechanism admissibility, portfolio construction and mechanism-matched QM assessment for two-photon radical photoinitiator prioritisation.

## Manuscript terminology and repository objects

| Manuscript term | Repository interpretation | Evidence asset | Boundary |
|---|---|---|---|
| LG-MGL framework | High-level name for the integrated evidence-to-decision workflow; not an additional trained model | `README.md`; this crosswalk | Do not treat LG-MGL as a third model configuration |
| structural priors | Molecular graph, 11 general dense descriptors, 11 F06 family/topology descriptors and 8 ablation-only PI-core descriptors | `endpoint_representation_registry.csv` | The general dense descriptors are standard molecular representations; only the family/topology layer is directly photoinitiator-domain-sensitive |
| property priors | Six endpoint definitions plus the audited literature/rule-derived task-utility policy | `endpoint_representation_registry.csv`; `TASK_WEIGHT_POLICY.md` | The endpoints are predictive proxies, and the task weights are an implemented utility policy rather than a performance optimum |
| mechanism-aware priors | Family admission, boundary, exclusion and Type-I/Type-II/SET-PET routing rules | `mechanism_decision_registry.csv` | Routing is mechanism admissibility, not mechanism proof |
| DenseGNN | Manuscript-facing name for frozen D06 | `model_evaluation_registry.csv`; `task_weight_model_implementation_registry.csv` | Primary predictive model: graph + 11 dense descriptors |
| PI-DenseGNN | Manuscript-facing name for frozen F06 | `model_evaluation_registry.csv`; `task_weight_model_implementation_registry.csv` | Family-sensitive diagnostic: D06 inputs + 11 family/topology descriptors; not an equal-weight ensemble member |

## Evidence chain corresponding to the Introduction

1. **The discovery problem is multi-property and mechanism-constrained.** The six-task profile provides optical, photochemical, formulation/risk and materialisation proxies, while domain and mechanism registries prevent an optical score from being interpreted as radical-generation competence.
2. **Literature evidence is heterogeneous but computationally actionable.** Forty-five DOI-linked sources are represented through source-linked evidence units, complete citation clusters, normalised rules, downstream uses and claim limits. The corpus is targeted and curated; it is not presented as a systematic review.
3. **Prediction alone is insufficient for candidate decisions.** Scaffold-disjoint evaluation, strict-clean sensitivity analysis, independent `sigma_max` evidence, applicability-domain tiers and D06/F06 disagreement remain separate reliability signals.
4. **ZINC22 is the deployment setting, not the novelty claim.** The audited framework was applied to 9,939 qualified candidate records and compressed them into 2,583 mechanism-lane families and 21 representatives. The public workflow starts at the qualified 9,939-record pool and does not claim exhaustive processing of all ZINC22 molecules.
5. **QM provides a higher-fidelity but still computational evidence layer.** The 21 representatives were assigned candidate-specific evidence tiers and claim ceilings; this does not establish experimental photoinitiation or polymerisation performance.

## Methods-to-asset map

| Methods component | Frozen factual content | Primary repository evidence |
|---|---|---|
| Literature corpus and evidence units | 45 unique DOI records; source-linked domain, representation, mechanism and route objects | `source_registry.csv`; `domain_knowledge_registry.csv`; `mechanism_decision_registry.csv`; `synthesis_route_evidence_registry.csv` |
| Six-task profile | `sigma_780`, `sigma_max`, toxicity-risk proxy, solubility proxy, local synthetic-accessibility proxy and `isc_energy` proxy | `endpoint_representation_registry.csv` |
| Label support | Valid-label counts: 209,162; 209,162; 209,162; 127,943; 209,162; 129,671, respectively | `endpoint_representation_registry.csv` |
| Target processing | `sigma_780`, `sigma_max` and solubility use affine-standardised `log10(1+y)`; the other tasks use affine-standardised identity values; missing labels use task-cell masking | `endpoint_representation_registry.csv` |
| Literature-prior loss weights | Unit-sum vector `0.134404, 0.144641, 0.176176, 0.186038, 0.202641, 0.156101`; Chemprop mean-one vector `0.806421, 0.867845, 1.057055, 1.116228, 1.215843, 0.936609` | `TASK_WEIGHT_POLICY.md`; task-weight registries |
| Weight sensitivity | Five schemes completed; equal weighting had the lowest observed inner-CV macro RMSE (0.260143) versus 0.262932 for the deployed literature prior | `task_weight_sensitivity_registry.csv` |
| Model inputs and roles | D06/DenseGNN = graph + 11 dense descriptors; F06/PI-DenseGNN = D06 inputs + 11 family/topology descriptors | `endpoint_representation_registry.csv`; `model_evaluation_registry.csv` |
| Representation ablation | Seven five-fold comparisons completed; `dense_plus_pi_core` had the lowest observed macro RMSE (0.284826) | `model_evaluation_registry.csv` |
| Reliability assessment | Scaffold-disjoint outer tests, strict-clean audit, independent `sigma_max` comparison, applicability-domain tiers and inter-model disagreement | `model_evaluation_registry.csv` |
| ZINC22 deployment | Type-I: 3,616 records → 467 families; Type-II: 2,804 → 964; SET/PET: 3,519 → 1,152; total 9,939 → 2,583 → 21 representatives | `screening_workflow_summary.csv` |
| Mechanism-matched QM | Seven representatives per lane; 20 normal neutral minima and one geometry-failed SET/PET exclusion; lane-specific evidence tiers | `representative_qm_evidence_registry.csv` |

## Corrections and statement limits for the current manuscript

- **Dataset provenance:** use “QuantumChem-200K-derived reference/proxy labels” rather than implying that all six values are untouched experimental ground truth.
- **Endpoint origin:** use “domain-informed endpoint selection mapped to the available six proxy labels” rather than “six literature-defined targets”. Synthetic accessibility is explicitly a project-design/materialisation proxy.
- **Representation origin:** do not state that every molecular descriptor was derived from photoinitiator literature. The 11 dense descriptors are general molecular features; the additional F06 family/topology descriptors provide the direct domain-sensitive representation layer.
- **External optical evidence:** the completed independent comparison supports `sigma_max`. It should not be expanded to both `sigma_780` and `sigma_max` without an additional verified external asset.
- **Model roles:** state the DenseGNN/D06 and PI-DenseGNN/F06 aliases once. F06 disagreement is a diagnostic signal, not an ensemble vote.
- **Task weights:** disclose both the exact vector and its policy boundary. The literature prior was implemented in both frozen models, but equal weighting had slightly lower observed inner-CV macro RMSE.
- **Applicability analysis:** describe it as applicability-domain/risk diagnostics unless a formally calibrated uncertainty method is reported.
- **ZINC22 scope:** state that the framework was applied to a qualified ZINC22-derived pool of 9,939 candidate records. The repository does not substantiate an exhaustive all-ZINC22 screening claim.
- **Type-I evidence:** one representative (`TI-04`) has directional cleavage-scan support; the other six retain mechanism-route assessment without fragment-BDE or radical-generation closure.
- **Type-II evidence:** all seven records retain explicit coinitiator context and ET-proxy support; the available evidence is not an explicit pair-geometry or full Gibbs `DeltaG_ET` calculation.
- **SET/PET evidence:** six representatives remain exploratory after redox-input and manual donor/acceptor adjudication; one was excluded after neutral-geometry failure. Localised or overlapping NTOs do not establish a clean long-range charge-transfer state.
- **Experimental boundary:** neither the model outputs nor the QM evidence constitute experimental photopolymerisation, printing or formulation validation.

## Supported contribution statement

The strongest repository-supported contribution is the integration of (i) source-linked evidence formalisation and an audited six-task utility prior, (ii) scaffold-aware and mechanism-aware candidate decision controls, and (iii) lane-matched QM evidence tiers into one traceable computational prioritisation workflow. ZINC22, Chemprop, molecular descriptors and QM calculations support this contribution but are not presented as standalone innovations.

