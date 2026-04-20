from __future__ import annotations

from typing import List, Dict, Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def build_profile_text(profile: Dict[str, Any]) -> str:
    parts: List[str] = []

    for key in ["preferred_categories", "preferred_sources", "keywords", "tone"]:
        value = profile.get(key)

        if isinstance(value, list):
            parts.extend([str(v) for v in value if v])
        elif value:
            parts.append(str(value))

    return " ".join(parts).strip()


def build_trend_text(trend: Dict[str, Any]) -> str:
    parts = [
        str(trend.get("topic", "")),
        str(trend.get("category", "")),
        " ".join(trend.get("keywords", [])),
        str(trend.get("raw_text", "")),
        " ".join(trend.get("sources", [])),
    ]
    return " ".join(parts).strip()


def _match_reason(trend: Dict[str, Any], profile: Dict[str, Any]) -> str:
    reasons = []

    preferred_categories = {c.lower() for c in profile.get("preferred_categories", [])}
    preferred_sources = {s.lower() for s in profile.get("preferred_sources", [])}
    keywords = {k.lower() for k in profile.get("keywords", [])}

    trend_category = str(trend.get("category", "")).lower()
    trend_sources = {s.lower() for s in trend.get("sources", [])}
    trend_keywords = {k.lower() for k in trend.get("keywords", [])}

    if trend_category and trend_category in preferred_categories:
        reasons.append(f"category match: {trend_category}")

    if preferred_sources and trend_sources.intersection(preferred_sources):
        reasons.append("source match")

    if keywords and trend_keywords.intersection(keywords):
        reasons.append("keyword overlap")

    if not reasons:
        reasons.append("high overall trend score")

    return ", ".join(reasons)


def recommend_trends(
    trends: List[Dict[str, Any]],
    user_profile: Dict[str, Any],
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """
    Rank trends by similarity to the user profile plus the trend score.
    """
    if not trends:
        return []

    profile_text = build_profile_text(user_profile)
    if not profile_text:
        profile_text = "general trends"

    corpus = [build_trend_text(t) for t in trends] + [profile_text]
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf = vectorizer.fit_transform(corpus)

    trend_vectors = tfidf[:-1]
    profile_vector = tfidf[-1]

    similarities = cosine_similarity(profile_vector, trend_vectors).flatten()

    ranked: List[Dict[str, Any]] = []

    for trend, sim in zip(trends, similarities):
        base_score = float(trend.get("final_score", 0.0))
        combined_score = (0.20 * base_score) + (0.80 * float(sim))

        item = dict(trend)
        item["recommendation_score"] = round(combined_score, 4)
        item["profile_similarity"] = round(float(sim), 4)
        item["reason"] = _match_reason(trend, user_profile)
        ranked.append(item)

    ranked.sort(key=lambda x: x.get("recommendation_score", 0), reverse=True)
    return ranked[:top_k]