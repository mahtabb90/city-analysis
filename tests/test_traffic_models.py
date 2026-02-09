from city_vibe.domain.traffic_models import TrafficData


def test_traffic_data_creation():
    traffic = TrafficData(city="Stockholm", congestion=0.5, speed=40, incidents=1)
    assert traffic.city == "Stockholm"
    assert traffic.congestion == 0.5
