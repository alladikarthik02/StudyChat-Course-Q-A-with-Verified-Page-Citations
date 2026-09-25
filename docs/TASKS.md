# Implementation tasks and checkpoints

T0 and T1 are complete. Each row is a stop-and-explain checkpoint, not authorization to skip the user's requested pause. Tests are written alongside the task they protect.

There are **9 tasks total (T0–T8)**: one planning task and eight implementation/validation tasks. At the end of each task, review changes, run appropriate checks, commit, push to the StudyChat repository, report the result, and pause.

| Task | Deliverable and dependency | Acceptance evidence | Interview discussion | State |
| --- | --- | --- | --- | --- |
| T0 | Read source material; spec, architecture critique, safety matrix, task plan | Source-to-requirement review; explicit unknowns | What does citation verification actually prove? | Complete: design only |
| T1 | Repository scaffold; React/TS, FastAPI, Compose Postgres/pgvector, migrations, config, fake provider, lockfiles, CI skeleton | Fresh local fixture startup, health/readiness, configuration tests, clean migration | Why this stack and why a fake provider? | Complete |
| T2 | Bounded PDF ingestion, page/chunk storage, upload/status/list/delete APIs | PDF fixtures; boundary/timeout/failure/restart tests; actual pgvector integration | How do you keep partial ingestion out of search? | Pending |
| T3 | Citation parser, normalization, exact/fuzzy verifier, offset mapping | Valid/wrong-page/unknown-doc/Unicode/short-quote/malformed/number-negation tests | Why deterministic quote matching, and where does it fail? | Pending |
| T4 | Scoped retrieval, threshold gate, OpenAI adapter, prompt contract, SSE lifecycle | Fake-provider streaming/error/cancellation tests; live smoke only with configured credentials; record model snapshot | Why abstain before streaming? Why no midstream retry? | Pending |
| T5 | Upload/chat UI, provisional states, verified chips, PDF.js viewer/highlights | Browser happy path plus wrong citation, cancellation, XSS and highlight-fallback tests | How do two different PDF text extractors agree? | Pending |
| T6 | Eval schema, fixture corpus, paired off/on scorer, threshold selection script, provenance manifests | Hand-computed scorer fixtures, split checks, offline repeatability; real labels remain separately tracked | How do you prevent selection bias and denominator gaming? | Pending |
| T7 | End-to-end hardening and reproducible runbook | Full offline suite, real DB/browser checks, fresh setup, safety matrix evidence | What breaks under failure and concurrent deletion? | Pending |
| T8 | Human research/corpus evidence, dev tuning, locked live evaluation and truthful resume update | Actual anonymized notes, permitted PDFs, blind gold labels, raw runs, 30-answer spot-check | What do your measured numbers support and not support? | Pending: human evidence required |

T1–T7 can progress without inventing human research. T8 needs real course materials and user-provided/interviewed participant evidence. The build guide recommends research before coding; record that validation is outstanding if the user chooses to continue implementation first. Do not contact classmates without explicit instruction.

## Checkpoint report template

- Task and outcome:
- Files/functions changed:
- Tests run and results:
- Metric contribution: which target this task supports, diagnostic evidence available, and any measured gap (otherwise “not measured”):
- Safety IDs verified / still pending:
- Actual challenge, root cause, chosen solution, alternatives:
- Interview question and evidence-backed answer:
- Next task and unresolved dependencies:
- Commit ID and push result:

## How each task supports the resume targets

The simultaneous objectives are at least 90% verified citation page accuracy and at least 95% answer rate. Definitions, exact-count examples, and the improvement policy live in [RESUME_EVIDENCE.md](RESUME_EVIDENCE.md). No task may claim downstream benchmark success solely because unit tests pass.

| Task | Contribution and required diagnostic |
| --- | --- |
| T1 | Make results reproducible through locked dependencies, deterministic fixtures, and explicit configuration |
| T2 | Preserve physical page identity and extraction coverage; identify failed/empty pages before they cause retrieval misses |
| T3 | Reject wrong references while retaining valid quotations; measure false accepts/rejects on labeled quote fixtures, including numbers and negation |
| T4 | Inspect retrieval recall@6 and pre-answer abstentions on available development labels; retain traces for diagnosing misses |
| T5 | Ensure displayed citations match server-verified references; browser tests prevent a UI error from undoing backend correctness |
| T6 | Produce paired off/on metrics and failure-category reports; validate all denominators against hand-calculated examples |
| T7 | Reduce infrastructure failures that count against answer rate; ensure no regression in previously validated behavior |
| T8 | Iterate on development failures, freeze settings, evaluate the real holdout, and report targets versus actual values together |

If real development PDFs/labels become available before T8, use them for T2–T7 diagnostics without inspecting held-out system outcomes. Human evidence remains a dependency, not something implementation can fabricate.

## T0 report

Read both supplied files and the resume's embedded repository link. The workspace is empty, and remote inspection succeeded with no refs returned. No application code or tests existed to review. Designed the architecture, documented its holes and limits, and mapped the resume bullets to required evidence. No application tests have run. Next checkpoint: T1.

## T1 report

Implemented React/TypeScript/Vite shell, FastAPI health/readiness, strict fixture-only configuration, deterministic embedding interface, transactional migrations, PostgreSQL 16/pgvector Compose service, dependency locks, CI, and local runbook. Nine backend tests passed including real database migration/idempotence and vector-distance checks; frontend type check and production build passed; Ruff passed. Docker startup required its credential helper on PATH. pnpm required explicit approval of the esbuild build script, now recorded in workspace configuration. The test client emits an upstream httpx deprecation warning; tests still pass.

Safety evidence: server-only secret configuration, host restrictions, loopback database binding, no live provider adapter, ignored data and environments. Metric contribution: reproducible plumbing only; accuracy/answer-rate are not measured. Interview explanation: a deterministic fake provider lets failure tests run without cost or model variability, but cannot validate semantic answer quality. Next: T2 ingestion.
