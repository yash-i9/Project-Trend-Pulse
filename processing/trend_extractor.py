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


def improve_title(topic: str, raw_text: str, sources: List[str]) -> str:
    """
    Improve vague titles by using raw_text if topic is too generic.
    Generic patterns: single word, weather alerts, etc.
    """
    topic = (topic or "").strip()
    
    # Check if topic is too vague
    is_vague = (
        len(topic) < 5 or 
        topic.lower() in ["weather alert", "alert", "update"] or
        (len(topic.split()) == 1 and len(topic) < 8)
    )
    
    if is_vague and raw_text:
        # Extract first 80 chars of raw_text as a better title
        raw_normalized = (raw_text or "").strip()
        sentences = raw_normalized.split('.')
        if sentences and sentences[0]:
            better_title = sentences[0].strip()
            if len(better_title) > 8 and len(better_title) <= 150:
                return better_title
    
    return topic


def extract_best_url(urls: List[str], sources: List[str]) -> str:
    """
    Extract the best URL from the list, preferring specific article URLs over homepages.
    """
    if not urls:
        return ""
    
    # Remove empty strings
    valid_urls = [u for u in urls if u and u.strip()]
    if not valid_urls:
        return ""
    
    # Prefer URLs that aren't just homepages
    # Filter out generic homepage URLs
    homepage_indicators = [
        "trends.google.com/trends/explore",
        "reddit.com/r/popular",
        "news.google.com/",
        "twitter.com/",
        "facebook.com/",
    ]
    
    specific_urls = [
        u for u in valid_urls
        if not any(indicator in u for indicator in homepage_indicators)
    ]
    
    # If we have specific URLs, use the first one; otherwise use the first available
    return specific_urls[0] if specific_urls else valid_urls[0]


def generate_description(topic: str, raw_texts: List[str], sources: List[str]) -> tuple[str, str]:
    """
    Generate a meaningful description based on sources.
    Returns (description, source_label) tuple.
    
    For Google Trends only: explains it's trending on Google
    For Reddit: includes subreddit context
    For News: uses article summary
    For mixed: combines information from multiple sources
    """
    unique_sources = set(sources)
    
    # Case 1: Only Google Trends
    if unique_sources == {"google_trends"}:
        return (
            f"Trending on Google Trends. This topic is gaining search interest. Click to see trending searches and related queries for '{topic}'.",
            "Google Trends Only"
        )
    
    # Case 2: Only Reddit
    elif unique_sources == {"reddit"}:
        # Extract subreddit info if available
        combined = " ".join(raw_texts)
        sentences = [s.strip() for s in combined.split('.') if s.strip()]
        desc = sentences[0] if sentences else combined
        if len(desc) > 250:
            desc = desc[:250] + "..."
        return (
            desc,
            "Reddit Discussion"
        )
    
    # Case 3: Only News
    elif unique_sources == {"news"}:
        combined = " ".join(raw_texts)
        sentences = [s.strip() for s in combined.split('.') if s.strip()]
        # Take first 1-2 sentences for better context
        desc = ". ".join(sentences[:2]) if len(sentences) > 1 else sentences[0] if sentences else combined
        if len(desc) > 280:
            desc = desc[:280] + "..."
        return (
            desc,
            "News"
        )
    
    # Case 4: Mixed sources - prefer content sources over trends
    else:
        # Prioritize News and Reddit content over Google Trends
        content_texts = []
        
        # Get non-empty texts for content
        for i, text in enumerate(raw_texts):
            if text and text.strip():
                if "reddit" in sources[i] or "news" in sources[i]:
                    content_texts.append(text.strip())
        
        # Build description from content sources
        if content_texts:
            combined = " ".join(content_texts)
            sentences = [s.strip() for s in combined.split('.') if s.strip()]
            desc = ". ".join(sentences[:2]) if len(sentences) > 1 else sentences[0]
            if len(desc) > 280:
                desc = desc[:280] + "..."
        else:
            desc = topic
        
        # Create readable source label with proper ordering
        source_list = []
        if "news" in unique_sources:
            source_list.append("News")
        if "reddit" in unique_sources:
            source_list.append("Reddit")
        if "google_trends" in unique_sources:
            source_list.append("Trending")
        
        source_label = " + ".join(source_list)
        
        return (desc, source_label)



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
        
        # Improve title if it's too vague
        original_topic = group["topic"]
        improved_topic = improve_title(original_topic, combined_text, group["sources"])
        
        # Get the best URL (prefer specific article URLs)
        best_url = extract_best_url(group["urls"], group["sources"])
        
        # Generate source-specific description
        description, source_label = generate_description(
            improved_topic,
            group["raw_texts"],
            group["sources"]
        )

        enriched.append(
            {
                "topic": improved_topic,
                "normalized_topic": key,
                "category": category,
                "sources": sorted(set(group["sources"])),
                "source_count": len(set(group["sources"])),
                "source_label": source_label,
                "keywords": keywords,
                "raw_text": combined_text,
                "popularity": float(np.mean(group["popularities"])) if group["popularities"] else 0.0,
                "published_at": latest_timestamp,
                "combined_url": best_url,
                "snippet": combined_text[:220],
                "description": description,
            }
        )

    return enriched