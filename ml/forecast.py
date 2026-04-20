from __future__ import annotations

from typing import List, Dict, Any

import numpy as np
from sklearn.linear_model import LinearRegression


def forecast_trend(history: List[Dict[str, Any]], periods: int = 3) -> Dict[str, Any]:
    """
    Forecast next popularity values from a history list.
    Each history item should have a 'popularity' field.
    """
    if not history:
        return {
            "method": "none",
            "history": [],
            "forecast": [],
            "message": "No trend history available.",
        }

    values = [float(item.get("popularity", 0) or 0) for item in history]
    values = [v for v in values if np.isfinite(v)]

    if len(values) == 0:
        return {
            "method": "none",
            "history": [],
            "forecast": [],
            "message": "No valid popularity values available.",
        }

    if len(values) < 2:
        avg = float(np.mean(values))
        return {
            "method": "moving_average",
            "history": values,
            "forecast": [round(avg, 2) for _ in range(periods)],
            "message": "Not enough data for regression, so moving average was used.",
        }

    x = np.arange(len(values)).reshape(-1, 1)
    y = np.array(values)

    model = LinearRegression()
    model.fit(x, y)

    future_x = np.arange(len(values), len(values) + periods).reshape(-1, 1)
    predicted = model.predict(future_x)

    direction = "upward" if predicted[-1] > values[-1] else "downward"

    return {
        "method": "linear_regression",
        "history": [round(v, 2) for v in values],
        "forecast": [round(float(v), 2) for v in predicted.tolist()],
        "direction": direction,
        "slope": round(float(model.coef_[0]), 4),
        "message": f"Forecast shows a {direction} trend based on the recent pattern.",
    }