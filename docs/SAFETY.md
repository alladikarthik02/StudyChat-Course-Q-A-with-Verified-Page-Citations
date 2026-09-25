# Safety requirements and evidence

All requirements are currently **specified, not tested**. Each implementation task must update the evidence column with actual test names/results and remaining limitations.

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
