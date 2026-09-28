# Active answer model

On 2026-09-27 the user requested GPT-5.5. The live default is now pinned to `gpt-5.5-2026-04-23`, with explicit low reasoning effort and a 4,000-token total output cap (including reasoning). The existing Responses streaming endpoint and deterministic citation verifier remain in use. Embeddings remain `text-embedding-3-small`; changing the answer model alone does not require different embeddings.

The private `.env` model/output-cap settings were updated without exposing or committing its key. Fixture mode remains selected; Docker remains stopped. No paid model call was made for this change. Six mocked provider/chat tests passed, covering request shape, stream completion, disconnect and HTTP errors. Live access, latency and quality remain unverified pending API credits and a new development/evaluation run. Existing model-specific calibration must not be reused.

At standard pricing of $5 per million input and $30 per million output tokens, an assumed 5,000 input and 1,000 total output tokens cost $0.055 per request ($1.32 for 24). At the 4,000-output-token cap with the same input, 24 requests would cost $3.48. Actual input sizes and repeated runs change costs; this is not a $5 hard spending limit. A 140-question run at the smaller assumption would cost $7.70 plus embeddings. Reasoning consumes output tokens, and exceeding the cap produces an incomplete response, which the app treats as failure rather than verified success.

Official references: [GPT-5.5 pricing and snapshot](https://developers.openai.com/api/docs/models/gpt-5.5), [migration guidance](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-5.5). Historical T4 notes describe the prior GPT-4.1 mini configuration; this document records the active model change. Higher model capability does not establish the resume metrics without measurement.

## Current selection: GPT-5.4 mini

The user subsequently selected `gpt-5.4-mini-2026-03-17`. It replaces GPT-5.5 as the active default and private environment override, retaining explicit low reasoning and the 4,000-token output cap. Six mocked provider tests pass. Pricing is $0.75 per million input tokens and $4.50 per million output tokens. At 5,000 input / 1,000 total output tokens, 24 questions are approximately $0.20; at 4,000 output tokens, approximately $0.52, excluding embeddings/retries. These are estimates rather than a spending limit. The prior GPT-5.5 section records the superseded choice. Reference: https://developers.openai.com/api/docs/models/gpt-5.4-mini
