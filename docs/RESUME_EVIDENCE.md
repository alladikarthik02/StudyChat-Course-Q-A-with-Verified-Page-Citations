# Resume alignment and evidence ledger

Source: first project only, Karthik_Alladi_OpenAI_SWE_EmergingTalent_Applied_FullStack.pdf. All statements below are currently unverified claims or planned capabilities.

| Resume element | Implementation/evidence needed | Status |
| --- | --- | --- |
| End-to-end React and TypeScript app | Running UI and browser test | Pending T1/T5/T7 |
| Python FastAPI, OpenAI streaming, PostgreSQL/pgvector | Real DB integration, provider adapter, SSE tests and live smoke | Foundation/ingestion tested; live provider and streaming pending T4 |
| Eight classmates reported wrong page numbers | Actual anonymized participant notes and accurate summary | Not supplied |
| 120 questions with hand-checked gold pages | Corpus manifest, permitted PDFs, blind human annotations | Not supplied |
| About one in four wrong-page citations / 74% baseline | Paired unfiltered scorer output with explicit denominator | Not measured |
| 90% citation accuracy | Verified-mode output and per-question audit | Not measured |
| 95% of answerable questions answered | Answer-rate numerator/denominator including errors and abstentions | Not measured |

Do not round or change denominator definitions to force a match. The “1 in 4” wording is approximate and must agree with the measured baseline. Resume phrasing must explain whether accuracy is among answered questions. Keep reproducible scripts and permitted raw evidence together; do not publish private documents to satisfy that requirement.

No performance or interview claims from projects 2–4 are part of StudyChat's completion criteria.

## Engineering targets and improvement policy

The user's requested direction is to meet or exceed the first project's resume metrics, or get as close as real evidence supports. Treat this as an engineering objective, not a guarantee about an unseen corpus.

- Target verified page accuracy among answered questions of at least 90%, simultaneously with answer rate of at least 95%, on the same frozen 120-question answerable set.
- At least 114 of 120 questions must receive completed answers with surviving citations to meet the answer-rate target. If exactly 114 are answered, at least 103 must have every displayed citation in the gold document/page set to meet the accuracy target. Print exact counts and unrounded rates alongside rounded display values.
- Measure the unfiltered baseline honestly. The 74% and “1 in 4” claims are reference values, not targets to force by degrading a stronger baseline. Explain paired changes even if the observed baseline differs.
- Treat 120 human-labeled questions and eight real classmate reports as evidence requirements; synthetic questions and invented interviews do not substitute for them.
- “Close” is descriptive, not a newly invented passing threshold: report each gap in percentage points and raw question counts. A result below either target remains below target even if the other metric exceeds it.

For development runs, record retrieval gold-page recall@6, abstention rate, quote acceptance rate, citation removal reasons, provider failures, page accuracy, answer rate, and joint success. Gold-page recall@6 means the fraction of questions for which any accepted gold document/page appears among the six retrieved chunks. It is a diagnostic, not proof that enough context exists to answer.

Classify misses before changing the system: extraction/page mapping, retrieval miss, premature abstention, malformed citation, quotation mismatch, misleading claim, or infrastructure failure. Improve the responsible component, add a regression test, and run the paired development evaluation again. Log configuration changes and both accuracy and answer-rate effects. Do not lower quote standards merely to increase answer rate.

Tune only on development data; freeze configuration before final held-out scoring. If held-out results prompt further tuning, disclose that the set is now development evidence and use a fresh blindly labeled holdout for a new generalization claim. Preserve all recorded runs rather than selecting a favorable sample. Report sample-size uncertainty; a 120-question result is a corpus-specific observation, not a universal performance guarantee.

Product implementation completion and metric validation are separate statuses. Do not mark resume alignment complete until real evidence supports the final wording. If targets remain unmet, document the gap and next experiment and revise the resume to observed results.

## Evidence through T3

The React scaffold builds; real pgvector ingestion and internal citation verification pass regression tests. The 81-test suite uses generated fixtures, not the 120-question human-labeled corpus. It therefore establishes implementation behavior, not the resume's empirical accuracy/answer-rate claims. Human interviews, development labels, held-out labels, and live runs are still outstanding.
