"""Hand-derived denominators and provenance checks for evaluation tooling."""

import importlib.util
from pathlib import Path

import pytest
from studychat.evaluation import calibrate, load_bundle, require_official_evidence, score


@pytest.fixture
def bundle(tmp_path):
    path = Path(__file__).resolve().parents[2] / "eval/create_fixture.py"
    spec = importlib.util.spec_from_file_location("create_fixture", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.create_fixture(tmp_path)
    return load_bundle(
        *(
            tmp_path / name
            for name in ("questions.jsonl", "corpus.json", "records.jsonl", "manifest.json")
        )
    )


def test_paired_denominators(bundle):
    off = score(bundle, "heldout", "off")
    on = score(bundle, "heldout", "on")
    assert (off["total"], off["answered"], off["correct"]) == (6, 3, 1)
    assert (on["total"], on["answered"], on["correct"]) == (6, 2, 2)
    assert on["page_accuracy_among_answered"] == 1
    assert on["answer_rate"] == pytest.approx(1 / 3)
    assert not on["target_met"]
    assert on["errors"] == on["abstentions"] == 1


def test_missing_records_stay_in_denominator(bundle):
    bundle.records.clear()
    result = score(bundle, "heldout", "on")
    assert result["total"] == result["errors"] == 6
    assert result["answered"] == 0
    assert result["page_accuracy_among_answered"] is None
    assert result["page_accuracy_95pct_interval"] is None
    assert not result["target_met"]


def test_calibration_never_uses_heldout_answers(bundle):
    original = calibrate(bundle)
    for q in bundle.questions:
        if q.split == "heldout":
            bundle.records.pop(q.id)
    assert calibrate(bundle) == original
    assert original["selected_threshold"] == 0.2


def test_censored_calibration_rejected(bundle):
    bundle.manifest.generation_threshold = 0.25
    with pytest.raises(ValueError, match="uncensored"):
        calibrate(bundle)


def test_synthetic_cannot_be_human_evidence(bundle):
    with pytest.raises(ValueError, match="not_resume_evidence"):
        require_official_evidence(bundle)


def test_artifact_tampering_rejected(bundle, tmp_path):
    with (tmp_path / "records.jsonl").open("a") as f:
        f.write("\n")
    with pytest.raises(ValueError, match="artifact_hash_mismatch"):
        load_bundle(
            *(
                tmp_path / name
                for name in ("questions.jsonl", "corpus.json", "records.jsonl", "manifest.json")
            )
        )


def test_exact_only_replays_same_records(bundle):
    assert score(bundle, "heldout", "on", exact_only=True)["correct"] == 2
