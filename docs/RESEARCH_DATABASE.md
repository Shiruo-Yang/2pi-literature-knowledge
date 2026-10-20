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
| `source_dossiers` | One source entry joining current bibliography, manuscript modules and attachment availability |
| `source_documents`, `document_binding_checks` | One attachment link and, where a local PDF exists, its first-page DOI-literal check |
| `document_reuse_groups` | One repeated PDF hash, preserving all attachment links rather than counting duplicate files as independent originals |
| `bibliography_updates`, `bibliography_differences` | Exact-DOI empty-field fills and retained differences from the read-only Zotero projection |
| `document_parser_pilot` | One source-page/parser attempt, with status, output fingerprint and observed runtime warnings |
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

All tables are available as UTF-8-with-BOM CSV files alongside the queryable SQLite database. `summary.json` reports the actual build counts. `manifest.json` checks every export. The five research modules remain the browsing structure; 33 relational tables implement scientific records, source audits, use assessments and document provenance. Document inventories are supporting infrastructure, not a sixth scientific module.

### Paper-supporting evidence and quality assessments

`paper_core` is an entry point to existing study support, not a certification tier. Its 80 entries comprise 69 literature-linked rules, six frozen endpoint definitions, two source-checked measurement cases and three source-identity cases. Records state their allowed and prohibited uses. Citation-linked priors are useful for interpretation but are not candidate-specific mechanism proof; endpoint-rationale citations do not establish optimal weights or a minimal sufficient task set.

`evidence_readiness` assesses every preserved field candidate. It distinguishes source-location evidence, accepted source-local name links, explicit units, numerical/component holds, internal-document exclusion and unresolved scientific ownership. It does not certify a candidate value merely because it has a source locator. `rule_readiness` records citation counts and the presence of scope/partner context, while leaving primary-experiment support and counterevidence explicitly unadjudicated. `quality_coverage` reports these checks separately for the 56 canonical concepts. These are completeness/use checks, not measured precision or recall.

### Previously audited source-defined cases

`source_structures` stores five source-local structure records separately from the 26 inherited accepted structure identifiers. They have not been globally merged with that index or counted as five new unique molecules. Two Cvejn structure records are associated with `source_measurements`; three Rumi structures are identity-conflict cases without optical labels. The Rumi generic drawing/name discrepancy remains explicit, together with the compound-specific name/formula basis for the previous assistant transcription.

`source_measurements` contains Cvejn compounds 6 and 7: 757 GM at 830 nm and 667 GM at 810 nm, respectively. The source table, structure and method locators remain linked. `measurement_conditions` contains 16 fields: eight per measurement, including sample concentration, reference dye/solvent/concentration, scan bounds and two explicitly missing laser specifications. THF is the sample solvent; methanol belongs to the Rhodamine B reference and is not reassigned to the sample.

These are maxima within the reported 750–850 nm measurement window, not certified global maxima. Their source review was performed by the assistant in the prior audit, not an independent human reviewer. They are retained as source-reported optical context with missing laser specifications, not a fully comparable measurement cohort. Training, final-test, global-maximum and independent-new-sample eligibility remain false; the original curve-extraction history is not certified. The known development overlap is retained categorically without importing training targets, predictions or sealed test data. No legacy observation is replaced, and cross-database duplicate status remains unresolved.

`source_fact_use` permits citation of the reported facts and within-source descriptive comparisons when conditions and limitations are disclosed. `cross_source_comparison_ready` remains false: absent laser specifications have not been harmonised across publications. This use-specific distinction does not prohibit quoting an otherwise traceable source value merely because every laser parameter is unavailable.

`source_lineage` adds three previously checked review-to-primary reference links. Bibliographic linkage does not certify the structure–value–condition chain of individual measurements. `source_audits` records original audit-input, manifest and source-document hashes without publishing local paths or source documents. Five DOI references absent from the old 621-source inventory are appended, giving 626 keys; unavailable bibliographic metadata are not invented.

The path-free input is `inputs/source_audit_records.json`. A public rebuild needs this file, not the local copyrighted full text. The optional `verify_source_audit_inputs.py` additionally checks the privately retained original assets and independently re-parses the saved source table, without opening model datasets or sealed test labels. It verifies provenance and preserved facts, not whole-corpus extraction accuracy.

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

The existing bibliography projection supplied 225 missing years and 224 missing journals by exact DOI, with 449 input-row provenance records. A separate read-only Zotero projection matched 471 of the current sources and supplied another 341 years and 333 journals. The combined 1,123 empty-cell fills leave 15 missing years and 24 missing journals across 626 source keys. `metadata_provenance` retains the first projection; `bibliography_updates` retains the Zotero fills. Summary fields distinguish these inputs from the combined total.

Six prior journal-format differences remain unchanged. The Zotero comparison records another 36 formatting variants and two content differences without overwriting existing values: a 2015/2016 publication-year discrepancy for DOI `10.1021/acs.macromol.5b02336`, and a title spelling discrepancy for `10.1021/acs.macromol.5b00201`. These remain unadjudicated; neither is silently declared a factual error. Publication type and original-experiment source status are not inferred from titles.

