# Completeness, traceability and claim audit

Release: **v2.1** (2026-08-19)

## Audit result

- 44 unique DOI sources; title, year and journal metadata complete.
- 25 domain-evaluation evidence units, 25 mechanism-decision rules and 19 route-evidence units resolve to a source.
- Six targets, one graph representation and 30 trained descriptor definitions have explicit implementation/evaluation states.
- D06 and F06 have 12 frozen task-level outer-test records; 14 strict-clean comparison rows and 6 independent sigma_max evaluation rows are also retained.
- Strict-clean outer-test comparison is complete, but model replacement remains gated by pending external-validation and top-k-stability checks.
- Descriptor ablation: 6/7 scheduled experiments complete; `dense_plus_pi_family` remains running and has no final comparative claim.
- ZINC22 deployment is recorded as 9,939 candidates → 2,583 families → 21 representatives.
- Candidate-level QM evidence is recorded for all 21 decisions: 20 neutral minima passed and one SET/PET representative was excluded after geometry failure.

## Automated release checks

- No duplicate DOI records.
- No internal absolute paths or internal working labels in the public data package.
- Every scientific rule resolves to an existing source identifier.
- Every candidate has a public representative identifier, a ZINC identifier, a decision status and a claim limit.
- Running computations are reported as running, never promoted to completed results.
- Mechanism assignment, QM support and experimental validation remain separate evidence levels.
