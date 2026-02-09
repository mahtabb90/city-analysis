from city_vibe.domain.traffic_models import TrafficData


def map_traffic_data(raw_data):
    """
    Convert raw traffic JSON into a TrafficData object.
    """
    return TrafficData(
        city=raw_data["city"],
        congestion=raw_data["congestion"],
        speed=raw_data["speed"],
        incidents=raw_data["incidents"],
    )
