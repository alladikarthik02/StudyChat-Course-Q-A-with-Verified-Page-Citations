"""Standalone isolated parser. Only bounded JSON is returned; parser logs are discarded."""

import json
import logging
import resource
import sys


def main():
    path, max_pages, max_chars, memory_mb = sys.argv[1:]
    memory = int(memory_mb) * 1024 * 1024
    if sys.platform == "linux":
        resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
    resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
    logging.disable(logging.CRITICAL)
    from pypdf import PdfReader

    try:
        reader = PdfReader(path, strict=True)
        if reader.is_encrypted:
            raise ValueError("encrypted_pdf")
        if len(reader.pages) > int(max_pages):
            raise ValueError("page_limit")
        pages = []
        total = 0
        for page in reader.pages:
            text = (page.extract_text() or "").replace("\x00", "")
            total += len(text)
            if total > int(max_chars):
                raise ValueError("text_limit")
            pages.append(text)
        if not any(text.strip() for text in pages):
            raise ValueError("no_extractable_text")
        metadata = reader.metadata or {}
        title = str(metadata.get("/Title", ""))[:1000]
        subject = str(metadata.get("/Subject", ""))[:1000]
        print(json.dumps({"pages": pages, "metadata": f"{title}\n{subject}".strip()}))
    except ValueError as exc:
        code = str(exc)
        allowed = {"encrypted_pdf", "page_limit", "text_limit", "no_extractable_text"}
        print(json.dumps({"error": code if code in allowed else "invalid_pdf"}))
    except MemoryError:
        print(json.dumps({"error": "parser_resource_limit"}))
    except Exception:
        print(json.dumps({"error": "invalid_pdf"}))


if __name__ == "__main__":
    main()
