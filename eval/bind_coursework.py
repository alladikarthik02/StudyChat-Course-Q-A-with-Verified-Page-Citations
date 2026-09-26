"""Bind committed synthetic question templates to an uploaded private corpus."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from studychat.evaluation import Corpus, Question, validate_dataset  # noqa: E402


def bind(template, sources, corpus):
    expected = {s["filename"]: s["sha256"] for s in sources}
    docs = {d.filename: d for d in corpus.documents}
    questions = []
    for row in template:
        doc = docs[row["source_filename"]]
        if doc.pdf_sha256 != expected[doc.filename]:
            raise ValueError("source_pdf_hash_mismatch")
        questions.append(
            Question(
                id=row["id"],
                split=row["split"],
                question=row["question"],
                document_ids=[doc.document_id],
                gold=[{"document_id": doc.document_id, "page": p} for p in row["gold_pages"]],
                label_source="synthetic",
                annotation_note=row["annotation_note"],
            )
        )
    validate_dataset(questions, corpus)
    return questions


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).parent / "coursework"
    rows = [
        json.loads(line) for line in (root / "questions.template.jsonl").read_text().splitlines()
    ]
    questions = bind(
        rows,
        json.loads((root / "sources.json").read_text()),
        Corpus.model_validate_json(args.corpus.read_text()),
    )
    with args.output.open("x") as file:
        file.write("".join(q.model_dump_json() + "\n" for q in questions))
    print(f"Bound {len(questions)} synthetic questions; no human labels claimed.")
