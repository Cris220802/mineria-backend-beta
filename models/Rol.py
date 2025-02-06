from sqlalchemy import String, Integer, Column
from sqlalchemy.orm import relationship
from db.database import Base

class Rol(Base):
    __tablename__ = "rol"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    
    users = relationship("User", back_populates="rol")
