from enum import Enum
from datetime import datetime
from dataclasses import dataclass
import json
import random

from city_vibe.database import (
    fetch_weather_history,
    fetch_traffic_history,
    get_or_create_city,
    insert_record,
)
from city_vibe.domain.models import AnalysisResult
from city_vibe.analysis.metrics import summarize_series, MetricSummary
from city_vibe.config import COMMENTS_PATH


class CityStatus(str, Enum):
    """High-level classification of the city conditions."""

    STABLE = "stable"
    IMPROVING = "improving"
    DECLINING = "declining"
    UNSTABLE = "unstable"


class VibeCategory(str, Enum):
    """Overall classification of the city's vibe."""

    POSITIVE = "Positive"
    NEUTRAL = "Neutral"
    NEGATIVE = "Negative"
    MIXED = "Mixed"
    PAYDAY_WEEKEND = "PaydayWeekend"
    PEOPLE_OUT_ON_TOWN = "PeopleOutOnTown"
    COZY_AT_HOME = "CozyAtHome"
    RUSH_HOUR_STRESS = "RushHourStress"
    QUIET_CITY = "QuietCity"
    VIBRANT_EVENING = "VibrantEvening"
    STORM_WATCH = "StormWatch"


@dataclass(frozen=True)
class RuleThresholds:
    """Threshold values used for classification."""

    variability_unstable: float = 2.0
    trend_improving: float = 1.0
    trend_declining: float = -1.0

    # Weather thresholds
    cold_temp: float = 5.0
    hot_temp: float = 25.0
    high_humidity: float = 90.0
    significant_precip: float = 1.0  # mm per day

    # Traffic thresholds
    heavy_congestion: float = 0.7
    light_congestion: float = 0.3
    high_incidents: int = 2


# --- Helper Logic Functions ---


def classify_status(
    metrics: MetricSummary, thresholds: RuleThresholds = RuleThresholds()
) -> CityStatus:
    """Classify status (improving/declining/unstable) based on metrics."""
    if metrics.variability > thresholds.variability_unstable:
        return CityStatus.UNSTABLE
    if metrics.trend >= thresholds.trend_improving:
        return CityStatus.IMPROVING
    if metrics.trend <= thresholds.trend_declining:
        return CityStatus.DECLINING
    return CityStatus.STABLE


def is_payday_weekend(date: datetime) -> bool:
    """Checks if it's a payday weekend (25th is Fri-Sun)."""
    if date.day != 25:
        return False
    return date.weekday() in [4, 5, 6]


def is_bad_weather(
    temp_avg: float,
    humidity_avg: float,
    status: CityStatus,
    precip_sum: float,
    thresholds: RuleThresholds = RuleThresholds(),
) -> bool:
    """Determines if weather is 'bad'."""
    return (
        temp_avg < thresholds.cold_temp
        or humidity_avg > thresholds.high_humidity
        or status in [CityStatus.DECLINING, CityStatus.UNSTABLE]
        or precip_sum > thresholds.significant_precip
    )


def is_good_outdoor_weather(
    temp_avg: float,
    humidity_avg: float,
    status: CityStatus,
    thresholds: RuleThresholds = RuleThresholds(),
) -> bool:
    """Determines if weather is 'good' for being outside."""
    return (
        thresholds.cold_temp <= temp_avg <= thresholds.hot_temp
        and humidity_avg < thresholds.high_humidity
        and status in [CityStatus.STABLE, CityStatus.IMPROVING]
    )


