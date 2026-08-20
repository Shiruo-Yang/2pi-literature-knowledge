# Literature-integration closure record

Release: **v3.1** (2026-08-20)

The literature-integration layer was frozen in v3.0. This v3.1 maintenance snapshot updates the completed descriptor-ablation evidence without reopening or expanding the literature corpus.

## Closure criteria

- **Citation clusters complete:** all 25 domain rules, 25 mechanism rules and 19 route records expose their full deduplicated `supporting_source_ids` and `supporting_dois` clusters.
- **Endpoint definitions submission-ready:** all six endpoints include a definition, original unit, frozen training unit, valid-label count, exact forward and inverse transformations, invalid-value handling and source mapping.
- **Route evidence interpretable:** `direct_route_precedent`, `qualified_close_analogue` and `contextual_or_analogous_support` are defined as descriptive provenance classes and are not used as scores, ranking weights or model inputs.
- **Release reproducible:** the package is rebuilt from source assets, hashed, manifested and checked by `scripts/validate_release.py`.

## Scope boundary

All seven strict-clean descriptor-ablation configurations completed on 20 August 2026. `dense_plus_pi_core` produced the lowest observed mean macro RMSE, but this sensitivity result neither establishes statistical superiority nor replaces the frozen D06/F06 deployment roles. Strict-clean retraining remains a separate sensitivity audit and does not replace the frozen endpoint definitions. The literature-integration layer remains closed.
