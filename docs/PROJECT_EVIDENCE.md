# Project evidence and learning goals

StudyChat is a personal learning project exploring retrieval, streaming interfaces, source verification and reproducible evaluation. Implementation tests and observed quality are different kinds of evidence.

| Capability | Evidence |
| --- | --- |
| React/TypeScript UI and PDF.js viewer | Seven browser workflows and eleven frontend tests |
| FastAPI, PostgreSQL/pgvector, streaming and ingestion | Backend unit/integration tests and live synthetic runs |
| Citation quote verification | Exact/fuzzy matching, source scoping and invalid-citation tests |
| Reproducible evaluation | Frozen datasets, configuration hashes, paired replay and confidence intervals |

## Measurement policy

The learning goals are at least 90% labeled-page accuracy among answered questions and at least 95% cited-answer coverage simultaneously. These are goals, not guaranteed outcomes. Errors and abstentions remain in the coverage denominator. A correct-page answer must have every displayed citation in its frozen acceptable-page set. Quote matches do not establish semantic correctness.

Tune on development questions, freeze the configuration, then evaluate untouched questions once. Preserve unfavorable results. If heldout failures inform changes, use a new set for the next evaluation. Report exact counts, sample sizes and uncertainty. Synthetic questions are explicitly AI-authored, not independent human labels. No participant study was performed.

Classify failures before changing the system: extraction, retrieval, abstention, citation formatting, quote mismatch, unsupported claim or infrastructure. Keep source files and raw outputs private; publish original synthetic questions, source hashes and aggregates.

## Recorded results

The original 16-question synthetic coursework evaluation produced 16 cited answers and 13 passing page checks (100% coverage, 81.25% labeled-page accuracy). The old score is preserved after later retrieval improvements. See [evaluation results](EVALUATION_RESULTS.md) for configuration, limitations and subsequent experiments.

The fresh 20-question synthetic cloud evaluation produced 20 cited answers and 19 passing page checks (100% coverage, 95% labeled-page accuracy). Both numerical goals were met on that sample. It uses a different document and is not a controlled improvement measurement.
