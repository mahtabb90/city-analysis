import requests

class TrafficClient:
    def __init__(self, base_url):
        self.base_url = base_url

    def fetch_traffic(self, city):
        response = requests.get(
            self.base_url,
            params={"city": city}
        )
        response.raise_for_status()
        return response.json()
