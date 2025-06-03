import boto3
import joblib
from io import BytesIO
from typing import Dict, Any
from sklearn.preprocessing import StandardScaler
# Asumiendo que LightGBMRegressor fue guardado con joblib, si no, ajusta la carga
# from lightgbm import LGBMRegressor # Solo para type hinting si es necesario

from config import (
    S3_BUCKET_NAME,
    MODEL_S3_PREFIX,
    HORIZONTES,
    SCALER_PB_FILENAME,
    MODEL_FILENAME_TEMPLATE
)

# Variables globales para almacenar los artefactos cargados
SCALER: StandardScaler = None
MODELS: Dict[str, Any] = {} # Ej: {"t_plus_1": LGBMRegressor(), ...}
SCALER_FEATURE_NAMES: list = None # Almacenará scaler.feature_names_in_

def load_all_artifacts():
    global SCALER, MODELS, SCALER_FEATURE_NAMES
    
    if SCALER and MODELS: # Evita recargar si ya están cargados
        print("Artefactos de ML ya están cargados.")
        return

    s3_client = boto3.client(
        's3',
        aws_access_key_id='AKIAYGGSJA5XGZ6SIYGM',
        aws_secret_access_key='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',
        region_name='us-east-1'
    )
    print("Cargando artefactos de ML desde S3...")

    try:
        # Cargar Scaler
        scaler_key = f"{MODEL_S3_PREFIX}{SCALER_PB_FILENAME}"
        scaler_obj = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=scaler_key)
        scaler_bytes = BytesIO(scaler_obj['Body'].read())
        SCALER = joblib.load(scaler_bytes)
        # Guardar los nombres de las características que el scaler espera
        if hasattr(SCALER, 'feature_names_in_'):
            SCALER_FEATURE_NAMES = list(SCALER.feature_names_in_)
        else:
            # Si feature_names_in_ no está (versiones antiguas de sklearn),
            # necesitarías haber guardado esta lista por separado.
            print("Advertencia: scaler.feature_names_in_ no encontrado. La validación de columnas puede ser incompleta.")
            # Deberías tener una forma de obtener esta lista si no está en el scaler.
            # SCALER_FEATURE_NAMES = [...] # Cargarla desde un archivo de metadatos por ejemplo

        print(f"Scaler cargado. Espera {len(SCALER_FEATURE_NAMES or [])} características: {SCALER_FEATURE_NAMES}")


        # Cargar Modelos
        for h in HORIZONTES:
            model_filename = MODEL_FILENAME_TEMPLATE.format(h=h)
            model_key = f"{MODEL_S3_PREFIX}{model_filename}"
            model_obj = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=model_key)
            model_bytes = BytesIO(model_obj['Body'].read())
            
            model_name = f't_plus_{h}' # Ej: 't_plus_1'
            MODELS[model_name] = joblib.load(model_bytes)
        print(f"{len(MODELS)} modelos cargados exitosamente.")

    except Exception as e:
        print(f"Error crítico al cargar artefactos de ML desde S3: {e}")
        # Decide cómo manejar esto: ¿elevar una excepción para detener el inicio de la app?
        # ¿o permitir que la app inicie pero las rutas de predicción fallen?
        # Por seguridad, es mejor elevar la excepción para saber que algo anda mal.
        raise RuntimeError(f"Falla al cargar artefactos de ML: {e}")

# Opcional: funciones getter para acceder a los artefactos de forma segura
def get_scaler() -> StandardScaler:
    if not SCALER:
        raise RuntimeError("Scaler no ha sido cargado. Asegúrate de llamar a load_all_artifacts().")
    return SCALER

def get_models() -> Dict[str, Any]:
    if not MODELS:
        raise RuntimeError("Modelos no han sido cargados. Asegúrate de llamar a load_all_artifacts().")
    return MODELS

def get_scaler_feature_names() -> list:
    if not SCALER_FEATURE_NAMES:
         # Esto podría pasar si SCALER no se cargó o feature_names_in_ no estaba disponible.
        raise RuntimeError("Nombres de características del scaler no disponibles. Asegúrate de que el scaler esté cargado y tenga 'feature_names_in_'.")
    return SCALER_FEATURE_NAMES