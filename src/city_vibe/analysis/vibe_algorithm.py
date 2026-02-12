from enum import Enum
from datetime import datetime, date
from dataclasses import dataclass
import json
import random
import logging
from typing import Optional

from city_vibe.database import (
    fetch_weather_history,
    fetch_traffic_history,
    get_or_create_city,
    insert_record,
    fetch_forecast_data,
)
from city_vibe.domain.models import (
    AnalysisResult,
    ForecastRecord,
)
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
    FORECAST = "Forecast"


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


def _get_full_vibe_description(
    vibe_category: VibeCategory, target_date: Optional[date] = None
) -> str:
    """
    Retrieves the base description and appends random comments for the given vibe category.
    If target_date is provided, it prepends a "Predicted for..." message.
    It attempts to fetch up to 2 unique comments.
    """
    logger = logging.getLogger(__name__)
    try:
        if not COMMENTS_PATH.exists():
            return "No comments config found."

        with open(COMMENTS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        vibes_config = data.get("vibes", [])
        base_description = "A standard day in the city."  # Default if not found

        for entry in vibes_config:
            if entry.get("category") == vibe_category.value:
                base_description = entry.get("base_description", base_description)
                comments = entry.get("comments", [])

                selected_comments = []
                if comments:
                    # Try to get 2 unique comments, or fewer if not enough are available
                    num_comments_to_fetch = min(2, len(comments))
                    selected_comments = random.sample(comments, num_comments_to_fetch)

                full_description = base_description
                if target_date:
                    full_description = f"Predicted for {target_date.strftime('%Y-%m-%d')}: {full_description}"

                if selected_comments:
                    # Join selected comments, ensuring they are separated nicely
                    full_description = (
                        f"{full_description} " + ". ".join(selected_comments) + "."
                    )

                return full_description

        # If category not found, return default description with optional date prefix
        if target_date:
            return (
                f"Predicted for {target_date.strftime('%Y-%m-%d')}: {base_description}"
            )
        return base_description

    except Exception as e:
        logger.error(f"Error getting full vibe description: {e}")
        return "Error generating vibe description."


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

    # Logic
    if (
        w_status == CityStatus.UNSTABLE
        and t_inc_summary.avg > thresholds.high_incidents
    ):
        category = VibeCategory.STORM_WATCH
    elif is_friday and (now.hour >= 17) and bad_weather:
        category = VibeCategory.COZY_AT_HOME
    elif (
        payday_weekend or (is_friday and now.hour >= 17) or good_weather
    ) and good_weather:
        category = VibeCategory.PEOPLE_OUT_ON_TOWN
    elif (
        is_rush_hour
        and not is_weekend
        and t_cong_summary.avg > thresholds.heavy_congestion
    ):
        category = VibeCategory.RUSH_HOUR_STRESS
    elif is_night and t_cong_summary.avg < thresholds.light_congestion:
        category = VibeCategory.QUIET_CITY
    elif (
        good_weather and t_cong_summary.avg < thresholds.light_congestion and is_weekend
    ):
        category = VibeCategory.POSITIVE
    elif bad_weather and t_cong_summary.avg > thresholds.heavy_congestion:
        category = VibeCategory.NEGATIVE
    # Fallback to general
    elif w_status == CityStatus.IMPROVING:
        category = VibeCategory.POSITIVE

    description = _get_full_vibe_description(category)

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


def predict_vibe_for_date(city_name: str, target_date: date) -> AnalysisResult:
    """
    Predicts the overall 'vibe' for a city for a future date,
    synthesizing weather forecast, historical traffic patterns, and future date context.
    """
    city_id = get_or_create_city(city_name)
    thresholds = RuleThresholds()
    logger = logging.getLogger(__name__)  # Ensure logger is available

    # 1. Fetch Data
    # Weather Forecast for target_date
    forecast_record: ForecastRecord = fetch_forecast_data(city_id, target_date)

    if not forecast_record:
        logger.warning(
            f"No weather forecast available for {city_name} on {target_date}."
        )
        return AnalysisResult(
            city_id=city_id,
            timestamp=datetime.combine(target_date, datetime.min.time()),
            category=VibeCategory.FORECAST.value,
            status="Insufficient weather forecast data for prediction.",
            metrics_json="{}",
        )

    # Traffic: Use summary of recent historical traffic as proxy
    # Fetch last 7 days of traffic from today (current datetime)
    recent_traffic_history = fetch_traffic_history(city_name, days=7)

    if not recent_traffic_history:
        logger.warning(f"No recent traffic history available for {city_name}.")
        return AnalysisResult(
            city_id=city_id,
            timestamp=datetime.combine(target_date, datetime.min.time()),
            category=VibeCategory.FORECAST.value,
            status="Insufficient recent traffic data for prediction.",
            metrics_json="{}",
        )

    # 2. Compute Summaries for Forecasted Weather
    avg_temp = (forecast_record.temp_max + forecast_record.temp_min) / 2
    # Humidity not directly available in forecast, using a reasonable proxy
    humidity_proxy = (
        70.0  # Placeholder, could be improved with historical average if available
    )
    precip_sum = (
        forecast_record.precipitation_mm
        if forecast_record.precipitation_mm is not None
        else 0.0
    )

    # Simplified weather status based on forecast for a single day
    weather_status_forecast: CityStatus
    if precip_sum > thresholds.significant_precip and avg_temp < thresholds.cold_temp:
        weather_status_forecast = CityStatus.DECLINING
    elif avg_temp > thresholds.hot_temp:
        weather_status_forecast = CityStatus.UNSTABLE
    elif avg_temp < thresholds.cold_temp:
        weather_status_forecast = CityStatus.DECLINING
    else:
        weather_status_forecast = (
            CityStatus.STABLE
        )  # Default to stable if no extreme conditions

    # Compute Summaries for Traffic (from historical proxy)
    t_cong = [r.congestion_level for r in recent_traffic_history]
    t_inc = [r.incidents for r in recent_traffic_history]

    t_cong_summary = summarize_series(t_cong)
    t_inc_summary = summarize_series(t_inc)

    traffic_status_proxy = classify_status(
        t_cong_summary, thresholds
    )  # Classify based on historical summary

    # 3. Vibe Synthesis for Future Date
    # Use target_date for contextual factors
    is_weekend = target_date.weekday() in [5, 6]
    is_friday = target_date.weekday() == 4
    # For daily prediction, we won't use hour-specific rush_hour or night.
    # We'll assume a 'day-time' general vibe for the full day prediction.

    payday_weekend = is_payday_weekend(
        datetime.combine(target_date, datetime.min.time())
    )  # Convert date to datetime for this check

    good_weather_forecast = is_good_outdoor_weather(
        avg_temp, humidity_proxy, weather_status_forecast, thresholds
    )
    bad_weather_forecast = is_bad_weather(
        avg_temp, humidity_proxy, weather_status_forecast, precip_sum, thresholds
    )

    category = VibeCategory.NEUTRAL

    # Logic Trees adapted for forecast
    if (
        weather_status_forecast == CityStatus.DECLINING
        and traffic_status_proxy
        == CityStatus.UNSTABLE
    ):
        category = VibeCategory.STORM_WATCH
    elif is_friday and bad_weather_forecast:  # No time check as it's a daily prediction
        category = VibeCategory.COZY_AT_HOME
    elif (
        payday_weekend or is_friday or good_weather_forecast
    ) and good_weather_forecast:
        category = VibeCategory.PEOPLE_OUT_ON_TOWN
    elif traffic_status_proxy == CityStatus.DECLINING and not is_weekend:
        category = VibeCategory.RUSH_HOUR_STRESS  # General stress due to traffic
    elif (
        traffic_status_proxy == CityStatus.STABLE and is_weekend
    ):  # Light congestion if stable traffic
        category = VibeCategory.QUIET_CITY
    elif (
        good_weather_forecast
        and traffic_status_proxy == CityStatus.STABLE
        and is_weekend
    ):
        category = VibeCategory.POSITIVE
    elif bad_weather_forecast and traffic_status_proxy == CityStatus.DECLINING:
        category = VibeCategory.NEGATIVE
    elif weather_status_forecast == CityStatus.IMPROVING:
        category = VibeCategory.POSITIVE

    description = _get_full_vibe_description(category, target_date)

    # 4. Finalize Result
    metrics = VibeMetrics(
        weather_summary={
            "temp_avg": avg_temp,
            "temp_max": forecast_record.temp_max,
            "temp_min": forecast_record.temp_min,
            "humidity_proxy": humidity_proxy,
            "precip_sum": precip_sum,
        },
        traffic_summary={
            "cong": t_cong_summary.__dict__,
            "inc": t_inc_summary.__dict__,
        },
        weather_status=weather_status_forecast,
        traffic_status=traffic_status_proxy,
    )

    result = AnalysisResult(
        city_id=city_id,
        timestamp=datetime.combine(
            target_date, datetime.min.time()
        ),
        category=f"{VibeCategory.FORECAST.value}_{category.value}",
        status=description,
        metrics_json=json.dumps(metrics.__dict__, default=str),
    )

    insert_record("analysis_results", result)
    return result
