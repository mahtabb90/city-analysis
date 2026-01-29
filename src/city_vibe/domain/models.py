from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class City:
    id: Optional[int]
    name: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None

@dataclass
class WeatherRecord:
    id: Optional[int]
    city_id: int
    timestamp: datetime
    temperature: float
    humidity: float

@dataclass
class TrafficRecord:
    id: Optional[int]
    city_id: int
    timestamp: datetime
    congestion_level: float

@dataclass
class AnalysisResult:
    id: Optional[int]
    city_id: int
    timestamp: datetime
    category: str
    status: str
    metrics_json: str
