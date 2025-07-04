from sqlalchemy import String, Integer, Column, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from db.database import Base
from models.Rol import Rol

class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    rol_id = Column(Integer, ForeignKey("rol.id"), nullable=False)
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    active = Column(Boolean, nullable=False)

    # Relación con Rol y Ensaye
    rol = relationship("Rol", back_populates="users")
    ensayes = relationship("Ensaye", back_populates="user")
