# Manuscript-aligned literature database

The current scientific database is `data/research/research.sqlite`. It organizes the existing corpus around the study's literature-to-decision argument: molecular-design priors and property requirements inform the six-task profile; mechanism and formulation context determine how those predictions can be interpreted; synthesis evidence supports materialisation planning. Frozen model, screening and quantum-chemistry records are referenced as downstream study context.

## Research modules

| Module | Scientific question | Existing content | Manuscript role |
|---|---|---|---|
| Molecular design | Which molecular families, structural roles and boundaries are relevant? | 25 domain rules, 7 identity/role field records, shared compound index | Structural priors and family-sensitive representation rationale |
| Property profile | Which optical or photochemical evidence motivates the six endpoints? | Six endpoint definitions and fixed utility weights, 13 endpoint-rationale source links, 286 related field records | Explain the predictive profile and the distinction between optical response and productive initiation |
| Mechanism | Which Type-I, Type-II or SET/PET interpretation is supported? | 25 mechanism rules and 205 statement candidates | Mechanism admissibility, partner requirements and claim limits |
| Formulation and processing | Under which formulation and irradiation conditions were results reported? | 8,700 field candidates and 2,344 source-context groups | Interpret observed thresholds, conversion and geometry in context |
| Synthesis | What source precedent supports making a molecular family? | 19 route-evidence records and 59 text candidates | Family-level route plausibility and synthetic-accessibility rationale |

Counts describe different objects and must not be added as if they were independent experiments. The property module contains 48 public scalar candidates among its 286 field records. Those candidates have their own source/identity/use status; 48 is not a count of newly validated optical measurements. Most of the current numerical extraction coverage is processing context.

Module assignment follows the controlled field dictionary and describes intended organizational use. For example, generic wavelength fields enter the context module with an unresolved-role requirement; their assignment does not establish that every such value is a processing wavelength. These module counts are not a final classification of all experiments in the original papers.

The modules follow the manuscript's literature-knowledge role. They do not freeze future Results subsection titles. The frozen model weights and manuscript conclusions have not changed in this reorganization.

## Scientific records and common indexes

| Table | Record unit |
|---|---|
| `papers` | One DOI-first or unresolved-alias source key; includes current bibliographic fields and original year/journal |
| `compounds` | One distinct recorded InChIKey from the previously accepted source-local identity assignments |
| `compound_source_links` | One source-local identity assignment, preserving its original entity ID, location and confidence |
| `observations` | One source-anchored scalar candidate with a canonical property, value, explicit unit and use status |
| `observation_evidence` | Link from a scalar candidate to its original field record and representation |
| `evidence_index` | One original field record, assigned to a research module and canonical property without losing its ID or original status |
| `evidence_compounds` | One inherited evidence-to-accepted-identity link, retaining its original match basis, confidence and status |
| `formulation_contexts` | One original extraction-context group; this is not necessarily a unique experiment or complete recipe |
| `knowledge_rules`, `rule_sources` | One literature-derived rule and its explicit supporting sources |
| `six_task_profile`, `profile_sources` | One fixed endpoint definition and its inherited literature-rationale citations |
| `field_dictionary` | One original field name mapped to its scientific module, canonical concept and interpretation requirement |
| `metadata_provenance`, `metadata_conflicts` | Bibliographic fills or differences linked to the input metadata row |
| `research_modules`, `input_assets` | Module definitions, exact record counts and input fingerprints |

All tables are available as UTF-8-with-BOM CSV files alongside the queryable SQLite database. `summary.json` reports the actual build counts. `manifest.json` checks every export. The five research modules are the browsing structure; the 17 relational tables implement the underlying links.

### Compound identity and scientific ownership

The compound index contains 26 recorded structure identifiers, linked to 72 accepted source-local assignments. Materials/ionic objects, nonchemical tokens, unresolved identities and global-name-only matches remain in the preserved supporting database. They are not promoted into this accepted-structure index. An inherited identity link means the source contains a named compound; it does not by itself prove that a particular value belongs to that compound.

### Observation fields and missing conditions

The 6,179 scalar candidates retain original field membership through `observation_evidence`. Essential measurement columns are explicit: `measurement_wavelength_nm`, `measurement_solvent`, `measurement_method`, `temperature_K`, `peak_definition`, and `value_qualifier`. They remain empty or unresolved where measurement-specific ownership is unavailable in the public source projection. Nearby wavelengths, solvent names and the shared context cluster are not used to fill these fields automatically.

`condition_assignment_status` identifies this limit. `context_ids` preserve possible surrounding conditions for subsequent source review. Do not treat a context identifier as proof that every field belongs to the same experiment. `value_status` remains a reported scalar candidate, and `measurement_certification` remains `not_newly_certified`. No count of complete independently validated experiments is inferred from this table.

Known original/converted field pairs can share a candidate only when source, exact anchor, complete context membership, explicit normalized units, quantity, identity-link set and use status agree, with a unique member per representation. No pair met all conservative merging requirements in this build, so every scalar candidate retains its own field-record identity. Scientific field normalization must not be confused with deduplication of experiments.

