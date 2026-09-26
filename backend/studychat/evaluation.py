"""Deterministic page evaluation. Gold labels never influence generation or verification."""

import hashlib
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from studychat.citations import PageSource, parse_citations, verify_answer
from studychat.text import normalize


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GoldPage(StrictModel):
    document_id: UUID
    page: int = Field(gt=0)


class Question(StrictModel):
    id: str = Field(min_length=1)
    split: Literal["dev", "heldout"]
    question: str = Field(min_length=1, max_length=4000)
    document_ids: list[UUID] = Field(min_length=1, max_length=10)
    gold: list[GoldPage] = Field(min_length=1)
    label_source: Literal["synthetic", "human_blind"]
    annotation_note: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_gold(self):
        if len(set(self.document_ids)) != len(self.document_ids):
            raise ValueError("duplicate_selected_document")
        if any(g.document_id not in self.document_ids for g in self.gold):
            raise ValueError("gold_outside_selected_documents")
        if len({(g.document_id, g.page) for g in self.gold}) != len(self.gold):
            raise ValueError("duplicate_gold_page")
        return self


class CorpusDocument(StrictModel):
    document_id: UUID
    filename: str
    pdf_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    embedding_model: str
    pages: list[str] = Field(min_length=1)
    page_text_sha256: list[str]

    @model_validator(mode="after")
    def hashes_match(self):
        if self.page_text_sha256 != [hashlib.sha256(t.encode()).hexdigest() for t in self.pages]:
            raise ValueError("page_text_hash_mismatch")
        return self


class Corpus(StrictModel):
    kind: Literal["fixture", "synthetic", "human"]
    provenance: str = Field(min_length=1)
    documents: list[CorpusDocument] = Field(min_length=1)


class RetrievedPage(GoldPage):
    similarity: float = Field(ge=-1.000001, le=1.000001, allow_inf_nan=False)
    alias: str = Field(pattern=r"^D[1-9]\d*$")


class Record(StrictModel):
    question_id: str
    outcome: Literal["completed", "abstained", "error"]
    answer: str = Field(max_length=100000)
    aliases: dict[str, UUID]
    retrieval: list[RetrievedPage] = Field(max_length=6)
    error_code: str | None = None

    @model_validator(mode="after")
    def aliases_match(self):
        if any(self.aliases.get(row.alias) != row.document_id for row in self.retrieval):
            raise ValueError("retrieval_alias_mismatch")
        if set(self.aliases) != {row.alias for row in self.retrieval}:
            raise ValueError("aliases_outside_retrieval")
        return self


class Manifest(StrictModel):
    schema_version: Literal[1] = 1
    mode: Literal["fixture", "live"]
    origin: str
    dataset_sha256: str
    corpus_sha256: str
    records_sha256: str
    git_revision: str
    started_at: str
    chat_model: str
    embedding_model: str
    prompt_hash: str
    generation_threshold: float = Field(ge=-1, le=1, allow_inf_nan=False)
    threshold_label: str
    max_output_tokens: int = Field(gt=0)
    dependency_hashes: dict[str, str]
    normalization_version: str
    verifier_version: str
    split: Literal["dev", "heldout", "all"]
    calibration_sha256: str | None = None


@dataclass
class Bundle:
    questions: list[Question]
    corpus: Corpus
    records: dict[str, Record]
    manifest: Manifest


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_jsonl(path: Path, model):
    rows = []
    for line_number, line in enumerate(path.read_text().splitlines(), 1):
        if line.strip():
            try:
                rows.append(model.model_validate_json(line))
            except ValueError as exc:
                raise ValueError(f"invalid_{path.name}_line_{line_number}") from exc
    return rows


