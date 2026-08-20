# Completeness, traceability and claim audit

Release: **v3.2** (2026-08-20)

## Audit result

- 44 unique DOI sources; title, year and journal metadata complete. The formalised domain, mechanism and route registries cite 44 unique sources in total.
- 25 domain-evaluation evidence units, 25 mechanism-decision rules and 19 route-evidence units expose complete, deduplicated citation clusters. Multi-source records: 19 domain, 19 mechanism and 0 route records.
- All six targets contain a scientific definition, original unit, frozen training unit, valid-label count, exact forward and inverse transformation, invalid-value policy and source mapping.
- One graph representation and 30 descriptor definitions have explicit implementation/evaluation states.
- The complete task-prior chain is exposed as 10 derivation stages, six task-weight rows, 12 D06/F06 implementation rows, five completed sensitivity schemes and five node-level fallback disclosures.
- The unit-sum MT6 vector and Chemprop mean-one vector are algebraically equivalent; all six values match both final D06 and F06 training specifications.
- Equal weighting had the lowest observed five-fold inner-CV macro RMSE (0.260143) versus 0.262932 for the deployed literature prior. The prior is therefore reported as a utility policy, not a predictive optimum.
- All four role nodes and the integrative adjudicator used deterministic fallback; no external LLM-generated role score was used.
- Route-evidence provenance classes are fully defined and are explicitly excluded from model inputs, candidate scores and ranking weights.
- D06 and F06 have 12 frozen task-level outer-test records; 14 strict-clean comparison rows and 6 independent sigma_max evaluation rows are also retained.
- Strict-clean outer-test comparison is complete, but model replacement remains gated by pending external-validation and top-k-stability checks.
- Descriptor ablation: 7/7 scheduled experiments complete; all 35 fold/configuration combinations used matching validation splits. `dense_plus_pi_core` had the lowest observed fold-mean macro RMSE (0.284826; Δ=-0.003729 versus graph-only; 1.29% relative reduction).
- ZINC22 deployment is recorded as 9,939 candidates → 2,583 families → 21 representatives.
- Candidate-level QM evidence is recorded for all 21 decisions: 20 neutral minima passed and one SET/PET representative was excluded after geometry failure.

## Automated release checks

- No duplicate DOI records.
- No internal absolute paths or internal working labels in the public data package.
- Every scientific rule resolves to an existing source identifier.
- Every domain, mechanism and route rule exposes a non-empty citation cluster without within-row DOI duplication.
- Every endpoint has all submission-required definition and transformation fields.
- Task weights sum to one, Chemprop-scaled weights sum to six, implementation rows match the archived D06/F06 specifications and all five sensitivity schemes contain five completed folds.
- Every task-prior node records fallback status, prompt hashes and the no-human/no-external-LLM claim boundary.
- Every candidate has a public representative identifier, a ZINC identifier, a decision status and a claim limit.
- Completed and pending computations are reported separately; the completed ablation result does not change the frozen deployment roles.
- Mechanism assignment, QM support and experimental validation remain separate evidence levels.
