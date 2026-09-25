# Implementation tasks and checkpoints

T0–T5 are complete. Each row is a stop-and-explain checkpoint, not authorization to skip the user's requested pause. Tests are written alongside the task they protect.

There are **9 tasks total (T0–T8)**: one planning task and eight implementation/validation tasks. At the end of each task, review changes, run appropriate checks, commit, push to the StudyChat repository, report the result, and pause.

| Task | Deliverable and dependency | Acceptance evidence | Interview discussion | State |
| --- | --- | --- | --- | --- |
| T0 | Read source material; spec, architecture critique, safety matrix, task plan | Source-to-requirement review; explicit unknowns | What does citation verification actually prove? | Complete: design only |
| T1 | Repository scaffold; React/TS, FastAPI, Compose Postgres/pgvector, migrations, config, fake provider, lockfiles, CI skeleton | Fresh local fixture startup, health/readiness, configuration tests, clean migration | Why this stack and why a fake provider? | Complete |
| T2 | Bounded PDF ingestion, page/chunk storage, upload/status/list/delete APIs | PDF fixtures; boundary/timeout/failure/restart tests; actual pgvector integration | How do you keep partial ingestion out of search? | Complete |
| T3 | Citation parser, normalization, exact/fuzzy verifier, offset mapping | Valid/wrong-page/unknown-doc/Unicode/short-quote/malformed/number-negation tests | Why deterministic quote matching, and where does it fail? | Complete |
| T4 | Scoped retrieval, threshold gate, OpenAI adapter, prompt contract, SSE lifecycle | Fake-provider streaming/error/cancellation tests; live smoke only with configured credentials; record model snapshot | Why abstain before streaming? Why no midstream retry? | Complete; paid smoke not run (no key) |
| T5 | Upload/chat UI, provisional states, verified chips, PDF.js viewer/highlights | Browser happy path plus wrong citation, cancellation, XSS and highlight-fallback tests | How do two different PDF text extractors agree? | Complete |
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

## T2 report

Completed upload/status/list/download/delete APIs, bounded isolated PDF extraction, physical-page chunking, metadata page 0, batched fixture embeddings, atomic publication, restart cleanup, and cancellation-safe mutations. Final verification: **33 tests passed** against real PostgreSQL/pgvector, Ruff passed. One upstream test-client deprecation warning remains. Detailed observed challenges and limitations are in CHALLENGES.md; safety evidence is in SAFETY.md. Source PDFs and generated fixtures are not committed. Metric contribution: reliable physical-page identity and prevention of partial indexing; real retrieval/answer accuracy is not measured. Next: T3 citation verification.

## T3 report

Implemented strict citation parsing, exact and labeled approximate quote checks, NFKC/grapheme-aware source offsets, dehyphenation and whitespace normalization, invalid-reference replacement, ambiguity handling, finite resource budgets, and server-scoped database page loading. Added 46 citation tests plus two database integration tests for selected/ready page scope and upload-to-verification. Final local result: **81 tests passed**, no skips, Ruff passed. T1 and T2 GitHub workflows also passed on Linux. T3's commit triggers its own workflow; publication is reported in the task conversation.

Safety evidence: S04 document/page scoping and S07 matching limits are tested at the service level. Frontend chips, streaming, and PDF.js highlighting remain T4/T5 work. Metric contribution: rejects wrong-document/wrong-page/invalid quotes while retaining valid Unicode and hyphenated quotations. The exact-only mode makes future fuzzy sensitivity evaluation possible. Resume metrics remain unmeasured, not inferred from these synthetic regression tests. Interview explanation: matching is deterministic and inspectable, but neither a matching quote nor a 0.9 fuzzy ratio establishes entailment. Stop here as requested; T4 is next and has not started.

## T4 report

Implemented exact cosine top-six retrieval scoped to selected ready documents and embedding model, pre-delta abstention, pinned OpenAI Responses/embedding adapter, POST SSE events and heartbeats, cancellation, output/time/concurrency limits, and post-generation source revalidation. Fixture mode streams deterministic excerpts. The full suite passes 94 tests with real pgvector; HTTP mocks exercise provider completion/errors/disconnects. No API key was present, so paid live smoke remains unverified. Threshold 0.25 is explicitly untuned. Metric contribution: prevents weak-context generation and cross-document/model retrieval; empirical retrieval recall and resume metrics await real labels.

Safety: S04/S05/S06/S08/S09/S13/S14 now have service-level tests. Live transmission requires explicit request consent. No retries after generation begins. One upstream test-client deprecation warning remains. Next: T5 UI and PDF viewer; continue under the user's T4–T6 authorization.

## T5 report

Built the course library, bounded upload flow, document selection/deletion, consent UI for live transmission, question composer, provisional stream states, cancellation/errors, checked citation chips, and lazy-loaded PDF.js source viewer. The viewer independently maps Unicode text to DOM ranges; ambiguous/missing matches show the quote with a visible fallback. Plain React text rendering prevents model HTML execution. Autoscroll stops when the reader scrolls up; mobile layout is checked.

Validation: 11 frontend unit tests and 7 Chromium browser tests passed, including a real upload → fixture stream → verified page 2 → rendered PDF highlight; production build passed. Visually inspected the rendered result. CI now runs browser tests using generated original PDFs. No PDF binaries, screenshots, browser downloads, node_modules, or build output are committed. Paid live API calls remain untested. Next: T6 evaluation tooling.
