from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class City(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[int] = None
    name: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class WeatherRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[int] = None
    city_id: int
    timestamp: datetime = datetime.now()
    temperature: float
    humidity: float

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