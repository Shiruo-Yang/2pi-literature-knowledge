# Supplementary registry summary (v3.2)

This compact summary makes the knowledge-to-decision logic understandable without requiring inspection of the full repository.

| Research object | Scientific question | Registry | Items |
|---|---|---|---:|
| Sources | Where did the evidence come from? | `source_registry.csv` | 44 |
| Layer 1 — domain evaluation knowledge | What should a two-photon radical photoinitiator be evaluated on? | `domain_knowledge_registry.csv` | 25 |
| Layer 2 — endpoint and representation knowledge | What is predicted and how is the molecule represented? | `endpoint_representation_registry.csv` | 37 |
| Task-prior derivation | How was literature/rule evidence converted into the six loss weights? | `task_weight_derivation_registry.csv` | 10 |
| Implemented task weights | Which exact weights entered D06 and F06? | `task_weight_policy_registry.csv`; `task_weight_model_implementation_registry.csv` | 6 + 12 |
| Task-weight sensitivity | How did five controlled weighting policies compare? | `task_weight_sensitivity_registry.csv` | 5 |
| Role-node disclosure | Were human experts or external LLM outputs used? | `task_weight_node_disclosure_registry.csv` | 5 |
| Layer 3 — mechanistic decision knowledge | How is a candidate assigned to Type-I, Type-II or SET/PET assessment? | `mechanism_decision_registry.csv` | 25 |
| Route evidence | Which synthesis precedents inform materialisation review? | `synthesis_route_evidence_registry.csv` | 19 |
| Model evidence | What was evaluated and what remains in progress? | `model_evaluation_registry.csv` | 40 |
| Screening deployment | How was ZINC22 compressed into an auditable portfolio? | `screening_workflow_summary.csv` | 6 |
| QM evidence | What candidate-level evidence and claim ceiling resulted? | `representative_qm_evidence_registry.csv` | 21 |

The workflow yields a computationally prioritised, QM-assessed candidate portfolio. It does not establish experimental polymerisation performance.
