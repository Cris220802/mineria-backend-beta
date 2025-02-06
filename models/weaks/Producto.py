from sqlalchemy import String, Integer, ForeignKey,  Column, Float
from sqlalchemy.orm import relationship
from db.database import Base

class Producto(Base):
    __tablename__ = "producto"
    
    ensaye_id = Column(Integer, ForeignKey("ensaye.id"), primary_key=True)
    molienda_humeda = Column(Float, nullable=False)
    humedad = Column(Float, nullable=False)
    cabeza_general = Column(Float, nullable=False)
    
    ensaye = relationship("Ensaye", back_populates="producto")