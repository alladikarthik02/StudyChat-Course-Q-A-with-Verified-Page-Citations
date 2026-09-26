"""Upload permitted PDFs to the local app and save a private page/hash manifest for labeling."""

import argparse
import asyncio
import hashlib
import json
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from studychat.config import Settings  # noqa: E402
from studychat.extraction import extract_pdf  # noqa: E402


def local_url(url):
    parsed = urlparse(url)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise ValueError("Use the local StudyChat API, never an arbitrary remote upload target")
    return url.rstrip("/")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default="http://127.0.0.1:8000", type=local_url)
    parser.add_argument("--pdf", type=Path, action="append", required=True)
    parser.add_argument("--kind", choices=["fixture", "synthetic", "human"], required=True)
    parser.add_argument(
        "--provenance",
        required=True,
        help="Permissions/source description; no personal identifiers",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--live-consent", action="store_true", help="Allow extracted PDF text to be sent to OpenAI"
    )
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; use a new manifest path")
    documents = []
    with httpx.Client(base_url=args.api_url, timeout=120) as client:
        config = client.get("/config")
        config.raise_for_status()
        config = config.json()
        if config["provider_mode"] == "live" and not args.live_consent:
            parser.error("Live mode requires --live-consent")
        for path in args.pdf:
            if path.stat().st_size > 20 * 1024 * 1024:
                parser.error("PDF exceeds upload limit")
            original = path.read_bytes()
            extracted = asyncio.run(extract_pdf(path.resolve(), Settings(provider_mode="fixture")))
            response = client.post(
                "/documents",
                files={"file": (path.name, original, "application/pdf")},
                headers={"X-StudyChat-Consent": "yes"} if args.live_consent else {},
            )
            response.raise_for_status()
            doc_id = response.json()["id"]
            deadline = time.monotonic() + 180
            while True:
                response = client.get(f"/documents/{doc_id}")
                response.raise_for_status()
                row = response.json()
                if row["state"] == "failed":
                    raise RuntimeError(f"Ingestion failed: {row['error_code']}")
                if row["state"] == "ready":
                    break
                if time.monotonic() > deadline:
                    raise TimeoutError("Ingestion deadline")
                time.sleep(0.2)
            pages = extracted["pages"]
            documents.append(
                {
                    "document_id": doc_id,
                    "filename": path.name,
                    "pdf_sha256": hashlib.sha256(original).hexdigest(),
                    "embedding_model": row["embedding_model"],
                    "pages": pages,
                    "page_text_sha256": [hashlib.sha256(t.encode()).hexdigest() for t in pages],
                }
            )
            print(f"Prepared document {doc_id}: {len(pages)} pages")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {"kind": args.kind, "provenance": args.provenance, "documents": documents}, indent=2
        )
        + "\n"
    )
    args.output.chmod(0o600)
    print("Corpus prepared. Write blind gold labels before running generation.")


if __name__ == "__main__":
    main()
