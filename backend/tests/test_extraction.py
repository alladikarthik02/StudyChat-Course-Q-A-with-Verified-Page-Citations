import asyncio

import pytest
from studychat.config import Settings
from studychat.extraction import IngestionError, extract_pdf
from studychat.text import normalize, split_page


def test_chunk_offsets_overlap_and_cover_page():
    text = "abcde " * 1000
    chunks = split_page(text)
    assert chunks[0]["start_offset"] == 0
    assert chunks[-1]["end_offset"] == len(text)
    for chunk in chunks:
        assert chunk["text"] == text[chunk["start_offset"] : chunk["end_offset"]]
        assert len(chunk["text"]) <= 2400
    for left, right in zip(chunks, chunks[1:]):
        assert left["end_offset"] - right["start_offset"] == 240
    assert split_page("   ") == []
    with pytest.raises(ValueError):
        split_page(text, size=10, overlap=10)


def test_normalization():
    assert normalize("  The ﬁrst inter-\nnational\t lecture ") == "The first international lecture"


async def test_parser_timeout_kills_worker(tmp_path, pdf_bytes):
    path = tmp_path / "source.pdf"
    path.write_bytes(pdf_bytes())
    with pytest.raises(IngestionError, match="parser_timeout"):
        await extract_pdf(path, Settings(parse_timeout_seconds=0.00001))


async def test_cancel_parser_reaps_process(tmp_path, pdf_bytes, monkeypatch):
    path = tmp_path / "source.pdf"
    path.write_bytes(pdf_bytes())
    original = asyncio.create_subprocess_exec
    processes = []

    async def capture(*args, **kwargs):
        process = await original(*args, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", capture)
    task = asyncio.create_task(extract_pdf(path, Settings()))
    while not processes:
        await asyncio.sleep(0.001)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert processes[0].returncode is not None


async def test_memory_watch_rejects_over_budget_child(monkeypatch):
    from types import SimpleNamespace

    from studychat.extraction import memory_watch

    fake = SimpleNamespace(memory_info=lambda: SimpleNamespace(rss=1025))
    monkeypatch.setattr("studychat.extraction.psutil.Process", lambda pid: fake)
    with pytest.raises(IngestionError, match="parser_resource_limit"):
        await memory_watch(SimpleNamespace(pid=123, returncode=None), 1024)
