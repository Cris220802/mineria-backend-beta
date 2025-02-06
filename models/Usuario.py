from sqlalchemy import String, Integer, Column, ForeignKey
from sqlalchemy.orm import relationship
from db.database import Base

class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    rol_id = Column(Integer, ForeignKey("rol.id"), nullable=False)
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)

    # Relación con Rol y Ensaye
    rol = relationship("Rol", back_populates="users")
    ensayes = relationship("Ensaye", back_populates="user")
