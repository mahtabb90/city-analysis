from datetime import datetime, timedelta
from typing import List, Dict

from city_vibe.clients.traffic.mock_api import generate_mock_traffic_data


class TrafficClient:
    def __init__(self):
        pass

    def get_current_traffic(self, city: str) -> Dict:
        """
        Fetches current traffic data for a given city.
        """
        mock_data = generate_mock_traffic_data(date=datetime.now())
        mock_data["city"] = city
        mock_data["timestamp"] = datetime.now().isoformat()
        return mock_data

    def get_historical_traffic_range(
        self,
        city: str,
        start_date: datetime,
        end_date: datetime,
        points_per_day: int = 5,
    ) -> List[Dict]:
        """
        Generates historical mock traffic data for a given city and date range,
        with a specified number of data points per day.
        """
        historical_data = []
        current_date = start_date

        # Define approximate times for the 5 points during the day
        daily_times = [
            timedelta(hours=8),  # Morning rush
            timedelta(hours=11),  # Late morning
            timedelta(hours=14),  # Afternoon
            timedelta(hours=17),  # Evening rush
            timedelta(hours=20),  # Late evening
        ]

        while current_date <= end_date:
            for i in range(points_per_day):
                # Create a specific timestamp for this data point
                point_timestamp = (
                    current_date + daily_times[i % len(daily_times)]
                )  # Cycle through daily_times

                mock_data = generate_mock_traffic_data(date=point_timestamp)
                mock_data["city"] = city
                mock_data["timestamp"] = (
                    point_timestamp.isoformat()
                )  # Use full timestamp
                historical_data.append(mock_data)
            current_date += timedelta(days=1)
        return historical_data
