from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import List, Dict, Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS


CATEGORY_KEYWORDS = {
    "technology": ["ai", "tech", "software", "startup", "app", "phone", "computer", "robot", "device", "internet"],
    "sports": ["cricket", "football", "match", "league", "win", "tournament", "score", "goal", "player", "sport"],
    "business": ["market", "stock", "share", "profit", "funding", "economy", "finance", "budget", "company", "startup"],
    "entertainment": ["movie", "music", "song", "film", "trailer", "celebrity", "show", "series", "viral", "game"],
    "politics": ["election", "government", "minister", "policy", "parliament", "vote", "politics", "party"],
    "health": ["health", "doctor", "disease", "vaccine", "hospital", "medical", "flu", "fitness"],
    "science": ["space", "research", "science", "lab", "discovery", "mission", "experiment"],
    "weather": ["weather", "rain", "storm", "temperature", "alert", "forecast", "cyclone", "heatwave"],
}


def normalize_text(text: str) -> str:
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_topic(text: str) -> str:
    return normalize_text(text)


def infer_category(text: str) -> str:
    text = normalize_text(text)
    scores = {}

    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        scores[category] = score

    best_category = max(scores, key=scores.get)
    return best_category if scores[best_category] > 0 else "general"


def extract_keywords(text: str, top_n: int = 5) -> List[str]:
    text = normalize_text(text)
    if not text:
        return []

    words = [w for w in text.split() if w not in ENGLISH_STOP_WORDS and len(w) > 2]
    if not words:
        return []

    counts = Counter(words)
    return [word for word, _ in counts.most_common(top_n)]


def _parse_timestamp(value: Any) -> str:
    if not value:
        return datetime.utcnow().isoformat()

    if isinstance(value, str):
        return value

    return datetime.utcnow().isoformat()


def extract_trend_features(raw_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Clean, deduplicate and enrich raw trend items.
    Output contains:
    - normalized topic
    - inferred category
    - keywords
    - source list
    - merged popularity
    """
    grouped: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "topic": "",
        "normalized_topic": "",
        "category_votes": [],
        "sources": [],
        "raw_texts": [],
        "urls": [],
        "popularities": [],
        "timestamps": [],
    })

    for item in raw_items:
        topic = item.get("topic", "")
        key = normalize_topic(topic)

        if not key:
            continue

        group = grouped[key]
        group["topic"] = group["topic"] or topic
        group["normalized_topic"] = key
        group["sources"].append(item.get("source", "unknown"))
        group["raw_texts"].append(item.get("raw_text") or topic)
        group["urls"].append(item.get("url") or "")
        group["popularities"].append(float(item.get("popularity", 0) or 0))
        group["timestamps"].append(_parse_timestamp(item.get("published_at")))
        group["category_votes"].append(item.get("category") or infer_category(topic))

    enriched: List[Dict[str, Any]] = []

    for key, group in grouped.items():
        combined_text = " ".join(group["raw_texts"])
        keywords = extract_keywords(combined_text, top_n=5)
        category = Counter(group["category_votes"]).most_common(1)[0][0] if group["category_votes"] else infer_category(combined_text)
        latest_timestamp = max(group["timestamps"]) if group["timestamps"] else datetime.utcnow().isoformat()

        enriched.append(
            {
                "topic": group["topic"],
                "normalized_topic": key,
                "category": category,
                "sources": sorted(set(group["sources"])),
                "source_count": len(set(group["sources"])),
                "keywords": keywords,
                "raw_text": combined_text,
                "popularity": float(np.mean(group["popularities"])) if group["popularities"] else 0.0,
                "published_at": latest_timestamp,
                "combined_url": next((u for u in group["urls"] if u), ""),
                "snippet": combined_text[:220],
            }
        )

    return enriched