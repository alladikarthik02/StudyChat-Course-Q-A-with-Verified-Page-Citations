# Evaluation protocol

`eval/create_fixture.py` generates original scripted edge cases. `eval/prepare_corpus.py` uploads permitted local PDFs and freezes page text and hashes. `eval/run_eval.py` captures raw streaming answers once. `eval/cite_eval.py` replays those identical outputs with quote verification off/on or exact-only. `eval/calibrate.py` selects a threshold using only development questions.

## Reproducible offline example

```sh
.venv/bin/python eval/create_fixture.py --output tmp/eval-fixture
.venv/bin/python eval/cite_eval.py --dataset tmp/eval-fixture/questions.jsonl --corpus tmp/eval-fixture/corpus.json --records tmp/eval-fixture/records.jsonl --manifest tmp/eval-fixture/manifest.json --quotes on
```

Expected heldout counts: 6 questions, 2 answered, 2 with correct displayed pages. Quote verification off yields 3 answered and 1 correct. The 100% conditional page accuracy with quotes on does NOT satisfy the joint target because answer rate is only 33.3%. This is a deliberately scripted scorer test, not model performance.

## Definitions and boundaries

Every selected question stays in the denominator, including missing outputs, errors and abstentions. An answered question must complete with at least one displayed citation. Page accuracy is the fraction of answered questions whose displayed citations all belong to their labeled acceptable document/page pairs. Answer rate is answered / all questions. Joint success is correct / all questions. Zero answered means undefined conditional accuracy, never 100%. Reports include counts, Wilson intervals, retrieval hit rate and removal reasons. Matching a quote is not proof that it supports the answer's claim; semantic correctness still needs independent review.

Corpus and run artifacts are hash-bound. Keep corpus snapshots and raw outputs private: they contain source text. Commit original question templates and aggregate measurements only for coursework runs. Generated scripted fixtures contain no private sources. Synthetic and human provenance are distinct; `--official` refuses synthetic/fixture evidence and requires the originally planned 20 development / 120 heldout human labels. Recorded provenance cannot itself prove that a person labeled independently.

## Live sequence

1. Configure the private API key in `.env`. Start one local API worker with provider mode `live` and similarity threshold `-1` for uncensored development capture. Live upload and capture require `--live-consent`; extracted text and questions are sent to OpenAI.
2. Prepare the corpus; write labels before generation. Bind the committed coursework template using `eval/bind_coursework.py` for the explicitly synthetic alternative.
3. Capture `--split dev` to a new output directory. Calibrate using its dataset/corpus/records/manifest paths and save the returned threshold.
4. Restart the API with that threshold. Freeze model, prompt, corpus and labels. Capture `--split heldout --calibration PATH` to a new output directory.
5. Replay `--quotes off` and `--quotes on` against the same heldout records. Publish both rates and sample counts regardless of success. Do not tune on heldout outcomes; changes require a new evaluation set.

A budget/credential/provider failure is a failed run, not evidence that the model answered. Partial captures without a finished manifest are retained privately and cannot be presented as a completed evaluation. No synthetic interview notes should be represented as participant research.
