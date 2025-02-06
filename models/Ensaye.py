from sqlalchemy import Column, Integer, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from db.database import Base

# Define el Enum de Python
class TipoEnsayes(str, PyEnum):
    CONCILIADO = "Laboratorio Conciliado"
    REAL = "Laboratorio Real"

class Ensaye(Base):
    __tablename__ = "ensaye"

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(DateTime, nullable=False)
    turno = Column(Integer, nullable=False)
    tipo_ensaye = Column(Enum(TipoEnsayes), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)

    # Relación con el usuario
    user = relationship("User", back_populates="ensayes")

    # Relación con Producto
    producto = relationship("Producto", back_populates="ensaye", uselist=False)  # Relación bidireccional
    
    # Relación con Circuito
    circuitos = relationship("Circuito", back_populates="ensaye")  # Relación bidireccional
