from pydantic import BaseModel
from schemas.rol_schema import RolBase
from typing import Optional

class UsuarioBase(BaseModel):
    id: int
    email: str
    name: str
    rol: RolBase
    active: bool
    
    class Config:
        from_attributes=True
        orm_mode=True

class CreateUserRequest(BaseModel):
    email: str
    password: str
    name: str
    rol_id: int
    active: bool
    
class UpdateUserRequest(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = None
    confirm_password: Optional[str] = None
    new_password: Optional[str] = None
    rol_id: Optional[int] = None
    active: Optional[int] = None
    
    