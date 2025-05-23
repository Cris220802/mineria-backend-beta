from fastapi import FastAPI, Depends
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
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

from router import usuario_router, rol_router, ensaye_router, dashboard_router, reporte_router


# Crear las tablas en la base de datos
# Base.metadata.drop_all(engine)  # Borra todas las tablas
Base.metadata.create_all(engine)

app = FastAPI()

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="MinerIA",
        version="1.0.0",
        description="API de aplicacion Web MinerIA",
        routes=app.routes,
    )
    
    # Habilitar withCredentials en Swagger UI
    openapi_schema["components"]["securitySchemes"] = {
        "cookieAuth": {
            "type": "apiKey",
            "in": "cookie",
            "name": "access_token",
        }
    }
    openapi_schema["security"] = [{"cookieAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Origen de tu frontend
    allow_credentials=True,  # Permitir cookies
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # Permitir todos los métodos (GET, POST, etc.)
    allow_headers=["Authorization", "Content-Type", "X-Requested-With", "Accept", "Origin"],  # Permitir todos los headers
)


app.include_router(auth.router)
app.include_router(usuario_router.router)
app.include_router(rol_router.router)
app.include_router(ensaye_router.router)
app.include_router(dashboard_router.router)
app.include_router(reporte_router.router)

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