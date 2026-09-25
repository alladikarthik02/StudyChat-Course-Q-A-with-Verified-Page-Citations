# Architecture review and challenge log

Distinguish anticipated risks from failures actually encountered. No implementation failure has been solved yet.

## T0 — findings encountered during design

| Finding | Why it matters | Decision / unresolved tradeoff |
| --- | --- | --- |
| GitHub URL was not visible in the message | Risk of selecting the wrong repository | Extracted StudyChat hyperlink from PDF annotations; remote inspection returned no refs |
| Resume metrics and eight interviews have no supporting artifacts | A build cannot establish historical claims | Track each as unverified; collect evidence and use actual measurements |
| `[p.N]` is ambiguous across PDFs | Correct page number can point to the wrong document | Use server-resolved document aliases plus physical page numbers |
| Post-stream verification occurs after the user sees text | Unverified content could look authoritative | Mark all streamed text provisional; final server result controls chips |
| Exact quotation is not entailment | A misleading answer can quote real text | Label quote status only; document semantic correctness outside metric scope |
| Guide calls for both verbatim quotes and fuzzy ratio >= 0.9 | Fuzzy acceptance can alter a number or negation | Distinguish approximate/exact matches, test counterexamples, report exact-only sensitivity |
| Citation removal can inflate accuracy | Empty answers can look perfectly correct | Report answer rate, conditional page accuracy, and joint success with failures retained |
| One embedding per long page can exceed limits | Truncation loses useful evidence | Split within each page, preserve offsets and physical page identity |
| pypdf and PDF.js extract different text layouts | Backend offsets do not directly identify browser glyphs | Map text separately; show page/quote fallback when highlight is ambiguous |
| Live off/on generations introduce confounding | Metric changes may come from sampling rather than verification | Primary comparison replays the same stored output through both modes |

## Anticipated implementation challenges

- Untrusted PDF parsing can consume memory or hang: use a bounded subprocess and test cleanup. Limits need actual platform verification.
- Failed embedding batches can leave partial records: stage work and publish readiness atomically.
- Client disconnect can leave upstream generation running: propagate cancellation and test resource release.
- Deleting a document while chatting can invalidate references: capture a request snapshot and cancel/fail explicitly if its source becomes unavailable; never substitute another document.
- SSE boundaries do not align with characters or events: incremental UTF-8 decoding and protocol tests.
- Retrieval threshold calibrated on held-out questions leaks information: freeze using the separate development split.
- Prompt injection remains possible despite fencing: no tools/secrets, scoped data, truthful limitations; advanced defense research deferred.

## Interview preparation grounded in this checkpoint

**Why not ask another model to verify citations?** A deterministic string matcher offers inspectable, repeatable quotation checks. It still cannot verify that the quote logically supports the claim.

**How could your evaluation mislead?** Removing difficult citations improves accuracy among remaining answers. Reporting answer rate and joint success exposes that tradeoff. Hand-labeled gold pages and document IDs prevent a wrong-document page match from passing.

**What have you actually built so far?** A reviewed specification and implementation plan. Runtime functionality and performance results are not implemented or measured yet.

## Entry template for subsequent tasks

Task/date; observed failure; minimal reproduction; root cause; alternatives considered; fix; regression test and result; safety impact; remaining limitation; interview explanation. Record actual evidence rather than invented debugging stories.

## T1 — environment and reproducibility

Docker was installed but stopped, and its credential helper was absent from the shell PATH. Started Docker and supplied its bundled executable path; verified real pgvector migration and distance query. pnpm rejected an unapproved esbuild installation script; added the specific esbuild allowance and rebuilt successfully. Locked the same pnpm/Node major versions in CI and the runbook. Neither issue changes retrieval accuracy; both affect whether another developer can reproduce the setup.
