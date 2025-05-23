from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class DataReporte(BaseModel):
    elemento: Optional[str] = None
    valor: Optional[float] = None
    