def load_bundle(dataset: Path, corpus_path: Path, records_path: Path, manifest_path: Path):
    manifest = Manifest.model_validate_json(manifest_path.read_text())
    for expected, path in [
        (manifest.dataset_sha256, dataset),
        (manifest.corpus_sha256, corpus_path),
        (manifest.records_sha256, records_path),
    ]:
        if expected != digest(path):
            raise ValueError(f"artifact_hash_mismatch:{path.name}")
    corpus = Corpus.model_validate_json(corpus_path.read_text())
    questions = load_jsonl(dataset, Question)
    records = load_jsonl(records_path, Record)
    validate_dataset(questions, corpus)
    if len({r.question_id for r in records}) != len(records):
        raise ValueError("duplicate_record")
    question_map = {q.id: q for q in questions}
    docs = {d.document_id: d for d in corpus.documents}
    for record in records:
        if record.question_id not in question_map:
            raise ValueError("unknown_record_question")
        question = question_map[record.question_id]
        for row in record.retrieval:
            if row.document_id not in question.document_ids:
                raise ValueError("retrieval_outside_selected_documents")
            if row.page > len(docs[row.document_id].pages):
                raise ValueError("retrieved_page_missing_from_corpus")
    return Bundle(questions, corpus, {r.question_id: r for r in records}, manifest)


def validate_dataset(questions: list[Question], corpus: Corpus):
    if not questions or len({q.id for q in questions}) != len(questions):
        raise ValueError("empty_dataset_or_duplicate_question_id")
    texts = [normalize(q.question).casefold() for q in questions]
    if len(set(texts)) != len(texts) or any(not text for text in texts):
        raise ValueError("duplicate_or_empty_question_text_across_splits")
    docs = {d.document_id: d for d in corpus.documents}
    if len(docs) != len(corpus.documents):
        raise ValueError("duplicate_corpus_document")
    for question in questions:
        if any(doc_id not in docs for doc_id in question.document_ids):
            raise ValueError("selected_document_missing_from_corpus")
        if any(g.page > len(docs[g.document_id].pages) for g in question.gold):
            raise ValueError("gold_page_missing_from_corpus")
        if corpus.kind == "human" and question.label_source != "human_blind":
            raise ValueError("human_corpus_requires_blind_labels")


def wilson(successes: int, total: int):
    if not total:
        return None
    z = 1.96
    p = successes / total
    center = (p + z * z / (2 * total)) / (1 + z * z / total)
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / (1 + z * z / total)
    return [max(0, center - half), min(1, center + half)]


def score(bundle: Bundle, split: str, quotes: str, *, exact_only=False, threshold=None):
    if quotes not in {"off", "on"} or split not in {"dev", "heldout"}:
        raise ValueError("invalid_scoring_mode")
    questions = [q for q in bundle.questions if q.split == split]
    if not questions:
        raise ValueError("empty_split")
    docs = {d.document_id: d for d in bundle.corpus.documents}
    outcomes, removed, match_counts = [], Counter(), Counter()
    for question in questions:
        record = bundle.records.get(question.id)
        gold = {(g.document_id, g.page) for g in question.gold}
        retrieval = record.retrieval if record else []
        retrieved = {(r.document_id, r.page) for r in retrieval}
        recall = bool(gold & retrieved)
        status = record.outcome if record else "error"
        reason = record.error_code if record else "missing_record"
        if threshold is not None and status != "error":
            if not retrieval or max(r.similarity for r in retrieval) < threshold:
                status, reason = "abstained", "threshold_gate"
        references, invalid_displayed = [], False
        if status == "completed" and record and record.answer.strip():
            try:
                if quotes == "off":
                    for citation in parse_citations(record.answer):
                        doc_id = record.aliases.get(citation.alias)
                        if citation.error or not doc_id or not citation.page or citation.page < 1:
                            invalid_displayed = True
                        else:
                            references.append((doc_id, citation.page))
                else:
                    sources = [
                        PageSource(doc_id, page, docs[doc_id].pages[page - 1])
                        for doc_id, page in sorted(retrieved, key=lambda p: (str(p[0]), p[1]))
                    ]
                    verified = verify_answer(
                        record.answer, record.aliases, sources, allow_fuzzy=not exact_only
                    )
                    for citation in verified.citations:
                        if citation.status == "removed":
                            removed[citation.reason] += 1
                        else:
                            references.append((citation.document_id, citation.citation.page))
                            match_counts[citation.status] += 1
            except ValueError:
                reason = "verification_limit"
                references, invalid_displayed = [], True
        answered = status == "completed" and bool(references)
        correct = answered and not invalid_displayed and all(ref in gold for ref in references)
        if status == "completed" and not answered:
            reason = reason or "no_surviving_citation"
        elif answered and not correct:
            reason = "wrong_gold_page"
        outcomes.append(
            {
                "question_id": question.id,
                "outcome": status,
                "answered": answered,
                "correct_pages": correct,
                "retrieval_gold_page_hit": recall,
                "reason": reason,
                "displayed_pages": [
                    {"document_id": str(doc), "page": page} for doc, page in references
                ],
            }
        )
    total = len(outcomes)
    answered = sum(o["answered"] for o in outcomes)
    correct = sum(o["correct_pages"] for o in outcomes)
    return {
        "evidence_kind": bundle.corpus.kind,
        "provider_mode": bundle.manifest.mode,
        "split": split,
        "quotes": quotes,
        "exact_only": exact_only,
        "total": total,
        "answered": answered,
        "correct": correct,
        "answer_rate": answered / total,
        "page_accuracy_among_answered": correct / answered if answered else None,
        "joint_success": correct / total,
        "answer_rate_95pct_interval": wilson(answered, total),
        "page_accuracy_95pct_interval": wilson(correct, answered),
        "abstentions": sum(o["outcome"] == "abstained" for o in outcomes),
        "errors": sum(o["outcome"] == "error" for o in outcomes),
        "retrieval_gold_page_recall_at_6": sum(o["retrieval_gold_page_hit"] for o in outcomes)
        / total,
        "removed_citations": dict(removed),
        "match_counts": dict(match_counts),
        "target_met": answered / total >= 0.95 and answered > 0 and correct / answered >= 0.90,
        "per_question": outcomes,
    }


