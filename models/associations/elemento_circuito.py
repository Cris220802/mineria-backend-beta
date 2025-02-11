from sqlalchemy import Integer, Column, Float, ForeignKey, Enum, ForeignKeyConstraint
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from db.database import Base
from models.Elemento import Elemento

class Etapa(str, PyEnum):
    CONCKNELSON = "Concentrado Knelson"
    CABEZA = "Cabeza Flotacion"
    CONCPB = "Concentrado Pb"
    COLASPB = "Colas Pb"
    CONCZN = "Concentrado Zn"
    COLASZN = "Colas Zn"
    CONCFE = "Concentrado Fe"
    COLASFE = "Colas Fe"
    COLASFINALES = "Colas Finales"

class CircuitoElemento(Base):
    __tablename__ = "circuito_elemento"

    circuito_ensaye_id = Column(Integer, primary_key=True)
    circuito_etapa = Column(Enum(Etapa), primary_key=True, nullable=False)
    elemento_id = Column(Integer, ForeignKey("elemento.id"), primary_key=True)
    
    # Datos adicionales
    existencia_teorica = Column(Float, nullable=False)
    desviacion_estandar = Column(Float)
    contenido = Column(Float)
    ley_corregida = Column(Float)
    distribucion = Column(Float)

    # Clave foránea compuesta hacia Circuito (ensaye_id + etapa)
    __table_args__ = (
        ForeignKeyConstraint(
            ['circuito_ensaye_id', 'circuito_etapa'],
            ['circuito.ensaye_id', 'circuito.etapa']
        ),
    )
    
    # Relaciones
    circuito = relationship("Circuito", back_populates="elementos")
    elemento = relationship("Elemento", back_populates="circuitos_association")

