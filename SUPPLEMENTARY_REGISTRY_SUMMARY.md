# Supplementary registry summary (v1.0)

This compact summary accompanies the Methods/Supplementary Information so that the C1 logic remains understandable without requiring the reader to inspect the full GitHub package.

| Layer | Scientific question | Registry | Items | Direct computational link |
|---|---|---|---:|---|
| Source | Where did the evidence come from? | `source_registry.csv` | 45 | DOI/source provenance |
| Layer 1 | What should a 2PI candidate be evaluated on? | `domain_knowledge_registry.csv` | 44 | domain criteria and admissibility controls |
| Layer 2 | What is predicted and how is the molecule represented? | `endpoint_representation_registry.csv` | 37 | six targets; graph; D06/F06 descriptors |
| Layer 3 | How is a candidate routed to mechanism-specific assessment? | `mechanism_knowledge_registry.csv` | 44 | Type-I/Type-II/SET-PET routing and claim limits |

The complete evidence chain and five worked examples are provided in `examples/evidence_to_computational_use_examples.csv`. Candidate-level numerical QM results remain a separate result asset and are not embedded in mechanism rules.
