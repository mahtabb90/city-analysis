from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class City:
    name: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    id: Optional[int] = None

@dataclass
class WeatherRecord:
    city_id: int
    timestamp: datetime
    temperature: float
    humidity: float
    id: Optional[int] = None

@dataclass
class TrafficRecord:
    city_id: int
    timestamp: datetime
    congestion_level: float
    id: Optional[int] = None

@dataclass
class AnalysisResult:
    city_id: int
    timestamp: datetime
    category: str
    status: str
    metrics_json: str
    id: Optional[int] = None