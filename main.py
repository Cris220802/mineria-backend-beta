from fastapi import FastAPI, Depends
from typing import Annotated
from starlette import status
from db.database import engine, Base, get_db
from models.Elemento import Elemento
from models.weaks.Circuito import Circuito
from models.Usuario import User
from models.Ensaye import Ensaye
from models.associations.elemento_circuito import CircuitoElemento
from auth import auth
from auth.auth import get_current_user
from helpers.init_admin import init_admin_user

from router import usuario_router, rol_router, ensaye_router


# Crear las tablas en la base de datos
# Base.metadata.drop_all(engine)  # Borra todas las tablas
Base.metadata.create_all(engine)

app = FastAPI()
app.include_router(auth.router)
app.include_router(usuario_router.router)
app.include_router(rol_router.router)
app.include_router(ensaye_router.router)

user_dependency = Annotated[dict, Depends(get_current_user)]

# Manejador del evento `startup`
@app.on_event("startup")
async def startup_event():
    db = next(get_db())
    # Inicializar el administrador de la base de datos
    init_admin_user(db)
    
# @app.get("/", status_code=status.HTTP_200_OK)
# async def user(user: user_dependency, db: db_dependency):
#     if user is None:
#         raise HTTPException(status_code=401, detail="Autenticación Fallida")
#     return {"user": user}