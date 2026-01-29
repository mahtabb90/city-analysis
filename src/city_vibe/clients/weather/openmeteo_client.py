import requests
from datetime import datetime

def get_weather(lat, lon):

    url = "https://api.open-meteo.com/v1/forecast"
    
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,apparent_temperature,rain,weather_code,cloud_cover,wind_speed_10m",
        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
        "timezone": "auto"           # gives local time
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()          # raises error if not 200 OK
        data = response.json()

        now = data["current"]
        
        result = {
            "time": datetime.fromisoformat(now["time"]),
            "temperature": now["temperature_2m"],
            "feels_like": now["apparent_temperature"],
            "rain": now["rain"],                 # mm in last hour
            "cloud_cover": now["cloud_cover"],   # 0–100 %
            "wind_speed": now["wind_speed_10m"], # km/h
            "weather_code": now["weather_code"]  # number → later we can make it say "Rain" or "Sunny"
        }
        
        return result
        
    except Exception as e:
        print("Error fetching weather:", e)
        return None


# A test when you run this file directly
if __name__ == "__main__":
    # Stockholm coordinates
    weather = get_weather(59.3293, 18.0686)
    
    if weather:
        print("Weather right now:")
        print(f"Time:          {weather['time']}")
        print(f"Temperature:   {weather['temperature']} °C")
        print(f"Feels like:    {weather['feels_like']} °C")
        print(f"Rain (last h): {weather['rain']} mm")
        print(f"Clouds:        {weather['cloud_cover']}%")
        print(f"Wind:          {weather['wind_speed']} km/h")
        print(f"Code:          {weather['weather_code']}")
    else:
        print("Could not get weather data")