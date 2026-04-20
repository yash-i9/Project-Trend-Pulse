from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Dict, Any

import pandas as pd

try:
    from pytrends.request import TrendReq
except Exception:
    TrendReq = None  # fallback if pytrends is unavailable

from processing.trend_extractor import infer_category


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fallback_data() -> List[Dict[str, Any]]:
    sample_topics = [
        "AI tools",
        "Stock market rally",
        "Cricket highlights",
        "Weather alert",
        "Budget 2026",
        "New smartphone launch",
        "Election updates",
        "Gaming release",
    ]
    items = []
    for i, topic in enumerate(sample_topics):
        items.append(
            {
                "source": "google_trends",
                "topic": topic,
                "category": infer_category(topic),
                "popularity": 60 + (i * 4),
                "published_at": _now_iso(),
                "raw_text": topic,
                "url": f"https://trends.google.com/trends/explore?q={topic.replace(' ', '%20')}",
            }
        )
    return items


def fetch_google_trends(country_code: str = "india", limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch trending searches from Google Trends.
    Falls back to demo data if the network call fails.
    """
    if TrendReq is None:
        return _fallback_data()[:limit]

    try:
        pytrends = TrendReq(hl="en-US", tz=330)
        df: pd.DataFrame = pytrends.trending_searches(pn=country_code)

        if df is None or df.empty:
            return _fallback_data()[:limit]

        values = df.iloc[:, 0].astype(str).tolist()[:limit]
        results: List[Dict[str, Any]] = []

        for idx, topic in enumerate(values):
            results.append(
                {
                    "source": "google_trends",
                    "topic": topic,
                    "category": infer_category(topic),
                    "popularity": max(100 - idx * 3, 40),
                    "published_at": _now_iso(),
                    "raw_text": topic,
                    "url": f"https://trends.google.com/trends/explore?q={topic.replace(' ', '%20')}",
                }
            )

        return results

    except Exception:
        return _fallback_data()[:limit]


if __name__ == "__main__":
    data = fetch_google_trends()
    for item in data:
        print(item)