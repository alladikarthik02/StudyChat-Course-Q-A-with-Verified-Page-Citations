# Synthetic coursework evaluation

These 24 AI-authored questions use two local CSCI 566 lecture decks: 8 development and 16 evaluation questions. They are a small engineering benchmark, not 120 independently human-labeled questions or evidence of interviews. Labels were written from extracted lecture text before observing generated answers. Acceptable-page lists may be incomplete; repeated slides can support the same answer. Page numbers are physical PDF pages, not slide numbers printed on the page.

The user authorized local testing and explicitly requested that PDFs remain local. PDFs, extracted text, credentials, generated answers and uploaded document IDs are under ignored paths. `sources.json` contains only filenames, page counts and SHA-256 hashes. The question template contains original questions and page labels, not copied lecture passages.

After uploading these exact PDFs with `eval/prepare_corpus.py --kind synthetic`, run:

```sh
.venv/bin/python eval/bind_coursework.py --corpus eval/private/coursework/corpus.json --output eval/private/coursework/questions.jsonl
```

The binder checks each PDF hash and maps filenames to the local API's document IDs. A different PDF version requires relabeling. The PDFs are not bundled, so another developer needs their own permitted copies for this benchmark; the fully reproducible generated fixture remains available without them.
