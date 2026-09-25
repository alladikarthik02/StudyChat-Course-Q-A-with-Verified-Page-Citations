# Safety requirements and evidence

Requirements are tracked individually below. T1–T3 have tested evidence; later chat/UI/evaluation controls remain pending. Each implementation task must update the evidence column with actual test names/results and remaining limitations.

| ID | Invariant / indicator | Planned verification | Evidence |
| --- | --- | --- | --- |
| S01 | Provider key stays server-side; no secrets in logs, frontend bundles, commits, or model context | Secret sentinel tests; ignored .env; bundle/config review | Pending |
| S02 | Upload byte/page/text/time/concurrency limits are enforced | Boundary, corrupt PDF, parser timeout and cleanup tests | Pending |
| S03 | User filenames and IDs cannot access arbitrary files | Traversal and unknown-ID API tests | Pending |
| S04 | Only selected ready documents enter retrieval, prompts, and citations | Two-document same-page tests; readiness and deletion races | Pending |
| S05 | PDF text/metadata/model output are untrusted; no tools execute document instructions | Fenced prompt assertions; metadata excluded; escaped rendering tests | Pending |
| S06 | No verified chip appears before server verification | Event lifecycle and browser tests | Pending |
| S07 | Verification means quote match, not truth; approximate matches are labeled | Exact/fuzzy/negation tests; UI wording review | Pending |
| S08 | Weak retrieval abstains before first answer token | Threshold and empty-retrieval tests | Pending |
| S09 | Streams end clearly; disconnects release resources; no silent midstream retry | Cancellation, provider failure and event-order tests | Pending |
| S10 | Partial ingestion is never queryable; delete removes source and derived data | DB failure, restart cleanup, file and vector deletion tests | Pending |
| S11 | Local service binds loopback; public use is unsupported without auth | Compose/host/CORS/origin configuration checks | Pending |
| S12 | No raw PDF/question/answer content in routine logs | Sentinel logging tests; opt-in local eval artifacts only | Pending |
| S13 | Live provider transmission is explained; fixtures send no content | Mode/config/UI tests; provider spy | Pending |
| S14 | Bounded requests control accidental cost | Input/output caps, concurrency and timeout tests | Pending |
| S15 | Metrics cannot reward withholding every answer or omit failures | Zero-answer/all-failure fixtures; raw denominator assertions | Pending |
| S16 | Gold labels and measured resume claims are not invented | Evidence manifest and human-label provenance review | Pending |

Prompt fencing reduces risk but is not a guarantee against prompt injection. The first project exposes no model tools, credentials, or cross-user data. Dedicated attack generation and classifiers belong to project 3. Uploaded PDFs remain untrusted even when a quote matches them.

Use generated fixtures in source control. Do not commit private course documents, personal interview notes, credentials, or raw private provider responses by default. Keep private evaluation artifacts local and publish only permitted/redacted evidence. Clearly label any released corpus that differs from the privately evaluated corpus.

## T2 evidence

- S02: `test_upload_limits_origin_and_paths`, extraction limit cases, `test_parser_timeout_kills_worker`, `test_memory_watch_rejects_over_budget_child`, and concurrent-ingestion rejection pass. macOS RSS sampling is approximate, not a hard memory ceiling.
- S03: traversal-like filenames become display basenames; UUID validation and unknown-file tests pass.
- S10: transaction rollback, second-batch embedding failure, cancellation, cascading deletion, restart recovery, and late-publication rejection pass against real pgvector.
- S11: foreign-origin rejection, host validation, loopback binding, and single-worker ownership are covered. Public multi-user deployment remains unsupported.
- S12/S13: parser stderr is discarded; provider failure details are replaced by safe codes; fixture-only mode makes no external calls. Full logging audit is still due in T7.
- S04–S09 and S14–S16 are only partially addressed or pending until retrieval, chat, UI, and evaluation exist. No answer-quality metrics are claimed.

## T3 evidence

- S04: `test_citation_sources_require_selected_ready_retrieved_pages` and wrong-document/same-page tests pass. Retrieval itself is T4; callers must use server-derived context.
- S07: exact/approximate labels, invalid thresholds, number/negation changes, repeated quotes, fuzzy budget exhaustion, and explicit semantic counterexamples are tested. No “answer verified” flag exists.
- Source-offset tests prove conservative mapping for Unicode expansions/composition and dehyphenation. These do not prove browser glyph highlighting; T5 must test that separately.
- S06/S08/S09 remain pending for chat streaming and UI. S15/S16 remain pending for real evaluation. Passing 81 regression tests does not establish 90% citation accuracy or 95% answer rate.

## T4 evidence

Scoped cosine retrieval, model mismatch, deleted source, pre-delta abstention, midstream failure, cancellation cleanup, timeout/concurrency caps, explicit live consent, and no-citation outcomes are covered in `test_chat.py`. Provider keys remain server-side. Prompts serialize excerpts as untrusted data and expose no tools. Fencing is not an injection guarantee. UI escape/provisional-state checks remain T5; real metric provenance remains T6/T8.

## T5 evidence

S05/S06/S07/S09/S13 are now exercised in the browser: no model HTML execution; no citation chips on interrupted/cancelled streams; exact versus approximate labels; source highlight fallback; explicit live-mode consent. Tests cover UTF-8/frame boundaries and invalid stream transitions. Full accessibility audits and broader browser support remain T7 concerns; Chromium desktop and mobile viewport are tested here.
