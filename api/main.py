from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from scrapers.google_trends import fetch_google_trends
from scrapers.reddit import fetch_reddit_trends
from scrapers.news import fetch_news_trends
from processing.trend_extractor import extract_trend_features
from processing.scorer import rank_trends
from ml.recommendation import recommend_trends
from ml.forecast import forecast_trend


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "trendpulse.db"


app = FastAPI(title="TrendPulse API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PreferenceInput(BaseModel):
    preferred_categories: List[str] = Field(default_factory=list)
    preferred_sources: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    tone: str = ""


class ForecastInput(BaseModel):
    topic: str
    periods: int = 3


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS trends (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                normalized_topic TEXT NOT NULL,
                category TEXT,
                sources TEXT,
                popularity REAL,
                final_score REAL,
                published_at TEXT,
                payload TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()


def save_trends(trends: List[Dict[str, Any]]) -> None:
    with get_connection() as conn:
        for trend in trends:
            conn.execute(
                """
                INSERT INTO trends (
                    topic, normalized_topic, category, sources,
                    popularity, final_score, published_at, payload
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trend.get("topic", ""),
                    trend.get("normalized_topic", ""),
                    trend.get("category", "general"),
                    json.dumps(trend.get("sources", [])),
                    float(trend.get("popularity", 0) or 0),
                    float(trend.get("final_score", 0) or 0),
                    trend.get("published_at", ""),
                    json.dumps(trend, ensure_ascii=False),
                ),
            )
        conn.commit()


def load_latest_trends(limit: int = 20) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM trends
            ORDER BY created_at DESC, id DESC
            """
        ).fetchall()

    seen = set()
    results: List[Dict[str, Any]] = []

    for row in rows:
        topic_key = (row["normalized_topic"] or row["topic"] or "").lower()
        if topic_key in seen:
            continue

        seen.add(topic_key)
        payload = json.loads(row["payload"])
        payload["db_id"] = row["id"]
        payload["db_final_score"] = row["final_score"]
        results.append(payload)

        if len(results) >= limit:
            break

    return results


def load_topic_history(topic: str) -> List[Dict[str, Any]]:
    topic_key = topic.strip().lower()

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM trends
            WHERE LOWER(normalized_topic) = ?
               OR LOWER(topic) LIKE ?
            ORDER BY created_at ASC, id ASC
            """,
            (topic_key, f"%{topic_key}%"),
        ).fetchall()

    history: List[Dict[str, Any]] = []
    for row in rows:
        payload = json.loads(row["payload"])
        history.append(payload)

    return history


def run_pipeline() -> List[Dict[str, Any]]:
    raw_items: List[Dict[str, Any]] = []
    raw_items.extend(fetch_google_trends(limit=50))
    raw_items.extend(fetch_reddit_trends(limit=50))
    raw_items.extend(fetch_news_trends(limit=50))

    extracted = extract_trend_features(raw_items)
    ranked = rank_trends(extracted)
    save_trends(ranked)
    return ranked


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "message": "TrendPulse API is running"}


@app.post("/refresh")
def refresh_data() -> Dict[str, Any]:
    try:
        ranked = run_pipeline()
        return {
            "message": "Trend data refreshed successfully.",
            "count": len(ranked),
            "top_trends": ranked[:10],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/trends")
def get_trends(limit: int = Query(20, ge=1, le=100)) -> Dict[str, Any]:
    trends = load_latest_trends(limit=limit)
    return {
        "count": len(trends),
        "trends": trends,
    }


@app.post("/recommend")
def recommend(payload: PreferenceInput, top_k: int = Query(5, ge=1, le=20)) -> Dict[str, Any]:
    trends = load_latest_trends(limit=300)

    if not trends:
        trends = run_pipeline()

    user_profile = payload.model_dump()
    recommendations = recommend_trends(trends, user_profile, top_k=top_k)

    return {
        "count": len(recommendations),
        "recommendations": recommendations,
    }


@app.get("/forecast")
def forecast(topic: str, periods: int = Query(3, ge=1, le=10)) -> Dict[str, Any]:
    history = load_topic_history(topic)

    if not history:
        raise HTTPException(status_code=404, detail="No history found for the given topic.")

    result = forecast_trend(history, periods=periods)
    return {
        "topic": topic,
        "result": result,
    }


@app.get("/summary")
def summary() -> Dict[str, Any]:
    trends = load_latest_trends(limit=150)
    categories = {}
    sources = {}
    for trend in trends:
        cat = trend.get("category", "general")
        categories[cat] = categories.get(cat, 0) + 1
        
        src_list = trend.get("sources", [])
        if not src_list:
            src = trend.get("source", "unknown")
            sources[src] = sources.get(src, 0) + 1
        else:
            for s in src_list:
                sources[s] = sources.get(s, 0) + 1

    return {
        "total_trends_available": len(trends),
        "category_distribution": categories,
        "source_distribution": sources,
        "note": "Trends are collected from Google Trends, Reddit, and news RSS feeds, then cleaned, scored, and ranked.",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=True)