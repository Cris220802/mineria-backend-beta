from sqlalchemy import Integer, Column, Enum, ForeignKey, Float
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from db.database import Base
from models.associations.elemento_circuito import CircuitoElemento
from models.Ensaye import Ensaye

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

class Circuito(Base):
    __tablename__ = "circuito"

    ensaye_id = Column(Integer, ForeignKey("ensaye.id"), primary_key=True)
    etapa = Column(Enum(Etapa), primary_key=True)
    tms = Column(Float)

    # Relación con Ensaye
    ensaye = relationship("Ensaye", back_populates="circuitos")

    # Relación con la tabla asociativa
    elementos = relationship(
        "CircuitoElemento",
        back_populates="circuito",
        foreign_keys="[CircuitoElemento.circuito_ensaye_id, CircuitoElemento.circuito_etapa]"
    )
    