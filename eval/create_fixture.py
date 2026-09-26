"""Generate scripted edge cases, NOT model performance or human-labeled course data."""

import argparse
import hashlib
import io
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from reportlab.pdfgen import canvas

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from studychat.citations import VERIFIER_VERSION  # noqa: E402
from studychat.evaluation import digest  # noqa: E402
from studychat.prompt import PROMPT_HASH  # noqa: E402
from studychat.text import NORMALIZATION_VERSION  # noqa: E402

DOC = "11111111-1111-1111-1111-111111111111"
PAGES = ["Gravity attracts objects with mass.", "Inertia resists changes in motion."]


def create_fixture(output: Path):
    output.mkdir(parents=True, exist_ok=True)
    stream = io.BytesIO()
    pdf = canvas.Canvas(stream, invariant=True)
    for text in PAGES:
        pdf.drawString(40, 700, text)
        pdf.showPage()
    pdf.save()
    corpus = {
        "kind": "fixture",
        "provenance": (
            "Original synthetic physics statements and scripted edge cases; "
            "not real evaluation evidence."
        ),
        "documents": [
            {
                "document_id": DOC,
                "filename": "synthetic-physics.pdf",
                "pdf_sha256": hashlib.sha256(stream.getvalue()).hexdigest(),
                "embedding_model": "fixture-hash-v1",
                "pages": PAGES,
                "page_text_sha256": [hashlib.sha256(t.encode()).hexdigest() for t in PAGES],
            }
        ],
    }
    (output / "corpus.json").write_text(json.dumps(corpus, indent=2) + "\n")
    questions = []
    for name, split, page in [
        ("dev-a", "dev", 1),
        ("dev-b", "dev", 2),
        ("correct", "heldout", 1),
        ("wrong-page", "heldout", 2),
        ("mixed", "heldout", 1),
        ("error", "heldout", 1),
        ("uncited", "heldout", 2),
        ("abstained", "heldout", 1),
    ]:
        questions.append(
            {
                "id": name,
                "split": split,
                "question": f"Synthetic case {name}: explain page {page}.",
                "document_ids": [DOC],
                "gold": [{"document_id": DOC, "page": page}],
                "label_source": "synthetic",
                "annotation_note": "Scripted test case, not a human label.",
            }
        )
    (output / "questions.jsonl").write_text("".join(json.dumps(q) + "\n" for q in questions))

    def citation(page, quote):
        return f"[D1 p.{page} {json.dumps(quote)}]"

    answers = [
        citation(1, PAGES[0]),
        citation(2, PAGES[1]),
        citation(1, PAGES[0]),
        citation(1, PAGES[1]),
        citation(1, PAGES[0]) + " " + citation(2, "Invented quotation."),
        "",
        "A response without a citation.",
        "",
    ]
    records = []
    for q, answer in zip(questions, answers, strict=True):
        outcome = (
            "error"
            if q["id"] == "error"
            else "abstained"
            if q["id"] == "abstained"
            else "completed"
        )
        similarity = 0.2 if q["id"] == "dev-b" else 0.1 if q["id"] == "abstained" else 0.8
        records.append(
            {
                "question_id": q["id"],
                "outcome": outcome,
                "answer": answer,
                "aliases": {"D1": DOC},
                "retrieval": [
                    {"document_id": DOC, "page": i, "alias": "D1", "similarity": similarity}
                    for i in (1, 2)
                ],
                "error_code": "scripted_provider_error" if outcome == "error" else None,
            }
        )
    (output / "records.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))
    root = Path(__file__).resolve().parents[1]
    manifest = {
        "schema_version": 1,
        "mode": "fixture",
        "origin": "scripted_edge_cases_not_model_generation",
        "dataset_sha256": digest(output / "questions.jsonl"),
        "corpus_sha256": digest(output / "corpus.json"),
        "records_sha256": digest(output / "records.jsonl"),
        "git_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip(),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "chat_model": "scripted-fixture-v1",
        "embedding_model": "fixture-hash-v1",
        "prompt_hash": PROMPT_HASH,
        "generation_threshold": -1,
        "threshold_label": "fixture_uncensored",
        "max_output_tokens": 1200,
        "dependency_hashes": {
            str(p.relative_to(root)): digest(p)
            for p in [root / "backend/requirements.txt", root / "frontend/pnpm-lock.yaml"]
        },
        "normalization_version": NORMALIZATION_VERSION,
        "verifier_version": VERIFIER_VERSION,
        "split": "all",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("tmp/eval-fixture"))
    create_fixture(parser.parse_args().output)