## Controlled fields and units

The field dictionary maps 98 original field names onto 56 canonical concepts while retaining `original_field`. Unit suffixes and synonyms do not generate new scientific properties. Important distinctions are preserved:

- Reported wavelength with unresolved role, laser/processing wavelength, fabricated line width and optical peak location remain different concepts.
- `sigma_2pa` is related context for the two optical endpoints. It is never assigned to `sigma_780` or `sigma_max` without the required wavelength or peak definition.
- Average power, peak power, irradiance, energy, polymerisation threshold and damage threshold retain separate concepts. An unspecified original `power_raw` stays unspecified.
- Initiator loading is not solubility; `wt%` and `phr` remain different amount bases.
- Triplet lifetime, unspecified quantum yield and ISC/triplet context remain related evidence, not labels for the model's ISC energy proxy.
- Synthesis precedent supports route plausibility, not a numerical synthetic-accessibility score.

Only recognized, explicit unit scales are converted: for example W to mW, mm/s to micrometres/s, or ps to fs. Original values and units remain in the supporting evidence files, and each member records whether an existing normalized value or a public raw scalar was used. Missing normalized units are not borrowed from a potentially differently scaled raw value. Qualifiers absent from the public projection remain explicitly unresolved.

## Six-task profile and downstream use

`six_task_profile.csv` retains the six fixed endpoint definitions, original label-source descriptions and deployed unit-sum weights. Literature is used to motivate evaluation criteria, structural families, mechanisms and formulation constraints. The trained proxy labels originate from the separate QuantumChem-200K modeling layer. The number of related field records is not a count of independent task labels, and the weights express the existing utility policy rather than a performance optimum.

`profile_sources.csv` links the inherited endpoint-rationale source aliases to the common source keys. `knowledge_rules.csv` preserves Type-I, Type-II and SET/PET context, coinitiator requirements, route evidence classes and allowed interpretations. These records support the paper's decision workflow; they are not newly computed screening results or quantum-chemistry observations.

## Metadata and quality

Existing bibliography data supplied 225 missing years and 224 missing journals through exact DOI matches. All 449 fills have input-row provenance. Six journal-name differences are formatting variants involving case or punctuation; the established spelling is retained. Missing values and any future substantive conflicts remain explicit. Publication type and original-experiment source status are not inferred from title keywords.

The current use restrictions are carried into every affected evidence record and scalar candidate: 33 scalar-to-anchor review holds, four 250 nm wavelength-component holds and 32 internal-document external-evidence exclusions. Records remain queryable with these flags. Location recovery is inherited from the previously verified traceability overlay.

## Repository layout

```text
README.md                    Study argument, five modules and main download links
data/research/               Current scientific tables and research.sqlite
data/literature/             Preserved base evidence and traceability maintenance layer
inputs/                     Public bibliography projection for reproducible metadata fills
configs/                    Controlled scientific dictionary and field-use decisions
docs/                       Scientific data guide and maintenance documentation
study_context/              Previous manuscript map, model/weight/screening/QM registries
outputs/                    Earlier acquisition and compatibility packages
scripts/                    Rebuild, query and validation commands
```

The previous root CSV and historical study files were moved into `study_context` without changing their values. Links in moved Markdown files were rebased where their old targets existed. Legacy outputs are supporting compatibility records, not extra observations to append to the current scientific database.

## Rebuild and verification

The current scientific export rebuilds from public files with Python 3.11 or later and the standard library:

```sh
python scripts/build_research_database.py --output new_research_staging
python scripts/verify_research_database.py --directory new_research_staging --metadata inputs/bibliographic_metadata.csv
python scripts/test_research_database.py
python scripts/query_research_database.py --module mechanism --kind rules --limit 3
```

The independent verifier checks all 17 relational tables, CSV/SQLite agreement, every original evidence ID, controlled-field assignments, identity/source links, explicit unit arithmetic, unchanged task weights, use restrictions and metadata row provenance. The preserved base and current snapshot hashes are also checked by the release validation tools. These checks establish reproducible organization and conservative transformations; source-level extraction precision remains a separate evaluation task.

The bibliography projection contains only the 247 previously acquired paper identifiers, DOIs, titles, years and journals, in original row order. Its provenance file fingerprints the original private path-bearing input. Original full text and images remain in the local evidence archive, while public scientific tables retain their identifiers and checksums.

The schema design follows the compound/property/condition linkage described in [Su et al.](https://doi.org/10.1002/advs.202204902), [Joung et al.](https://doi.org/10.1038/s41597-020-00634-8), the [ChemDataExtractor thermoelectric database](https://doi.org/10.1038/s41597-022-01752-1) and the [Open Reaction Database schema](https://docs.open-reaction-database.org/en/stable/schema.html). These are design precedents; their data or reported accuracies are not added to this release.