def require_official_evidence(bundle: Bundle):
    if bundle.corpus.kind != "human" or bundle.manifest.mode != "live":
        raise ValueError("fixture_results_are_not_resume_evidence")
    counts = Counter(q.split for q in bundle.questions)
    if counts != {"dev": 20, "heldout": 120}:
        raise ValueError("official_dataset_requires_20_dev_and_120_heldout")
    if bundle.manifest.split != "heldout" or not bundle.manifest.calibration_sha256:
        raise ValueError("official_holdout_requires_frozen_dev_calibration")
    if any(q.label_source != "human_blind" for q in bundle.questions):
        raise ValueError("blind_human_labels_required")
    # This checks recorded provenance, not whether humans actually followed blinding.


def calibrate(bundle: Bundle):
    if bundle.manifest.generation_threshold != -1:
        raise ValueError("calibration_requires_uncensored_runs_at_threshold_minus_one")
    dev = [q for q in bundle.questions if q.split == "dev"]
    if not dev or any(q.id not in bundle.records for q in dev):
        raise ValueError("complete_dev_records_required")
    candidates = sorted(
        {
            -1.0,
            1.0,
            *[
                max(r.similarity for r in bundle.records[q.id].retrieval)
                for q in dev
                if bundle.records[q.id].retrieval
            ],
        }
    )
    trials = []
    for threshold in candidates:
        metrics = score(bundle, "dev", "on", threshold=threshold)
        trials.append(
            {
                "threshold": threshold,
                **{
                    k: metrics[k]
                    for k in (
                        "answer_rate",
                        "page_accuracy_among_answered",
                        "joint_success",
                        "target_met",
                    )
                },
            }
        )
    feasible = [trial for trial in trials if trial["target_met"]]
    chosen = (
        max(feasible, key=lambda t: t["threshold"])
        if feasible
        else max(trials, key=lambda t: (t["joint_success"], t["answer_rate"], t["threshold"]))
    )
    return {
        "selected_threshold": chosen["threshold"],
        "target_met_on_dev": chosen["target_met"],
        "mode": bundle.manifest.mode,
        "chat_model": bundle.manifest.chat_model,
        "prompt_hash": bundle.manifest.prompt_hash,
        "dataset_sha256": bundle.manifest.dataset_sha256,
        "corpus_sha256": bundle.manifest.corpus_sha256,
        "dev_question_ids": [q.id for q in dev],
        "trials": trials,
        "warning": "Development selection only; held-out performance is not established.",
    }
