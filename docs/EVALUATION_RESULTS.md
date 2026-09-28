# Live synthetic coursework results

The frozen GPT-5.4 mini evaluation completed on 16 previously unrun AI-authored questions after development on eight separate questions. This is a small synthetic benchmark, not independent human research or the resume's original 120-question study.

| Measure | Quote verification off | Quote verification on |
| --- | ---: | ---: |
| Total questions | 16 | 16 |
| Completed answers with displayed citations | 16 | 16 |
| Answers whose displayed pages all match the frozen labels | 13 | 13 |
| Answer rate | 100% | 100% |
| Page accuracy among answered questions | 81.25% | 81.25% |
| Joint success | 81.25% | 81.25% |
| Errors / abstentions | 0 / 0 | 0 / 0 |
| Retrieval acceptable-page hit rate | 15/16 (93.75%) | 15/16 (93.75%) |

The 95% Wilson intervals are 80.64–100% for answer rate and 56.99–93.41% for page accuracy. These intervals do not account for synthetic-label bias, question dependence or incomplete acceptable-page lists. One sample run does not establish a universal success rate.

Quote-on replay retained 37 exact and one approximate quotation and removed one unmatched quotation. Exact-only replay retained 37 quotes and removed two; question-level counts remained unchanged. Off/on scoring uses the exact same raw answers. No 74%→90% improvement was observed, and the combined target is not met: page accuracy is 8.75 percentage points below 90% while answer rate exceeds 95% by five points.

## Frozen configuration and provenance

- Model: `gpt-5.4-mini-2026-03-17`; low reasoning; 4,000-token total output cap.
- Embeddings: `text-embedding-3-small`, 1,536 dimensions.
- Code at heldout capture: `794b795` (T7).
- Threshold: -1, selected on development data after no candidate met both targets. This disables similarity gating on nonempty context; it is not a validated rejection threshold for unanswerable questions.
- Retrieval: four semantic chunks plus up to two neighboring-page chunks, six maximum.
- Sources: two local lecture PDFs, 166 and 122 physical pages. No OCR or visual understanding is applied to diagrams.
- Source hashes and question templates: `eval/coursework/`.
- Aggregate report and hashes: `eval/results/coursework-mini-synthetic.json`.
- Private corpus/labels, frozen calibration and raw outputs: ignored `eval/private/coursework/`.

Development run 1 had 6/8 answered and 4/6 correct pages; run 2 had 8/8 answered and 6/8 correct pages after prompt and retrieval changes. Development runs were captured while those changes were uncommitted; their prompt hashes and local artifacts identify the configuration. The heldout run used the committed T7 code. Labels were not altered after seeing outputs.

## Failure review and limitations

AI review of all 16 raw answers found three failed page-label checks:

- Question 009: retrieval missed the backpropagation slide. The answer gave general shared-weight notation instead of the requested recurrent transpose detail. This is a substantive retrieval/answer failure, despite its quotes matching retrieved text.
- Question 018: the answer included physical page 100, which appears relevant to embeddings for unseen nodes but was absent from the frozen acceptable-page list.
- Question 023: the answer included physical page 114, which appears relevant to the enhancer pipeline but was absent from the frozen acceptable-page list.

The latter two indicate possible label incompleteness, not permission to revise the locked score. Independent review should adjudicate them in a separately versioned dataset. The review was performed by the coding assistant, not a human annotator, and is not a separate entailment accuracy metric. The original planned 30-answer human spot-check and eight classmate interviews were not performed.

Next experiments, if further accuracy work is requested: improve retrieval for mathematical notation and diagram-heavy slides; independently audit labels across all equivalent pages; add unanswerable questions; compare models on development data; then evaluate a new untouched set. The current heldout set must not be reused as untouched evidence after tuning against these failures.
