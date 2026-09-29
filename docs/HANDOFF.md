# StudyChat handoff

The first project is implemented and tested. The user-authorized synthetic evaluation is complete. The original 90% page-accuracy target and human-study resume claims are not established.

## Use the app

Start the database and backend using RUNBOOK.md, then start the frontend. Open http://127.0.0.1:5173. Select a ready PDF, acknowledge the live-data consent, enter a question, and open a citation chip to inspect the page. The two coursework decks and a cloud-computing chapter have been imported locally. Live questions and new uploads incur API charges.

The private environment currently selects `gpt-5.4-mini-2026-03-17`, low reasoning, 4,000 maximum output tokens, and the synthetic-development threshold of -1. The threshold preserves coverage on this small benchmark and does not establish reliable abstention on unanswerable questions. To use the offline fixture, set `STUDYCHAT_PROVIDER_MODE=fixture`, restart the backend, and reupload sources to create matching fixture embeddings. A production/live document cannot be queried using fixture embeddings.

Docker, backend and frontend were started for the handoff. To stop later, stop the two terminal servers and use `docker compose stop`. This retains the database. `docker compose down --volumes` erases the database and requires migrations and reuploading sources on restart.

## Validation and measured results

- 118 backend test cases passed with the dedicated real PostgreSQL/pgvector test database.
- 11 frontend unit tests, seven Chromium browser tests and the production build passed.
- Clean GitHub CI for the T7 code passed: https://github.com/alladikarthik02/StudyChat-Course-Q-A-with-Verified-Page-Citations/actions/runs/36476532843
- 16 untouched synthetic evaluation questions produced 16 cited answers and 13 passing page-label checks: 100% answer rate, 81.25% page accuracy. Both quote-off and quote-on replay produced those counts. No semantic answer-accuracy percentage is claimed.

Read EVALUATION_RESULTS.md for confidence intervals, exact-only results, failures and provenance. RESUME_EVIDENCE.md contains defensible replacement bullets. INTERVIEW_GUIDE.md explains actual decisions and challenges.

## File locations and privacy

Source PDFs, extracted text, corpus snapshots, calibration and raw model outputs remain in ignored `eval/private/coursework` and `eval/private/cloud`. The API key remains in ignored `.env`. Code, original synthetic question templates, source hashes, aggregate results and documentation are committed. No private PDF or raw provider answer is published.

The frozen heldout run is `eval/private/coursework/live-mini-heldout`. Replay it with `eval/cite_eval.py`, passing its records/manifest, `questions-live-mini.jsonl` and `corpus-live-mini.json`, with `--quotes off` or `--quotes on`. The original PDFs are not distributed, so public reproducibility uses the original generated fixture instead; private coursework reproduction requires the same permitted PDF versions and hashes.

## Remaining limits

This is a single-user local application, without public authentication, OCR or multi-user access controls. PDF figures may contain information absent from extracted text. Quote matching cannot prove entailment. Synthetic labels may omit other valid pages; the locked score was not revised after looking at outputs. Eight interviews, 120 human-written labels and a 30-answer human audit were not performed. A new independent evaluation is required after any tuning based on heldout failures.

## Current continuation checkpoint

R1 is committed and pushed as `5299ae0`: hybrid retrieval, bounded relevance selection, synthetic cloud templates and regression coverage. Local validation passed: 117 backend tests plus one new database regression (118 cases), 11 frontend tests, seven browser tests, build and Ruff.

The five cloud development questions completed (5/5 cited answers, 4/5 passing page labels). They ran against the R1 working changes before commit; their manifest records the preceding HEAD, so they are explicitly development-only evidence. The failing response included additional relevant pages outside its frozen labels. No stronger-model benefit was established.

R2's 20-question heldout capture has not run: automatic approval review requires explicit authorization to transmit excerpts from Cloud Computing - UNIT 2.pdf to OpenAI. The approval question is pending. Do not bypass that block. Once approved, use the existing private questions/corpus/calibration and a new heldout output directory with run_eval.py. Do not relabel or retune after seeing those outputs. Preserve the original 13/16 result separately. Backend and frontend are running on ports 8000 and 5173. Avoid live questions against the cloud chapter until the pending source-transmission approval is granted.
