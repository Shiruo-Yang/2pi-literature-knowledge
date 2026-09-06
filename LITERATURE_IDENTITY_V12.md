# Source-local molecular identity database v12

This release adds a traceable identity layer to the literature-knowledge package. It is an evidence-organization resource, not a new experimental optical database.

## Frozen contents

The v12 source-local layer contains 124 source-local entities, 3,376 evidence links and 2,344 formulation clusters. Seventy-two entities have an accepted single-molecule identity with an RDKit-valid structure identifier. Eight salt, ionic, commercial or otherwise multicomponent records are retained in a separate material registry. Thirteen non-chemical tokens are retained in a terminal registry so that process acronyms, citation markers, laser-source labels and instrument identifiers are not mistaken for molecules.

The automatic unresolved queue contains 31 entities and 168 registered structure-candidate evidence rows. It is divided into eight wildcard/polymer structures, four competing structures, three non-unique structure pairings and sixteen entities without a usable structure candidate.

## Public data boundary

The public package contains CSV and JSON summaries, registries and a SQLite snapshot. Local filesystem paths, downloaded PDFs, page images and local caches are not distributed. Page numbers and source-text locations remain in the registries as provenance fields.

The accepted identity layer is limited to molecular identity linkage. It does not create experimental values, six-task model labels, external-validation observations, ZINC22 screening decisions or quantum-chemistry inputs. Material records are explicitly excluded from single-molecule graph modelling.

## Reproducibility checks

- 72/72 accepted single-molecule structures pass RDKit parsing and identifier recomputation.
- The v12 SQLite snapshot passes `PRAGMA integrity_check`.
- The original v11 accepted identities are preserved.
- The unresolved queue covers every non-accepted, non-terminal source-local entity exactly once.
