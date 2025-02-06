from pydantic import BaseModel
from schemas.rol_schema import RolBase

class UsuarioBase(BaseModel):
    id: int
    email: str
    name: str
    rol: RolBase
    
    class Config:
        from_attributes=True
        orm_mode=True

class CreateUserRequest(BaseModel):
    email: str
    password: str
    name: str
    rol_id: int
    
    