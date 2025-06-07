import joblib
from typing import Dict, Any
import os
from pathlib import Path # Usaremos pathlib para un manejo de rutas más robusto

# Importamos la nueva configuración
from config import (
    LOCAL_MODELS_DIR, # <-- ¡Importante!
    HORIZONTES,
    ELEMENT_CONFIG
)

# --- Ya no se necesita boto3, dotenv, ni asyncio ---

# La estructura de datos global no cambia
ML_ARTIFACTS: Dict[str, Dict[str, Any]] = {}

def load_artifacts_for_element(element: str):
    """Carga el scaler y los modelos para un elemento específico desde el disco local."""
    global ML_ARTIFACTS

    if element in ML_ARTIFACTS:
        print(f"Artefactos para '{element}' ya están cargados.")
        return

    print(f"Cargando artefactos locales para el elemento: '{element}'...")
    
    config = ELEMENT_CONFIG.get(element)
    if not config:
        raise ValueError(f"No se encontró configuración para el elemento '{element}'.")

    base_path = Path(LOCAL_MODELS_DIR)
    artifacts = {"scaler": None, "models": {}, "feature_names": []}
    
    # 1. Cargar Scaler desde archivo local
    scaler_path = base_path / config['scaler_filename']
    if not scaler_path.is_file():
        raise FileNotFoundError(f"No se encontró el archivo scaler para '{element}' en: {scaler_path}")
    
    artifacts["scaler"] = joblib.load(scaler_path)
    
    if hasattr(artifacts["scaler"], 'feature_names_in_'):
        artifacts["feature_names"] = list(artifacts["scaler"].feature_names_in_)
    
    print(f"Scaler para '{element}' cargado desde {scaler_path}.")

    # 2. Cargar Modelos desde archivos locales
    for h in HORIZONTES:
        model_filename = config['model_filename_template'].format(h=h)
        model_path = base_path / model_filename
        
        if not model_path.is_file():
            raise FileNotFoundError(f"No se encontró el archivo de modelo para '{element}' en: {model_path}")
            
        model_name = f't_plus_{h}'
        artifacts["models"][model_name] = joblib.load(model_path)
    
    print(f"{len(artifacts['models'])} modelos para '{element}' cargados exitosamente.")
    
    ML_ARTIFACTS[element] = artifacts

def load_all_artifacts():
    """Función principal que carga los artefactos para todos los elementos definidos."""
    print("Iniciando carga de artefactos de ML desde el disco local...")
    try:
        for element_symbol in ELEMENT_CONFIG:
            load_artifacts_for_element(element_symbol)
        print("Carga de todos los artefactos completada.")
    except Exception as e:
        # Un error aquí es crítico y debe detener el inicio de la app
        print(f"Error crítico al cargar artefactos locales: {e}")
        raise RuntimeError(f"Falla al cargar artefactos de ML: {e}")

def get_artifacts_for_element(element: str) -> Dict[str, Any]:
    """Obtiene de forma segura los artefactos para un elemento."""
    if element not in ML_ARTIFACTS:
        # En un entorno local, la carga es tan rápida que no debería ocurrir si load_all_artifacts se llamó al inicio.
        # Si ocurre, es un error de configuración.
         raise RuntimeError(f"Los artefactos para '{element}' no fueron cargados. Verifica la configuración y el arranque de la app.")
    return ML_ARTIFACTS[element]