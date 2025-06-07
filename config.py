import pandas as pd # Para training_start_date_for_trend

import pandas as pd

# --- NUEVA CONFIGURACIÓN DE RUTA LOCAL ---
# Apunta a la carpeta que creaste en el Paso 1.
LOCAL_MODELS_DIR = "ml_models/" 

# --- S3 Configuration (YA NO SE NECESITA) ---
# S3_BUCKET_NAME = "ai-model-rec"  <-- Eliminar
# MODEL_S3_PREFIX = "modelos/"     <-- Eliminar

# --- El resto de la configuración permanece igual ---
HORIZONTES = range(1, 8)

# --- Configuración Específica por Elemento ---
ELEMENT_CONFIG = {
    "Pb": {
        "scaler_filename": "scaler_pb.joblib",
        "model_filename_template": "model_t_plus_{h}_pb.joblib",
        "columna_objetivo": "pb_recuperacion",
        "num_lags": 14,
        "ventanas_rolling": [3, 5, 7, 14],
        "periodo_estacional": 7
    },
    "Au": {
        "scaler_filename": "scaler_au.joblib",
        "model_filename_template": "model_t_plus_{h}_au.joblib",
        "columna_objetivo": "au_recuperacion",
        "num_lags": 5,
        "ventanas_rolling": [3, 5, 7, 14],
        "periodo_estacional": 7
    },
    "Ag": {
        "scaler_filename": "scaler_ag.joblib",
        "model_filename_template": "model_t_plus_{h}_ag.joblib",
        "columna_objetivo": "ag_recuperacion",
        "num_lags": 14,
        "ventanas_rolling": [3, 5, 7, 14],
        "periodo_estacional": 7
    },
    "Zn": {
        "scaler_filename": "scaler_zn.joblib",
        "model_filename_template": "model_t_plus_{h}_zn.joblib",
        "columna_objetivo": "zn_recuperacion",
        "num_lags": 10,
        "ventanas_rolling": [3, 5, 7, 14],
        "periodo_estacional": 7
    },
}

# --- General Model Configuration ---
HORIZONTES = range(1, 8) # t+1 a t+7


# --- Feature Engineering Configuration ---
# Debes definir esto basado en el inicio de tus datos de entrenamiento
# o guardarlo como metadato junto a tu modelo. Es crucial para 'tendencia_idx'.
# Ejemplo:
# TRAINING_START_DATE_FOR_TREND = pd.Timestamp("2024-01-01")
# TRAINING_START_DATE_FOR_TREND = None # ¡IMPORTANTE! Define esto correctamente.
