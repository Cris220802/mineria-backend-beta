from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ResumenElemento(BaseModel):
    elemento: Optional[str] = None
    recuperacion: Optional[float] = None
    comparativa_recuperacion: Optional[float] = None
    contenido: Optional[float] = None
    comparativa_contenido: Optional[float] = None
    ley: Optional[float] = None
    comparativa_ley: Optional[float] = None
    
class ElementoValorRecuperacion(BaseModel):
    valor: Optional[float] = None
    date: Optional[datetime] = None
    
class RecuperacionElemento(BaseModel):
    elemento: Optional[str] = None
    valores: Optional[List[ElementoValorRecuperacion]] = None
    
class ElementoValorContenido(BaseModel):
    valor: Optional[float] = None
    date: Optional[datetime] = None
    
class ContenidoElemento(BaseModel):
    elemento: Optional[str] = None
    valores: Optional[List[ElementoValorContenido]] = None
    
class ElementoValorLey(BaseModel):
    valor: Optional[float] = None
    date: Optional[datetime] = None
    seccion: Optional[str] = None
    
class LeyElemento(BaseModel):
    elemento: Optional[float] = None
    valores: Optional[List[ElementoValorLey]] = None
    
class CalidadConcentrado(BaseModel):
    seccion: Optional[str] = None
    elementos: Optional[List[LeyElemento]] = None
    
class CalidadesConcentrados(BaseModel):
    secciones: Optional[List[CalidadConcentrado]] = None
    
    
class DashboardResponse(BaseModel):
    resumen: List[ResumenElemento]
    recuperaciones: List[RecuperacionElemento]