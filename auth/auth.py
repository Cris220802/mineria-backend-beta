from datetime import timedelta, datetime
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Response, Cookie
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status

from db.database import SessionLocal
from models.Usuario import User
from models.Rol import Rol
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import jwt, JWTError
from schemas.token_schema import Token

router = APIRouter(
    prefix="/auth",
    tags=['auth']
)

SECRET_KEY = 'lkrQxb4Tk0cZtL_8FOHy9xGRyaDSeJGVVV3F3WvIk5E'
ALGORITHM = 'HS256'

bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_beaer = OAuth2PasswordBearer(tokenUrl='/auth/token')

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
db_dependency = Annotated[Session, Depends(get_db)]
    
@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: db_dependency, response: Response):
    user = autenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales Incorrectas")
    
    token = create_access_token(user.email, user.id, timedelta(minutes=1440))
    
     # Configurar la cookie
    response.set_cookie(
        key="access_token",
        value=token,  # Solo el token, sin "Bearer"
        httponly=True,  # Previene acceso a la cookie via JavaScript
        secure=True,    # Solo enviar la cookie sobre HTTPS, mientras False, cuando este en produccion True
        samesite="None", # Previene envío de la cookie en solicitudes cross-site
        max_age=1440 * 60  # Duración en segundos (20 minutos)
    )
    
    return {"access_token": token, "token_type": "bearer"}

def autenticate_user(email, password, db: db_dependency):
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        return False
    
    if not bcrypt_context.verify(password, user.hashed_password):
        return False
    
    return user

async def get_token_from_cookie(access_token: str = Cookie(None)):
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se proporcionó un token de acceso"
        )
    return access_token

def create_access_token(email: str, user_id: int, expires_delta: timedelta):
    encode = {'sub': email, 'id': user_id}
    expires = datetime.utcnow() + expires_delta
    encode.update({'exp': expires})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: Annotated[str, Depends(get_token_from_cookie)]):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get('sub')
        user_id: int = payload.get('id')
        if email is None or user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalido")
        return {'email': email, 'user_id': user_id}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalido")
    
def permission_required(*required_roles: str):
    def permission_dependency(
        db: db_dependency, 
        current_user: dict = Depends(get_current_user)
    ):
        # Obtenemos el usuario y su rol
        user = db.query(User).filter(User.id == current_user["user_id"]).first()
        
        # Verificar si el usuario y su rol existen
        if not user or not user.rol_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acceso denegado. Rol no asignado o usuario inexistente"
            )
        # Verificar si el rol del usuario está en los roles requeridos
        if user.rol.name not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acceso denegado. Se requiere uno de los roles: {', '.join(required_roles)}"
            )
        
        return user
    return permission_dependency