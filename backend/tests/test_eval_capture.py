"""Incomplete or inconsistent streams must never become successful evaluation records."""

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from studychat.prompt import PROMPT_HASH


@pytest.fixture
def capture(monkeypatch):
    directory = Path(__file__).resolve().parents[2] / "eval"
    monkeypatch.syspath_prepend(str(directory))
    spec = importlib.util.spec_from_file_location("eval_capture", directory / "run_eval.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.capture


def run_capture(capture, events, config=None):
    body = (
        "\n\n".join(
            "data: "
            + json.dumps(
                {
                    "seq": i,
                    "request_id": "test",
                    **event,
                }
            )
            for i, event in enumerate(events, 1)
        )
        + "\n\n"
    )
    with httpx.Client(
        base_url="http://testserver",
        transport=httpx.MockTransport(lambda request: httpx.Response(200, text=body)),
    ) as client:
        return capture(
            client, SimpleNamespace(id="q1", question="test", document_ids=[]), False, config
        )


def start():
    return {"event": "start", "prompt_hash": PROMPT_HASH, "model": "test", "threshold": 0.2}


def test_successful_stream(capture):
    result = run_capture(
        capture,
        [
            start(),
            {"event": "delta", "text": "Answer"},
            {"event": "verification"},
            {"event": "done", "outcome": "answered"},
        ],
    )
    assert result["outcome"] == "completed"
    assert result["answer"] == "Answer"


@pytest.mark.parametrize(
    "tail",
    [
        [{"event": "delta", "text": "partial"}],
        [{"event": "done", "outcome": "answered"}],
        [{"event": "error", "code": "failure"}, {"event": "done", "outcome": "answered"}],
        [
            {"event": "verification"},
            {"event": "delta", "text": "late"},
            {"event": "done", "outcome": "answered"},
        ],
        [{"event": "unknown"}],
    ],
)
def test_invalid_stream_fails_closed(capture, tail):
    result = run_capture(capture, [start(), *tail])
    assert result["outcome"] == "error"
    assert result["error_code"] == "capture_failed"


def test_model_drift_is_rejected(capture):
    result = run_capture(
        capture,
        [start(), {"event": "verification"}, {"event": "done", "outcome": "answered"}],
        {"chat_model": "different", "similarity_threshold": 0.2},
    )
    assert result["outcome"] == "error"
