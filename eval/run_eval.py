"""Capture fresh local-app answers; scoring off/on reuses these exact outputs."""

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from prepare_corpus import local_url  # noqa: E402
from studychat.citations import VERIFIER_VERSION  # noqa: E402
from studychat.evaluation import (  # noqa: E402
    Corpus,
    Question,
    digest,
    load_jsonl,
    validate_dataset,
)
from studychat.prompt import PROMPT_HASH  # noqa: E402
from studychat.text import NORMALIZATION_VERSION  # noqa: E402


def capture(client, question, live_consent):
    record = {
        "question_id": question.id,
        "outcome": "error",
        "answer": "",
        "aliases": {},
        "retrieval": [],
        "error_code": None,
    }
    seq = 0
    request_id = None
    terminal = False
    final_kind = None
    try:
        with client.stream(
            "POST",
            "/chat",
            json={
                "question": question.question,
                "document_ids": [str(i) for i in question.document_ids],
                "live_consent": live_consent,
            },
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line.startswith("data:"):
                    continue
                event = json.loads(line[5:].strip())
                if (
                    terminal
                    or event["seq"] != seq + 1
                    or (request_id and request_id != event["request_id"])
                ):
                    raise ValueError("stream_sequence_error")
                seq = event["seq"]
                request_id = event["request_id"]
                kind = event["event"]
                if seq == 1 and kind != "start":
                    raise ValueError("missing_start")
                if kind == "start" and event.get("prompt_hash") != PROMPT_HASH:
                    raise ValueError("prompt_version_mismatch")
                if kind == "delta":
                    record["answer"] += event["text"]
                    if len(record["answer"]) > 100000:
                        raise ValueError("answer_limit")
                if "retrieval" in event:
                    record["retrieval"] = event["retrieval"]
                    record["aliases"] = {
                        row["alias"]: row["document_id"] for row in event["retrieval"]
                    }
                if kind in {"verification", "abstain", "error"}:
                    final_kind = kind
                if kind == "error":
                    record["error_code"] = event.get("code", "stream_error")
                if kind == "done":
                    if final_kind is None:
                        raise ValueError("missing_final_state")
                    terminal = True
                    outcome = event["outcome"]
                    record["outcome"] = (
                        "completed"
                        if outcome in {"answered", "no_verified_citations"}
                        else "abstained"
                        if outcome == "abstained"
                        else "error"
                    )
            if not terminal:
                raise ValueError("incomplete_stream")
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        record["outcome"] = "error"
        record["error_code"] = "capture_failed"
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", type=local_url, default="http://127.0.0.1:8000")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--split", choices=["dev", "heldout"], required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--calibration", type=Path)
    parser.add_argument(
        "--exploratory",
        action="store_true",
        help="Allow an explicitly untuned heldout run; not official evidence",
    )
    parser.add_argument("--live-consent", action="store_true")
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Use a new output directory; prior runs are never overwritten")
    questions = load_jsonl(args.dataset, Question)
    corpus = Corpus.model_validate_json(args.corpus.read_text())
    validate_dataset(questions, corpus)
    selected = [q for q in questions if q.split == args.split]
    if not selected:
        parser.error("Empty split")
    if args.split == "heldout" and not args.calibration and not args.exploratory:
        parser.error("Freeze a dev calibration first, or explicitly use --exploratory")
    started = datetime.now(timezone.utc).isoformat()
    with httpx.Client(base_url=args.api_url, timeout=180) as client:
        response = client.get("/config")
        response.raise_for_status()
        config = response.json()
        if config["provider_mode"] == "live" and not args.live_consent:
            parser.error("Live API calls require --live-consent")
        if args.split == "dev" and config["similarity_threshold"] != -1:
            parser.error("Collect uncensored dev answers with STUDYCHAT_SIMILARITY_THRESHOLD=-1")
        if args.calibration:
            calibration = json.loads(args.calibration.read_text())
            expected = {
                "mode": config["provider_mode"],
                "chat_model": config["chat_model"],
                "prompt_hash": PROMPT_HASH,
                "dataset_sha256": digest(args.dataset),
                "corpus_sha256": digest(args.corpus),
                "selected_threshold": config["similarity_threshold"],
            }
            if any(calibration.get(k) != v for k, v in expected.items()):
                parser.error(
                    "Calibration does not match corpus, dataset, mode, model, prompt, "
                    "or configured threshold"
                )
        for doc in corpus.documents:
            response = client.get(f"/documents/{doc.document_id}/file")
            response.raise_for_status()
            if hashlib.sha256(response.content).hexdigest() != doc.pdf_sha256:
                parser.error("Source PDF changed since labeling")
            if doc.embedding_model != config["embedding_model"]:
                parser.error("Corpus embedding model differs from app; reprepare it")
        args.output_dir.mkdir(parents=True, mode=0o700)
        records_path = args.output_dir / "records.jsonl"
        with records_path.open("x") as file:
            for question in selected:
                record = capture(client, question, args.live_consent)
                file.write(json.dumps(record) + "\n")
                file.flush()
                print(f"{question.id}: {record['outcome']}")
        records_path.chmod(0o600)
    root = Path(__file__).resolve().parents[1]
    manifest = {
        "schema_version": 1,
        "mode": config["provider_mode"],
        "origin": "local_app_stream_capture",
        "dataset_sha256": digest(args.dataset),
        "corpus_sha256": digest(args.corpus),
        "records_sha256": digest(records_path),
        "git_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip(),
        "started_at": started,
        "chat_model": config["chat_model"],
        "embedding_model": config["embedding_model"],
        "prompt_hash": PROMPT_HASH,
        "generation_threshold": config["similarity_threshold"],
        "threshold_label": config["threshold_label"],
        "max_output_tokens": config["max_output_tokens"],
        "dependency_hashes": {
            str(p.relative_to(root)): digest(p)
            for p in [root / "backend/requirements.txt", root / "frontend/pnpm-lock.yaml"]
        },
        "normalization_version": NORMALIZATION_VERSION,
        "verifier_version": VERIFIER_VERSION,
        "split": args.split,
        "calibration_sha256": digest(args.calibration) if args.calibration else None,
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Saved raw outputs and provenance. Score off/on using these same records.")


if __name__ == "__main__":
    main()
