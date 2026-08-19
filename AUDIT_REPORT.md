# Completeness, traceability and claim audit

Release: **v3.0** (2026-08-19)

## Audit result

- 44 unique DOI sources; title, year and journal metadata complete. The formalised domain, mechanism and route registries cite 44 unique sources in total.
- 25 domain-evaluation evidence units, 25 mechanism-decision rules and 19 route-evidence units expose complete, deduplicated citation clusters. Multi-source records: 19 domain, 19 mechanism and 0 route records.
- All six targets contain a scientific definition, original unit, frozen training unit, valid-label count, exact forward and inverse transformation, invalid-value policy and source mapping.
- One graph representation and 30 descriptor definitions have explicit implementation/evaluation states.
- Route-evidence provenance classes are fully defined and are explicitly excluded from model inputs, candidate scores and ranking weights.
- D06 and F06 have 12 frozen task-level outer-test records; 14 strict-clean comparison rows and 6 independent sigma_max evaluation rows are also retained.
- Strict-clean outer-test comparison is complete, but model replacement remains gated by pending external-validation and top-k-stability checks.
- Descriptor ablation: 6/7 scheduled experiments complete; `dense_plus_pi_family` remains running and has no final comparative claim.
- ZINC22 deployment is recorded as 9,939 candidates → 2,583 families → 21 representatives.
- Candidate-level QM evidence is recorded for all 21 decisions: 20 neutral minima passed and one SET/PET representative was excluded after geometry failure.

## Automated release checks

- No duplicate DOI records.
- No internal absolute paths or internal working labels in the public data package.
- Every scientific rule resolves to an existing source identifier.
- Every domain, mechanism and route rule exposes a non-empty citation cluster without within-row DOI duplication.
- Every endpoint has all submission-required definition and transformation fields.
- Every candidate has a public representative identifier, a ZINC identifier, a decision status and a claim limit.
- Running computations are reported as running, never promoted to completed results.
- Mechanism assignment, QM support and experimental validation remain separate evidence levels.
