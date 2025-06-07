from fastapi import FastAPI, Depends
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from typing import Annotated
from starlette import status
import lightgbm as lgb # Keep for type hinting if needed, but joblib loads the instance
from sklearn.preprocessing import StandardScaler
import joblib
import boto3
from io import BytesIO
from contextlib import asynccontextmanager

from db.database import engine, Base, get_db
from models.Elemento import Elemento
from models.weaks.Circuito import Circuito
from models.Usuario import User
from models.Ensaye import Ensaye
from models.associations.elemento_circuito import CircuitoElemento
from auth import auth
from auth.auth import get_current_user
from helpers.init_admin import init_admin_user
from ml.artifacts import load_all_artifacts

from router import usuario_router, rol_router, ensaye_router, dashboard_router, reporte_router, prediccion_router

# --- Load Scaler and Models from S3 ---
scaler = None
loaded_models = {}

# Crear las tablas en la base de datos
#Base.metadata.drop_all(engine)  # Borra todas las tablas

Base.metadata.create_all(engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Código a ejecutar antes de que la aplicación empiece a recibir requests (startup)
    print("Iniciando aplicación...")
    db = next(get_db())
    # Inicializar el administrador de la base de datos
    init_admin_user(db)
    try:
        print("Iniciando servidor y cargando artefactos locales...")
        load_all_artifacts()
        print("Artefactos de ML cargados exitosamente durante el inicio.")
    except Exception as e:
        print(f"FALLO AL CARGAR ARTEFACTOS DE ML DURANTE EL INICIO: {e}")
        # Puedes decidir si la app debe fallar en iniciar aquí si los modelos son críticos.
        # Por ejemplo, raise RuntimeError(...)
    yield
    # Código a ejecutar cuando la aplicación se está apagando (shutdown)
    print("Apagando aplicación...")
    
app = FastAPI(lifespan=lifespan)

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
app.include_router(prediccion_router.router)

user_dependency = Annotated[dict, Depends(get_current_user)]

