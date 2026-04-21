from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Dict, Any

import feedparser

from processing.trend_extractor import infer_category


NEWS_FEEDS = [
    "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en",
    "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fallback_data() -> List[Dict[str, Any]]:
    sample = [
        "Government announces new policy",
        "Global markets show mixed signals",
        "New movie trailer goes viral",
        "Health experts discuss seasonal flu",
        "Sports league prepares for finals",
    ]
    results = []
    for i, topic in enumerate(sample):
        results.append(
            {
                "source": "news",
                "topic": topic,
                "category": infer_category(topic),
                "popularity": 50 + i * 6,
                "published_at": _now_iso(),
                "raw_text": topic,
                "url": f"https://news.google.com/search?q={topic.replace(' ', '%20')}",
            }
        )
    return results


def fetch_news_trends(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch trending headlines from RSS feeds.
    """
    results: List[Dict[str, Any]] = []

    try:
        for feed_url in NEWS_FEEDS:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                title = (entry.get("title") or "").strip()
                summary = (entry.get("summary") or "").strip()

                if not title:
                    continue

                combined_text = f"{title} {summary}".strip()
                results.append(
                    {
                        "source": "news",
                        "topic": title,
                        "category": infer_category(combined_text),
                        "popularity": 70,
                        "published_at": _now_iso(),
                        "raw_text": combined_text,
                        "url": entry.get("link", feed_url),
                    }
                )

                if len(results) >= limit:
                    return results

        return results if results else _fallback_data()[:limit]

    except Exception:
        return _fallback_data()[:limit]


if __name__ == "__main__":
    data = fetch_news_trends()
    for item in data:
        print(item)