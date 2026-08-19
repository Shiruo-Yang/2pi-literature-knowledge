# Literature-integration closure record

Release: **v3.0** (2026-08-19)

The literature-integration package is frozen for manuscript use. Further expansion of the source corpus or large-scale evidence extraction is outside this release scope.

## Closure criteria

- **Citation clusters complete:** all 25 domain rules, 25 mechanism rules and 19 route records expose their full deduplicated `supporting_source_ids` and `supporting_dois` clusters.
- **Endpoint definitions submission-ready:** all six endpoints include a definition, original unit, frozen training unit, valid-label count, exact forward and inverse transformations, invalid-value handling and source mapping.
- **Route evidence interpretable:** `direct_route_precedent`, `qualified_close_analogue` and `contextual_or_analogous_support` are defined as descriptive provenance classes and are not used as scores, ranking weights or model inputs.
- **Release reproducible:** the package is rebuilt from source assets, hashed, manifested and checked by `scripts/validate_release.py`.

## Scope boundary

The running `dense_plus_pi_family` descriptor-ablation experiment belongs to model-representation evaluation, not to unfinished literature curation. Its eventual result may update the model-results registry, but it does not reopen this literature-integration release. Strict-clean retraining remains a separate sensitivity audit and does not replace the frozen D06/F06 endpoint definitions in this snapshot.
