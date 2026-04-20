from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Dict, Any

import requests

from processing.trend_extractor import infer_category


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fallback_data() -> List[Dict[str, Any]]:
    sample = [
        "New AI model creates realistic images",
        "Cricket fans celebrate big win",
        "Tech startup raises funding",
        "Space mission reaches new milestone",
        "Electric vehicles gain popularity",
    ]
    results = []
    for i, topic in enumerate(sample):
        results.append(
            {
                "source": "reddit",
                "topic": topic,
                "category": infer_category(topic),
                "popularity": 55 + i * 5,
                "published_at": _now_iso(),
                "raw_text": topic,
                "url": "https://www.reddit.com/",
            }
        )
    return results


def fetch_reddit_trends(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch trending/hot Reddit posts from public JSON endpoint.
    """
    url = f"https://www.reddit.com/r/popular/hot.json?limit={limit}"
    headers = {
        "User-Agent": "TrendPulse/1.0 (educational project)"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        payload = response.json()

        items = payload.get("data", {}).get("children", [])
        results: List[Dict[str, Any]] = []

        for idx, post in enumerate(items):
            data = post.get("data", {})
            title = (data.get("title") or "").strip()
            subreddit = (data.get("subreddit") or "").strip()

            if not title:
                continue

            combined_text = f"{title} {subreddit}".strip()
            results.append(
                {
                    "source": "reddit",
                    "topic": title,
                    "category": infer_category(combined_text),
                    "popularity": max(95 - idx * 4, 35),
                    "published_at": _now_iso(),
                    "raw_text": combined_text,
                    "url": f"https://www.reddit.com{data.get('permalink', '')}",
                }
            )

        return results if results else _fallback_data()[:limit]

    except Exception:
        return _fallback_data()[:limit]


if __name__ == "__main__":
    data = fetch_reddit_trends()
    for item in data:
        print(item)