from pydantic import BaseModel


class TrafficData(BaseModel):
    city: str
    congestion: float
    speed: int
    incidents: int
