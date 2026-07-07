from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

RESOURCE_PATH = Path(__file__).resolve().parent.parent / "data" / "resources.json"

@dataclass
class KnowledgeHit:
    title: str
    category: str
    content: str
    score: int
    source: str = "approved_local_knowledge_base"


@lru_cache(maxsize=1)
def load_resources() -> list[dict]:
    if not RESOURCE_PATH.exists():
        return []
    return json.loads(RESOURCE_PATH.read_text(encoding="utf-8"))


def _tokens(text: str) -> set[str]:
    base = re.findall(r"[a-zA-Z]{3,}|[\u0900-\u097F]+", (text or "").lower())
    # small synonym expansion improves search without external vector DB.
    synonyms = {
        "ghabrahat": "anxiety",
        "tension": "stress",
        "neend": "sleep",
        "padhai": "study",
        "exam": "study",
        "deadline": "study",
        "breakup": "relationship",
        "akela": "loneliness",
        "akeli": "loneliness",
    }
    expanded = set(base)
    for token in list(base):
        if token in synonyms:
            expanded.add(synonyms[token])
    return expanded


def search_resources(query: str, limit: int = 4, category: str | None = None) -> list[KnowledgeHit]:
    resources = load_resources()
    terms = _tokens(query)
    scored: list[KnowledgeHit] = []
    for item in resources:
        haystack = " ".join(str(item.get(k, "")) for k in ["title", "category", "keywords", "content"]).lower()
        score = sum(3 if term == str(item.get("category", "")).lower() else 1 for term in terms if term in haystack)
        if category and item.get("category") == category:
            score += 3
        if score:
            scored.append(KnowledgeHit(
                title=str(item.get("title", "Untitled")),
                category=str(item.get("category", "general")),
                content=str(item.get("content", "")),
                score=score,
            ))
    scored.sort(key=lambda hit: hit.score, reverse=True)
    return scored[:limit]


def context_block(query: str, category: str | None = None) -> str:
    matches = search_resources(query, category=category)
    if not matches:
        return ""
    lines = []
    for hit in matches:
        lines.append(f"- {hit.title} ({hit.category}): {hit.content}")
    return "Approved coping knowledge. Use this as safe context, do not overclaim:\n" + "\n".join(lines)


def knowledge_metadata(query: str, category: str | None = None) -> list[dict]:
    return [hit.__dict__ for hit in search_resources(query, category=category)]
