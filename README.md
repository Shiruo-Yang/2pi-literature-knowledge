# Literature knowledge for two-photon photoinitiator prioritisation

This database supports the study's central workflow: literature-defined molecular requirements inform a six-task molecular profile, while mechanism, formulation and synthesis evidence guide the interpretation of candidate predictions.

The scientific content is organised into five modules that follow that argument. [Study and data guide](docs/RESEARCH_DATABASE.md) · [Current database](data/research/research.sqlite) · [Data summary](data/research/summary.json)

## Research content

| Module | What the literature contributes | Current records |
|---|---|---|
| Molecular design and structural priors | Molecular families, donor/acceptor roles and structural boundaries used before interpreting graph-model predictions | 25 domain rules; 7 identity/role field records |
| Six-task property rationale and optical evidence | Endpoint definitions, optical and excited-state evidence, and the scope of each predictive proxy | 6 fixed endpoint definitions; 286 related field records |
| Photoinitiation mechanism | Type-I, Type-II and SET/PET context, partner requirements and limits on mechanism claims | 25 mechanism rules; 205 statement candidates |
| Formulation and processing | Resin/initiator loading, irradiation conditions, thresholds, conversion and fabricated geometry | 8,700 field candidates; 2,344 context groups |
| Synthesis and materialisation | Source-backed route precedent and its applicability to molecular families | 19 route-evidence records; 59 text candidates |

Each module answers a question in the paper. Literature records provide chemical rationale, experimental context and source evidence. The frozen six-task labels and model weights retain their separate computational provenance; related literature records are not assigned directly as new model labels.

The current field inventory contains 9,257 records mapped from 98 original field names to 56 canonical concepts. The 69 source-linked rules and six endpoint definitions supply the study's knowledge layer. Field candidates, scalar candidates, context groups and rules are counted separately.

## Main tables

| File | Scientific use |
|---|---|
| [papers.csv](data/research/papers.csv) | Literature identifiers and bibliography, with original and updated metadata |
| [compounds.csv](data/research/compounds.csv) / [source assignments](data/research/compound_source_links.csv) | 26 recorded structure identifiers linked to 72 previously accepted source-local identities |
| [knowledge_rules.csv](data/research/knowledge_rules.csv) / [citations](data/research/rule_sources.csv) | Molecular-design rules, mechanism requirements and synthesis-route precedent |
| [six_task_profile.csv](data/research/six_task_profile.csv) / [rationale sources](data/research/profile_sources.csv) | The six fixed endpoint definitions, existing utility weights and literature-rationale links |
| [observations.csv](data/research/observations.csv) | Source-anchored scalar candidates with explicit property, unit, identity/context links and use status |
| [formulation_contexts.csv](data/research/formulation_contexts.csv) | Existing formulation and exposure context groups |
| [evidence_index.csv](data/research/evidence_index.csv) / [observation links](data/research/observation_evidence.csv) | Every original field record linked to its module, concept, location and candidate |
| [field_dictionary.csv](data/research/field_dictionary.csv) | Original field names, canonical concepts, manuscript roles and interpretation requirements |
| [research.sqlite](data/research/research.sqlite) | All scientific tables, relationships and the five module views |

The source directory contains 626 source keys, of which 286 have field evidence. Five references from existing local source audits are now connected to the scientific database; they are not five newly mined papers. Those are coverage counts, not counts of fully extracted papers or complete experiments. Existing bibliography data filled 225 missing years and 224 missing journals, with row-level provenance.

## Paper-supporting evidence and permitted use

The [paper evidence index](data/research/paper_core.csv) brings together 69 source-linked priors, six fixed endpoint definitions, two previously source-checked optical table records and three structure-identity conflict cases. These 80 entries are different kinds of support, **not 80 validated measurements**. Each entry states its permitted use, current assessment status and prohibited interpretations.

