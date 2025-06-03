from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import date

class HistoricalDataPoint(BaseModel):
    date: date
    value: float

class PredictionResponse(BaseModel):
    predictions: Dict[str, float]
    historical_pb_recovery: Optional[List[HistoricalDataPoint]] = None
    trend: Optional[str] = None

    class Config:
        # from_attributes = True # Para Pydantic V2, si es necesario
        pass