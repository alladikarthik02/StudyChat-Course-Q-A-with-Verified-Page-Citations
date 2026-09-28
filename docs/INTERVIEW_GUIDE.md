# StudyChat interview preparation

These are practice questions based on actual implementation challenges, not transcripts of past interviews.

## How did you prevent partial uploads from appearing in search?

PDF parsing runs in a bounded child process. Embeddings are computed before pages/chunks and the ready state are published transactionally. Retrieval accepts only selected ready documents. Failed or interrupted jobs are recovered or cleaned up on startup. Tests simulate embedding failure, cancellation, rollback and deletion racing publication.

## What does a verified citation guarantee?

It guarantees a quoted span matches text on an authorized retrieved physical page, exactly after normalization or approximately under conservative limits. It does not prove the claim follows from the quote. Approximate matches are labeled, number/negation changes are guarded, and semantic counterexamples are tested. A human audit is needed to measure entailment.

## Why can backend and browser highlighting disagree?

pypdf and PDF.js extract and segment text differently. The backend tracks Unicode normalization offsets; the browser independently maps grapheme-normalized text into DOM ranges. When a quote is ambiguous or unavailable, the viewer opens the page and displays the quote without inventing a highlight. Actual PDF rendering and ambiguity cases are covered in browser tests.

## What did the first real evaluation reveal?

Eight synthetic development questions exposed grouped citation syntax, a quote shortened into a word absent from the source, and retrieval missing a neighboring slide's explanation. Explicit citation examples and limited adjacent-page context improved development coverage from 6/8 to 8/8 and correct-page answers from 4/8 to 6/8. The sample is small, synthetic and used for tuning, so it cannot establish generalization.

## Why report both page accuracy and answer rate?

A system can obtain high conditional accuracy by withholding nearly all answers. Every question remains in the denominator, including failed requests and missing outputs. Report correct/answered, answered/total and correct/total together, with raw counts and uncertainty. The scripted scorer fixture reaches 100% conditional accuracy on only two of six questions and correctly fails the combined target.

## How did you keep evaluation independent of tuning?

Questions were split before model generation. Only the eight development outputs informed changes and threshold selection; settings were frozen before the 16 evaluation requests. Off/on scoring reuses identical raw outputs. Hashes tie corpus, questions, outputs and calibration together. Gold pages never enter prompts or quote verification. Labels are explicitly AI-authored, not human-blind evidence; incomplete acceptable-page lists remain a limitation.

## What breaks in production?

This is a local single-user app. It lacks account isolation, public authentication, OCR and production hosting operations. It intentionally permits one service owner, bounds requests, and exposes no model tools. Scaling would require durable job orchestration, authenticated per-owner document access and operational monitoring. None of those capabilities are claimed here.
