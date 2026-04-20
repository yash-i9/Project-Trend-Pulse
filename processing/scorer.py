from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Dict, Any

import numpy as np


POSITIVE_WORDS = {
    "growth", "gain", "rise", "surge", "booming", "strong", "record", "win", "improve",
    "launch", "breakthrough", "popular", "positive", "success", "trend"
}

NEGATIVE_WORDS = {
    "fall", "drop", "loss", "weak", "crash", "decline", "slump", "risk",
    "problem", "issue", "down", "negative", "fear", "delay", "ban"
}

SOURCE_WEIGHTS = {
    "google_trends": 1.00,
    "news": 0.92,
    "reddit": 0.88,
}


def _safe_parse_dt(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        value = value.replace("Z", "+00:00")
        return datetime.fromisoformat(value)
    except Exception:
        return datetime.now(timezone.utc)


def sentiment_score(text: str) -> float:
    text = (text or "").lower()
    words = text.split()
    if not words:
        return 0.0

    pos = sum(1 for w in words if w in POSITIVE_WORDS)
    neg = sum(1 for w in words if w in NEGATIVE_WORDS)
    raw = (pos - neg) / max(len(words), 1)
    return float(np.clip(raw * 5, -1.0, 1.0))


def recency_score(published_at: str | None) -> float:
    dt = _safe_parse_dt(published_at)
    now = datetime.now(timezone.utc)

    age_hours = (now - dt).total_seconds() / 3600.0
    if age_hours <= 1:
        return 1.0
    if age_hours >= 72:
        return 0.0

    return float(np.clip(1.0 - (age_hours / 72.0), 0.0, 1.0))


def source_score(sources: List[str]) -> float:
    if not sources:
        return 0.6
    weights = [SOURCE_WEIGHTS.get(src, 0.75) for src in sources]
    return float(np.mean(weights))


def popularity_score(popularity: float) -> float:
    return float(np.clip(popularity / 100.0, 0.0, 1.0))


def keyword_score(keywords: List[str]) -> float:
    if not keywords:
        return 0.0
    return float(np.clip(len(keywords) / 5.0, 0.0, 1.0))


def compute_trend_score(item: Dict[str, Any]) -> Dict[str, Any]:
    pop = popularity_score(float(item.get("popularity", 0) or 0))
    rec = recency_score(item.get("published_at"))
    src = source_score(item.get("sources", []))
    key = keyword_score(item.get("keywords", []))
    senti = sentiment_score(item.get("raw_text", ""))

    final_score = (
        0.38 * pop +
        0.22 * rec +
        0.18 * src +
        0.12 * key +
        0.10 * (0.5 + senti / 2.0)
    )

    enriched = dict(item)
    enriched["score_breakdown"] = {
        "popularity": round(pop, 4),
        "recency": round(rec, 4),
        "source": round(src, 4),
        "keywords": round(key, 4),
        "sentiment": round(senti, 4),
    }
    enriched["final_score"] = round(float(np.clip(final_score, 0.0, 1.0)), 4)
    return enriched


def rank_trends(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    scored = [compute_trend_score(item) for item in items]
    scored.sort(key=lambda x: x.get("final_score", 0), reverse=True)
    return scored