| Current addition | What can be inspected |
|---|---|
| [Field readiness](data/research/evidence_readiness.csv) | A use-specific assessment for all 9,257 field candidates, including unresolved ownership, units, location and inherited holds |
| [Rule readiness](data/research/rule_readiness.csv) | Citation coverage and recorded scope for all 69 priors; primary-experiment support and counterevidence remain explicitly unassessed |
| [Source optical records](data/research/source_measurements.csv) / [structures](data/research/source_structures.csv) / [conditions](data/research/measurement_conditions.csv) | Two Cvejn table values linked to their source structures and 16 condition fields; three additional Rumi structure-only cases retain an internal drawing/name conflict |
| [Review-to-primary links](data/research/source_lineage.csv) | Three checked bibliographic links, kept separate from unverified individual measurement chains |
| [Coverage and gaps](data/research/quality_coverage.csv) | Counts by scientific concept, source, scalar candidacy, location, identity links and use restrictions |

The optical cases report 757 GM at 830 nm and 667 GM at 810 nm in THF. They retain the 750–850 nm measurement window, separate sample/reference conditions, and missing pulse-duration/repetition-rate information. They are source-reported **window maxima**, not certified global maxima, independent final-test additions, production training replacements or polymerisation-efficiency measurements. This integration reuses prior source audits; it does not create new human certification or increase the number of independent experiments by assertion.

These cases can support source-fact citation and within-paper descriptive comparisons with their reported conditions and limits. This does not establish harmonised cross-source comparability or eligibility for model evaluation.

Readiness checks measure completeness and inherited use restrictions. **Extraction accuracy and recall have not yet been measured against independent reference annotations.** A located source, a parseable structure or matching tools alone is not an accuracy benchmark.

## Reading the data

A scalar candidate has a reported value that can be organised numerically. Its compound ownership, measurement method or conditions may still need source resolution. The 6,179 scalar candidates therefore remain labelled as candidates. The property module contains 48 of these; most remaining scalar records describe processing conditions.

Measurement wavelength, solvent, method, temperature, peak definition and value qualifier have explicit fields. Missing or unresolved information stays visible. A nearby processing wavelength is not filled into an optical measurement, and a two-photon cross section is not automatically interpreted as either a global maximum or polymerisation efficiency.

Current use restrictions remain part of the tables: four 250 nm wavelength components are withheld after source-image review identified fabricated line width; 33 scalar-to-anchor gaps require review; 32 internal-document records are excluded from external-evidence use. The underlying records remain traceable.

The [study and data guide](docs/RESEARCH_DATABASE.md) explains module scope, record definitions, controlled units, source attribution and remaining evidence gaps.

## Query and reproduce

CSV files open in spreadsheet software. SQLite supports linked queries. These commands use Python 3.11 or later and the standard library:

```sh
python scripts/query_research_database.py
python scripts/query_research_database.py --module mechanism --kind rules --limit 3
python scripts/query_research_database.py --module mechanism --kind core --query coinitiator --limit 3
python scripts/query_research_database.py --kind source-measurements --limit 2
python scripts/query_research_database.py --kind coverage --module property_profile
python scripts/build_research_database.py --output new_research_staging
python scripts/verify_research_database.py --directory new_research_staging --metadata inputs/bibliographic_metadata.csv
python scripts/verify_evidence_quality.py --directory new_research_staging
python scripts/validate_release.py
```

The scientific export preserves all original evidence IDs, source links, fixed task definitions, weights and use restrictions. The verifier checks table mirrors, relationships, explicit unit arithmetic and metadata provenance. No new measurement or training-label certification is inferred from restructuring.

## Supporting records

[Maintenance documentation](docs/) describes the preserved evidence base and source-location checks. [Earlier study records](study_context/) retain the previous manuscript map, model, weight-policy, screening and quantum-chemistry registries. [Earlier acquisition packages](outputs/) remain available for provenance and compatibility. These are supporting inputs to the current scientific database, not extra observations to append.

Original full text, source images and private path-bearing inputs stay in the local evidence archive. Public exports provide scientific metadata, candidate values, rules, locations and fingerprints. Third-party material retains its original rights.