### Document inventory and bounded parser pilot

`source_dossiers` is the common source entry point across the five research modules. Module membership is inherited from linked evidence, priors, endpoint citations and source-audit cases, not inferred from a PDF filename. It distinguishes bibliography coverage from field-evidence coverage and local-document availability.

`source_documents` preserves 666 attachment links, including 518 local PDF links with 425 distinct content hashes. Forty-five repeated-file groups are confined to one source key each. No cross-source identical-file group was detected; different PDF versions, reused experiments and review-to-primary dependencies are not excluded by this result. Duplicate attachments remain linked and were not deleted from Zotero or disk. Filename-based supporting-information suggestions are explicitly provisional; the parent-item DOI is not treated as verified attachment identity.

`document_binding_checks` covers all 518 PDF links using the first page of each distinct file, with OCR disabled. The expected DOI appears literally for 463 links; 55 require further binding checks. Absence is not proof of a wrong attachment, and presence is not unique source certification. Page-output hashes support local recomputation without distributing source text.

OpenRefine was run on a copy of the 471-row bibliography projection. Original columns and row count were retained; added columns normalise whitespace and DOI case. These selected values were already clean, so changed-cell counts are zero. No fuzzy reconciliation or chemical merging was used. The official 3.10.1 Windows package digest was checked; its API self-reported `3.10-SNAPSHOT [TRUNK]`, so both identifiers are disclosed in `inputs/openrefine_cleanup.json`.

The ten-source parser pilot selected papers with existing quality gaps and table-related keywords, one distinct original file per source. It did not use prediction errors, model targets or sealed test data. LiteParse 2.0.0 read the first page and a selected target page; Docling 2.140.0 read the target page with table structure enabled. All 20 attempts produced output, with seven Docling candidate tables across six papers. This selected native-text sample does not establish performance on scanned papers or the whole corpus. One Docling warning reported 1 of 214 PDF cells dropped from a 16-by-12 table grid for DOI `10.1088/2631-7990/ae289e`, PDF page 12. It remains visible in the pilot table, with no certified numeric import.

Original PDF text, table CSVs and page coordinates remain in the private archive. Public pilot rows contain only tool versions, document/output fingerprints, target pages, counts and the observed warning. Neither a successful parse, agreement between parsers nor a table count is an extraction-accuracy estimate. MinerU.Chem remains available for targeted chemical-structure candidates; it was not rerun for this bibliography/document batch. GROBID was not deployed because this bounded batch did not require new reference-list extraction. No competing database or new training-label layer was created.

The current use restrictions are carried into every affected evidence record and scalar candidate: 33 scalar-to-anchor review holds, four 250 nm wavelength-component holds and 32 internal-document external-evidence exclusions. Records remain queryable with these flags. Location recovery is inherited from the previously verified traceability overlay.

## Repository layout

```text
README.md                    Study argument, five modules and main download links
data/research/               Current scientific tables and research.sqlite
data/literature/             Preserved base evidence and traceability maintenance layer
inputs/                     Public bibliography, document fingerprints, parser status and source-audit projections
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
python scripts/verify_evidence_quality.py --directory new_research_staging
python scripts/verify_source_organization.py --directory new_research_staging
python scripts/test_research_database.py
python scripts/test_evidence_quality.py
python scripts/test_source_organization.py
python scripts/query_research_database.py --module mechanism --kind rules --limit 3
python scripts/query_research_database.py --module mechanism --kind core --query coinitiator --limit 3
python scripts/query_research_database.py --kind source-measurements --limit 2
python scripts/query_research_database.py --kind sources --module property_profile --limit 3
python scripts/query_research_database.py --kind document-reuse --limit 3
python scripts/query_research_database.py --kind parser-pilot --query docling --limit 3
```

The independent verifiers check all 33 relational tables, CSV/SQLite agreement, every original evidence ID, controlled-field assignments, identity/source links, explicit unit arithmetic, unchanged task weights, use restrictions, metadata row provenance, document groups, parser status and the source-audit projection. The optional `verify_source_organization_private.py` independently re-reads the retained Zotero facts, rehashes all original PDFs and parser outputs, and recomputes DOI-literal checks from saved page text. The preserved base and current snapshot hashes are also checked by the release validation tools. These checks establish reproducible organization and conservative transformations; source-level extraction precision remains a separate evaluation task.

The original bibliography projection contains 247 previously acquired paper identifiers, DOIs, titles, years and journals in original row order. The additional Zotero projection contains 471 matched parent items and their document metadata. Neither projection includes notes, annotations, source full text or private paths. Original full text and images remain in the local evidence archive; public scientific tables retain identifiers and checksums.

The schema design follows the compound/property/condition linkage described in [Su et al.](https://doi.org/10.1002/advs.202204902), [Joung et al.](https://doi.org/10.1038/s41597-020-00634-8), the [ChemDataExtractor thermoelectric database](https://doi.org/10.1038/s41597-022-01752-1) and the [Open Reaction Database schema](https://docs.open-reaction-database.org/en/stable/schema.html). These are design precedents; their data or reported accuracies are not added to this release.
