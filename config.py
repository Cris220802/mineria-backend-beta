import pandas as pd # Para training_start_date_for_trend

# --- S3 Configuration ---
S3_BUCKET_NAME = "ai-model-rec"  # Reemplaza con tu bucket
MODEL_S3_PREFIX = "modelos/"      # Reemplaza con tu prefijo en S3

# --- Model Configuration ---
COLUMNA_OBJETIVO = 'pb_recuperacion'
NUM_LAGS = 14
VENTANAS_ROLLING = [3, 5, 7, 14]
PERIODO_ESTACIONAL_PRINCIPAL = 7
HORIZONTES = range(1, 8) # t+1 a t+7

# --- Feature Engineering Configuration ---
# Debes definir esto basado en el inicio de tus datos de entrenamiento
# o guardarlo como metadato junto a tu modelo. Es crucial para 'tendencia_idx'.
# Ejemplo:
# TRAINING_START_DATE_FOR_TREND = pd.Timestamp("2020-01-01")
TRAINING_START_DATE_FOR_TREND = None # ¡IMPORTANTE! Define esto correctamente.

# Nombres de archivo de los artefactos (tal como se guardaron)
SCALER_PB_FILENAME = "scaler_pb.joblib"
MODEL_FILENAME_TEMPLATE = "model_t_plus_{h}_pb.joblib"