from pydantic import BaseModel
from datetime import datetime, date
from enum import Enum
from typing import List, Optional
from schemas.usuario_schema import UsuarioBase
   
# Enum para las etapas (usando Pydantic)
class Etapa(str, Enum):
    CONCKNELSON = "Concentrado Knelson"
    CABEZA = "Cabeza Flotacion"
    CONCPB = "Concentrado Pb"
    COLASPB = "Colas Pb"
    CONCZN = "Concentrado Zn"
    COLASZN = "Colas Zn"
    CONCFE = "Concentrado Fe"
    COLASFE = "Colas Fe"
    COLASFINALES = "Colas Finales"

# Enum para el tipo de ensaye (ajusta según tus valores)
class TipoEnsayes(str, Enum):
    CONCILIADO = "Laboratorio Conciliado"
    REAL = "Laboratorio Real"

class ElementoCircuitoRequest(BaseModel):
    elemento_id: int  # ID del elemento en la DB
    existencia_teorica: float  # Campo obligatorio
    desviacion_estandar: Optional[float] = None
    contenido: Optional[float] = None
    ley_corregida: Optional[float] = None
    distribucion: Optional[float] = None

class CircuitoRequest(BaseModel):
    etapa: Etapa  # Etapa del circuito
    tms: Optional[float] = None
    elementos: List[ElementoCircuitoRequest]
    
class CreateEnsayeRequest(BaseModel):
    # Campos de Ensaye
    fecha: datetime
    tipo_ensaye: TipoEnsayes  # Usa tu Enum real
    turno: int
    
    # Campos de Producto
    molienda_humeda: float
    humedad: float
    cabeza_general: float
    
    # Circuitos con datos por etapa y elemento
    circuitos: List[CircuitoRequest]

# Get Response
class ElementoResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True

class CircuitoElementoResponse(BaseModel):
    existencia_teorica: float
    desviacion_estandar: Optional[float] = None
    contenido: Optional[float] = None
    ley_corregida: Optional[float] = None
    distribucion: Optional[float] = None
    elemento: ElementoResponse

    class Config:
        from_attributes = True

class CircuitoResponse(BaseModel):
    etapa: str
    tms: Optional[float] = None
    elementos: List[CircuitoElementoResponse]

    class Config:
        from_attributes = True

class ProductoResponse(BaseModel):
    molienda_humeda: float
    humedad: float
    cabeza_general: float

    class Config:
        from_attributes = True 

class EnsayeResponse(BaseModel):
    id: int
    fecha: datetime
    turno: int
    tipo_ensaye: str
    user: UsuarioBase
    producto: ProductoResponse  
    circuitos: List[CircuitoResponse]

    class Config:
        from_attributes = True



