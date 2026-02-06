from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class City(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[int] = None
    name: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_confirmed: bool = False
    last_updated: Optional[datetime] = None


class WeatherRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[int] = None
    city_id: int
    timestamp: datetime = datetime.now()
    temperature: float
    humidity: Optional[float]
    wind_speed: Optional[float] = None
    precipitation: Optional[float] = None
    weather_code: Optional[int] = None


class TrafficRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[int] = None
    city_id: int
    timestamp: datetime = datetime.now()
    congestion_level: float
    speed: Optional[float] = None
    incidents: Optional[int] = None


class AnalysisResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[int] = None
    city_id: int
    timestamp: datetime = datetime.now()
    category: str
    status: str
    metrics_json: str


class ForecastRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[int] = None
    city_id: int
    date: datetime
    description: str
    temp_max: float
    temp_min: float
    feels_like_max: float
    feels_like_min: float
    precipitation_mm: float
    precipitation_chance: float
    wind_speed_max: float
    forecast_retrieval_time: datetime
