import random
from datetime import datetime

DEFAULT_MOCK_TRAFFIC_DATA = {
    "congestion": 0.7,
    "speed": 30.0,
    "incidents": 2,
}


def generate_mock_traffic_data(
    base_data: dict = None, date: datetime = None
) -> dict:
    """
    Generates a single set of randomized mock traffic data based on base data.
    If a date is provided, introduces variations for weekends vs. weekdays.
    """
    if base_data is None:
        base_data = DEFAULT_MOCK_TRAFFIC_DATA

    congestion_base = base_data.get("congestion", 0.5)
    speed_base = base_data.get("speed", 40.0)
    incidents_base = base_data.get("incidents", 1)

    # Introduce date-based variation
    if date and (date.weekday() >= 5):
        congestion_base = max(0.1, congestion_base * 0.7)
        speed_base = min(60.0, speed_base * 1.2)
    else:  # Weekday
        congestion_base = min(0.9, congestion_base * 1.1)
        speed_base = max(20.0, speed_base * 0.9)

    # Apply some randomization around the base values
    congestion = round(
        max(0.0, min(1.0, congestion_base + random.uniform(-0.1, 0.1))), 2
    )
    speed = round(max(0.0, speed_base + random.uniform(-5, 5)), 0)
    incidents = max(0, incidents_base + random.randint(-1, 1))

    return {
        "congestion": congestion,
        "speed": speed,
        "incidents": incidents,
        "date": date.isoformat() if date else None,
    }
