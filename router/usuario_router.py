from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Response, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from starlette import status
from passlib.context import CryptContext

from db.database import db_dependency
from models.Usuario import User
from models.Rol import Rol
from schemas.usuario_schema import UsuarioBase, CreateUserRequest, UpdateUserRequest
from auth.auth import permission_required


router = APIRouter(
    prefix="/user",
    tags=['user']
)

bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(
    db: db_dependency, 
    create_user_request: CreateUserRequest,
    permission: dict = Depends(permission_required("Supervisor General"))
):
    # Verificar si el correo electrónico ya está registrado
    existing_user = db.query(User).filter(User.email == create_user_request.email).first()
    
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El correo electrónico ya está registrado en la plataforma")
    
    # Obtener el objeto 'Rol' utilizando el 'rol_id' que se recibe en la solicitud
    rol = db.query(Rol).filter(Rol.id == create_user_request.rol_id).first()
    
    if not rol:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rol no encontrado")
    
    # Crear el modelo de usuario con el rol asignado
    create_user_model = User(
        name=create_user_request.name,
        email=create_user_request.email,
        hashed_password=bcrypt_context.hash(create_user_request.password),
        rol=rol,  # Asignar la instancia de 'Rol' en lugar del 'rol_id'
        active=create_user_request.active
    )
    
    db.add(create_user_model)
    db.commit()
    db.refresh(create_user_model)
    
    return create_user_model

@router.get("/")
async def read_users(
    db: db_dependency,
    permission: dict = Depends(permission_required("Supervisor General")),
    skip: int = Query(0, description="Número de página (0 por defecto)"),
    limit: int = Query(10, le=50, description="Cantidad de registros por página (máx. 50)"),
    user_id: int = Query(None, description="buscar por id de usuario"),
    rol: int = Query(None, description="buscar por rol de usuario"),
    name: str = Query(None, description="buscar por nombre de usuario"),
    ):
    query = db.query(User)
    
    if user_id:
        query = query.filter(User.id == user_id)
        
    if rol:
        query = query.filter(User.rol_id == rol)
    
    if name:
        # Busca cualquier nombre que CONTENGA el texto de 'name', sin importar mayúsculas/minúsculas.
        query = query.filter(User.name.ilike(f"%{name}%"))
        
    total_count = query.count()
    
    users = query.offset(skip * limit).limit(limit).all()
    
    # Convertir a modelos de respuesta
    data = [UsuarioBase.model_validate(user) for user in users]
            
    return {
        "data": data,
        "totalCount": total_count,
        "page": skip,
        "pageSize": limit
    }
    
@router.get("/ensayistas")
async def read_ensayistas(
    db: db_dependency,
    permission: dict = Depends(permission_required("Supervisor General")),
    ):
    users = db.query(User).filter(User.rol_id == 4).all()
       
    # Convertir a modelos de respuesta
    return [UsuarioBase.model_validate(user) for user in users]



@router.get('/{id}', response_model=UsuarioBase)
async def read_user(
    db: db_dependency,
    id: int,
    permission: dict = Depends(permission_required("Supervisor General")),
    ):
    user = db.query(User).filter(User.id == id).first()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    
    return UsuarioBase.model_validate(user)

@router.put('/{id}', response_model=UsuarioBase, status_code=status.HTTP_200_OK)
async def update_user(
    db: db_dependency,
    id: int,
    update_user_request: UpdateUserRequest,
    permission: dict = Depends(permission_required("Supervisor General"))
):
    user = db.query(User).filter(User.id == id).first()
    
    # Verificar si el usuario existe
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    
    # Actualizar los atributos del usuario
    if update_user_request.name:
        user.name = update_user_request.name
    if update_user_request.email:
        user.email = update_user_request.email
    if update_user_request.new_password:
        if not bcrypt_context.verify(update_user_request.confirm_password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La contraseña anterior es incorrecta")
        
        user.hashed_password = bcrypt_context.hash(update_user_request.new_password)
    
    # Verificar si el rol ha cambiado y actualizarlo si es necesario
    if update_user_request.rol_id:
        rol = db.query(Rol).filter(Rol.id == update_user_request.rol_id).first()
        if not rol:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rol no encontrado")
        user.rol = rol
    
    # Guardar los cambios en la base de datos
    db.commit()
    db.refresh(user)  # Refrescar el objeto para asegurarse de tener los últimos datos
    
    return user
    
@router.delete('/{id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    db: db_dependency,
    id: int,
    permission: dict = Depends(permission_required("Supervisor General"))
):
    user = db.query(User).filter(User.id == id).first()
    
    # Verificar si el usuario existe
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    
    # Eliminar el usuario de la base de datos
    db.delete(user)
    db.commit()
    
    return
