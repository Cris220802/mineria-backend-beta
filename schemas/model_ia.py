from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import date

class HistoricalDataPoint(BaseModel):
    date: date
    value: float

class PredictionResponse(BaseModel):
    element: str
    prediction_type: str # <-- NUEVO CAMPO
    predictions: Dict[str, float]
    historical_data: List[HistoricalDataPoint]
    trend: str
    isError: bool = False
    detail: Optional[str] = None