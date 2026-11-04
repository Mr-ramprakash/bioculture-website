"""Read approved knowledge from JSON files bundled with the Vercel backend."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .connectors.base import KnowledgeRecord

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.I)
_KNOWLEDGE_FILES = {
    "BIOMAN": Path(__file__).resolve().parents[2] / "knowledge-base" / "bioman" / "knowledge.json",
    "ROCOTILE": Path(__file__).resolve().parents[2] / "knowledge-base" / "rocotile" / "knowledge.json",
}


class KnowledgeFileError(RuntimeError):
    pass


def search_approved_knowledge(
    company_code: str,
    query: str,
    *,
    public_only: bool = False,
    limit: int = 5,
    knowledge_files: dict[str, Path] | None = None,
) -> list[KnowledgeRecord]:
    """Search one fixed company file; callers cannot supply a filename or path.

    ``knowledge_files`` is an optional server-owned mapping for standalone
    deployments. Request data must never be used to construct this mapping.
    """
    company = company_code.upper()
    file_map = _KNOWLEDGE_FILES if knowledge_files is None else knowledge_files
    path = file_map.get(company)
    if path is None:
        return []
    try:
        document: Any = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise KnowledgeFileError("Company knowledge is unavailable") from exc
    if not isinstance(document, dict) or document.get("company_code") != company or not isinstance(document.get("records"), list):
        raise KnowledgeFileError("Company knowledge is invalid")

    query_tokens = set(_TOKEN_RE.findall(query.lower()))
    ranked: list[tuple[int, str, dict[str, Any]]] = []
    for row in document["records"]:
        if not isinstance(row, dict) or row.get("approved") is not True or row.get("status") != "approved":
            continue
        if public_only and row.get("public") is not True:
            continue
        if not all(isinstance(row.get(field), str) and row[field] for field in ("record_id", "topic", "answer")):
            continue
        questions = row.get("questions", [])
        if not isinstance(questions, list) or not all(isinstance(question, str) for question in questions):
            continue
        candidates = [row.get("question", ""), *questions]
        best_question = ""
        score = len(query_tokens & set(_TOKEN_RE.findall(row["topic"].lower())))
        for candidate in candidates:
            candidate_score = len(query_tokens & set(_TOKEN_RE.findall(candidate.lower())))
            if candidate_score > score:
                score, best_question = candidate_score, candidate
        if score:
            ranked.append((score, best_question, row))

    ranked.sort(key=lambda item: item[0], reverse=True)
    return [
        KnowledgeRecord(
            record_id=row["record_id"],
            topic=row["topic"],
            question=question or row.get("question") or ("; ".join(row.get("questions", [])[:3])),
            answer=row["answer"],
            language=row.get("language") if isinstance(row.get("language"), str) else "en",
        )
        for _, question, row in ranked[: max(1, min(limit, 5))]
    ]
