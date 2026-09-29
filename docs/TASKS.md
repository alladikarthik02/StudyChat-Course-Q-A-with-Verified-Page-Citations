# Implementation tasks and checkpoints

StudyChat is a personal learning project. The implementation plan comprised T0–T8, followed by a T9 handoff and two follow-up accuracy/evaluation checkpoints.

| Task | Completed work | Validation |
| --- | --- | --- |
| T0 | Technical spec, architecture critique, safety requirements | Documented scope, risks and measurement policy |
| T1 | React/TypeScript, FastAPI, PostgreSQL/pgvector, migrations, configuration and CI | Configuration, migration and scaffold checks |
| T2 | Bounded PDF ingestion, atomic storage, upload/list/delete and restart recovery | Real database and ingestion tests |
| T3 | Citation parsing, exact/fuzzy quote verification and source offsets | Unicode, malformed citation, numeric/negation and scope tests |
| T4 | Retrieval, OpenAI adapter, streaming, cancellation and limits | Provider mocks, stream lifecycle and live calls |
| T5 | Library, chat, citation chips and PDF.js highlighting | Eleven frontend tests and seven browser workflows |
| T6 | Dataset schemas, paired replay, calibration and provenance | Hand-calculated metric fixtures and stream validation |
| T7 | Hardening and reproducible setup | Backend, browser and clean CI checks |
| T8 | Frozen synthetic coursework evaluation | 16/16 cited answers, 13/16 passing page labels |
| T9 | Setup, evidence and learning notes | Handoff and documented limitations |
| R1 | Hybrid lexical/semantic retrieval, bounded model relevance selection | 118 backend cases, frontend/browser/build checks; five-question development run |
| R2 | Fresh cloud chapter evaluation and repository cleanup | Final results in EVALUATION_RESULTS.md; publication audit in HANDOFF.md |

## Checkpoint policy

Explain each completed step, run relevant tests, document actual challenges and safety evidence, inspect staged changes, and commit/push necessary files. Private PDFs, keys, extracted text and raw outputs stay local.

## Contribution to quality

Ingestion preserves physical pages; retrieval finds relevant passages; verification rejects unmatched quotes; the UI keeps incomplete answers provisional. Evaluation separately measures coverage and page-label accuracy, retaining errors and abstentions in the denominator. Functional tests do not establish answer quality. The simultaneous learning goals are 90% page-label accuracy and 95% cited-answer coverage; report actual counts and uncertainty even when these goals are missed.

## Actual challenges

See CHALLENGES.md for PDF extraction boundaries, Unicode source offsets, stream completion, calibration contamination, rare-term retrieval and incomplete synthetic page labels. See SAFETY.md for evidence supporting each protection.
