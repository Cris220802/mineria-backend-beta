
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette import status
from db.database import SessionLocal
from auth.auth import permission_required
from models.Rol import Rol
from schemas.rol_schema import RolBase, RolCreateRequest

router = APIRouter(
    prefix="/rol",
    tags=['rol']
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
db_dependency = Annotated[Session, Depends(get_db)]

@router.get("/", response_model=list[RolBase])
async def read_rols(
    db: db_dependency, 
    permission: dict = Depends(permission_required("Supervisor General"))
):
    rols = db.query(Rol).all() 
    return [RolBase.model_validate(rol) for rol in rols]  