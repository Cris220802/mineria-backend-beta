from pydantic import BaseModel

class RolBase(BaseModel):
    id: int
    name: str
    
    class Config:
        from_attributes=True
        orm_mode=True
    
class RolCreateRequest(BaseModel):
    name: str
