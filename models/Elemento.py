from sqlalchemy import String, Integer, Column
from sqlalchemy.orm import relationship
from db.database import Base

class Elemento(Base):
    __tablename__ = "elemento"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)

    # Relación con la tabla asociativa
    circuitos_association = relationship("CircuitoElemento", back_populates="elemento")