def get_vibe_comment(category: VibeCategory) -> str:
    """Selects a random comment for the given category from comments.json."""
    try:
        if not COMMENTS_PATH.exists():
            return ""

        with open(COMMENTS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        vibes = data.get("vibes", [])
        for entry in vibes:
            if entry.get("category") == category.value:
                return random.choice(entry.get("comments", [""]))
    except Exception:
        pass
    return ""


@dataclass
class VibeMetrics:
    """Detailed metrics that contribute to the overall Vibe."""

    weather_summary: dict
    traffic_summary: dict
    weather_status: CityStatus
    traffic_status: CityStatus


# --- Main Vibe Logic ---


def calculate_vibe(city_name: str, days: int = 7) -> AnalysisResult:
    """
    Calculates the overall 'vibe' for a city by synthesizing weather, traffic, and time.
    """
    city_id = get_or_create_city(city_name)
    thresholds = RuleThresholds()

    # 1. Fetch Data
    weather_history = fetch_weather_history(city_name, days)
    traffic_history = fetch_traffic_history(city_name, days)

    if not weather_history or not traffic_history:
        return AnalysisResult(
            city_id=city_id,
            timestamp=datetime.now(),
            category=VibeCategory.NEUTRAL.value,
            status="Insufficient data for analysis",
            metrics_json="{}",
        )

    # 2. Compute Summaries
    w_temps = [r.temperature for r in weather_history]
    w_hum = [r.humidity for r in weather_history]
    w_precip = sum(
        [r.precipitation for r in weather_history if r.precipitation is not None]
    )

    t_cong = [r.congestion_level for r in traffic_history]
    t_inc = [r.incidents for r in traffic_history]

    w_summary = summarize_series(w_temps)
    h_summary = summarize_series(w_hum)
    t_cong_summary = summarize_series(t_cong)
    t_inc_summary = summarize_series(t_inc)

    w_status = classify_status(w_summary, thresholds)
    t_status = classify_status(t_cong_summary, thresholds)

    # 3. Vibe Synthesis
    now = datetime.now()
    is_weekend = now.weekday() in [5, 6]
    is_friday = now.weekday() == 4
    is_rush_hour = (7 <= now.hour <= 9) or (16 <= now.hour <= 18)
    is_night = now.hour >= 22 or now.hour <= 5

    payday_weekend = is_payday_weekend(now)
    good_weather = is_good_outdoor_weather(
        w_summary.avg, h_summary.avg, w_status, thresholds
    )
    bad_weather = is_bad_weather(
        w_summary.avg, h_summary.avg, w_status, w_precip, thresholds
    )

    category = VibeCategory.NEUTRAL
    description = "A standard day in the city."

    # Logic Trees
    if (
        w_status == CityStatus.UNSTABLE
        and t_inc_summary.avg > thresholds.high_incidents
    ):
        category = VibeCategory.STORM_WATCH
        description = (
            "Unpredictable weather and traffic chaos. The city is on edge."
        )

    elif is_friday and (now.hour >= 17) and bad_weather:
        category = VibeCategory.COZY_AT_HOME
        description = (
            "Dreadful weather outside, but it's Friday! "
            "The city is retreating for a cozy night in."
        )

    elif (
        payday_weekend or (is_friday and now.hour >= 17) or good_weather
    ) and good_weather:
        category = VibeCategory.PEOPLE_OUT_ON_TOWN
        description = (
            "High spirits, full wallets, and perfect weather. "
            "The streets are alive!"
        )

    elif (
        is_rush_hour
        and not is_weekend
        and t_cong_summary.avg > thresholds.heavy_congestion
    ):
        category = VibeCategory.RUSH_HOUR_STRESS
        description = (
            "The morning grind is in full swing. "
            "High congestion and hurried people."
        )

    elif is_night and t_cong_summary.avg < thresholds.light_congestion:
        category = VibeCategory.QUIET_CITY
        description = (
            "The city is resting. Quiet streets and a peaceful atmosphere."
        )

    elif (
        good_weather
        and t_cong_summary.avg < thresholds.light_congestion
        and is_weekend
    ):
        category = VibeCategory.POSITIVE
        description = "A beautiful, lazy weekend day. Perfect for a stroll."

    elif bad_weather and t_cong_summary.avg > thresholds.heavy_congestion:
        category = VibeCategory.NEGATIVE
        description = (
            "Bad weather and heavy traffic. A frustrating day for commuters."
        )

    # Fallback to general
    elif w_status == CityStatus.IMPROVING:
        category = VibeCategory.POSITIVE
        description = "The mood is lifting as conditions improve."

    vibe_comment = get_vibe_comment(category)
    if vibe_comment:
        description = f"{description} {vibe_comment}"

    # 4. Finalize Result
    metrics = VibeMetrics(
        weather_summary={
            "temp": w_summary.__dict__,
            "hum": h_summary.__dict__,
            "precip": w_precip,
        },
        traffic_summary={
            "cong": t_cong_summary.__dict__,
            "inc": t_inc_summary.__dict__,
        },
        weather_status=w_status,
        traffic_status=t_status,
    )

    result = AnalysisResult(
        city_id=city_id,
        timestamp=now,
        category=category.value,
        status=description,
        metrics_json=json.dumps(metrics.__dict__, default=str),
    )

    insert_record("analysis_results", result)
    return result
