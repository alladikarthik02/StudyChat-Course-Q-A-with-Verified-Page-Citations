# Live synthetic coursework results

The frozen GPT-5.4 mini evaluation completed on 16 previously unrun AI-authored questions after development on eight separate questions. This is a small synthetic benchmark, not independent human research.

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

Quote-on replay retained 37 exact and one approximate quotation and removed one unmatched quotation. Exact-only replay retained 37 quotes and removed two; question-level counts remained unchanged. Off/on scoring uses the exact same raw answers. On this original dataset, the combined target was not met: page accuracy is 8.75 percentage points below 90% while answer rate exceeds 95% by five points.

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

## Fresh cloud chapter evaluation (R2)

After R1 hybrid retrieval was frozen, 20 previously unrun synthetic questions from a separate 51-page cloud-computing chapter were evaluated once using GPT-5.4 mini. Five separate development questions produced five cited answers and four passing page checks. No model switch was warranted by those development failures.

| Measure | Quote off | Quote on | Exact only |
| --- | ---: | ---: | ---: |
| Questions | 20 | 20 | 20 |
| Cited answers | 20 | 20 | 20 |
| Passing page-label checks | 19 | 19 | 19 |
| Cited-answer coverage | 100% | 100% | 100% |
| Page accuracy among answered | 95% | 95% | 95% |
| Errors / abstentions | 0 / 0 | 0 / 0 | 0 / 0 |
| Gold-page retrieval hit rate | 100% | 100% | 100% |

Both numerical learning goals are met on this sample. The 95% Wilson intervals are 83.89–100% for coverage and 76.39–99.11% for page accuracy. This is neither a universal accuracy guarantee nor a semantic-answer benchmark. Different source documents and questions mean the 81.25% and 95% results are not a controlled before/after comparison. The original result remains unchanged.

Quote-on accepted 46 exact and seven approximate quotes and removed one unmatched quote. Exact-only accepted 46 and removed eight; question-level counts stayed unchanged. Question cloud-synthetic-020 failed because it cited page 32 along with pages 36/37 while the frozen acceptable set was 34–37. Source review finds page 32 relevant to iterative precopy migration, but the label and 19/20 score are preserved. This review is an AI diagnostic, not independent human adjudication.

Capture HEAD: a373ba5 (R1 implementation at 5299ae0, followed by handoff documentation). The evaluation-error wording and documentation were edited during capture; retrieval, prompts, models and calibration were unchanged. Model snapshot: gpt-5.4-mini-2026-03-17, low reasoning; selector cap 1,200 tokens, answer cap 4,000. Threshold -1, frozen on five development questions, does not validate abstention on unanswerable inputs. Hybrid retrieval supplies up to 32 candidates to the selector, then at most six to the answer.

Public artifacts: eval/cloud question templates/source hash and eval/results/cloud-mini-synthetic.json with configuration/data/output hashes. Private artifacts: eval/private/cloud corpus, calibration, PDF and raw outputs. The user explicitly approved excerpt transmission to the API; the source PDF is not published. No labels or answers were changed after the run.
