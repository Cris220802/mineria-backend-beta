from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Optional, List as PyList
from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from enum import Enum
import pandas as pd

# Modelos de base de datos y dependencia
from models.Elemento import Elemento
from models.Ensaye import Ensaye
from models.associations.elemento_circuito import CircuitoElemento
from db.database import get_db

# Esquemas Pydantic
from schemas.model_ia import PredictionResponse, HistoricalDataPoint

# Lógica de ML y Configuración
from ml.artifacts import get_artifacts_for_element
# ¡IMPORTANTE! Asegúrate de que esta función exista en tu carpeta ml/
from ml.feature_engineering import generar_caracteristicas_para_prediccion 
from config import ELEMENT_CONFIG, HORIZONTES
from auth.auth import permission_required


# --- Clases Internas y Enums ---

class ElementoValorRecuperacionInternal:
    """Clase interna para el manejo de datos procesados desde la BD."""
    date: date
    valor: float

# Enum para validación de rutas en FastAPI, se basa en tu config
class ElementSymbol(str, Enum):
    Pb = "Pb"
    Au = "Au"
    Ag = "Ag"
    Zn = "Zn"
    # Añade aquí otros elementos si los configuras, ej: Zn = "Zn"
    
router = APIRouter(
    prefix="/predicciones",
    tags=['Predicciones Dinámicas']
)

# --- Funciones de Lógica de Datos ---

def get_recovery_data_from_db(
    db: Session, 
    element_name: str,
    days_limit: int = 90  # Límite de días para optimizar la consulta
) -> PyList[ElementoValorRecuperacionInternal]:
    """
    Obtiene y procesa los datos de recuperación promedio diaria para un elemento específico.
    """
    print(f"Obteniendo los últimos {days_limit} días de datos para el elemento: {element_name.upper()}...")
    
    elemento_obj = db.query(Elemento).filter(func.upper(Elemento.name) == element_name.upper()).first()
    if not elemento_obj:
        raise ValueError(f"Elemento '{element_name}' no encontrado en la base de datos.")

    start_date_filter = date.today() - timedelta(days=days_limit)
    all_ensayes_data = db.query(
        Ensaye.id, 
        Ensaye.fecha
    ).filter(
        func.date(Ensaye.fecha) >= start_date_filter
    ).all()

    if not all_ensayes_data:
        return []

    ensaye_id_to_date_map = {ensaye_id: fecha_ens.date() for ensaye_id, fecha_ens in all_ensayes_data}
    date_to_ensaye_ids_map = {}
    for ensaye_id, fecha_ens_obj in ensaye_id_to_date_map.items():
        date_to_ensaye_ids_map.setdefault(fecha_ens_obj, set()).add(ensaye_id)

    all_ensayes_ids_list = list(ensaye_id_to_date_map.keys())
    etapas_relevantes = ["CONCPB", "CONCZN", "CONCFE"]
    
    circuitos_data = db.query(
        CircuitoElemento.circuito_ensaye_id,
        CircuitoElemento.distribucion
    ).filter(
        and_(
            CircuitoElemento.circuito_ensaye_id.in_(all_ensayes_ids_list),
            CircuitoElemento.elemento_id == elemento_obj.id,
            CircuitoElemento.circuito_etapa.in_(etapas_relevantes)
        )
    ).all()
    
    if not circuitos_data:
        return []

    daily_total_distribucion = {}
    for ce_ensaye_id, ce_distribucion in circuitos_data:
        ensaye_date_obj = ensaye_id_to_date_map.get(ce_ensaye_id)
        if ensaye_date_obj:
            daily_total_distribucion[ensaye_date_obj] = daily_total_distribucion.get(ensaye_date_obj, 0.0) + (ce_distribucion or 0.0)

    processed_valores: PyList[ElementoValorRecuperacionInternal] = []
    for current_date, total_dist in sorted(daily_total_distribucion.items()):
        num_ensayes_on_day = len(date_to_ensaye_ids_map.get(current_date, set()))
        avg_recovery = total_dist / num_ensayes_on_day if num_ensayes_on_day > 0 else 0.0
        
        valor_rec = ElementoValorRecuperacionInternal()
        valor_rec.date = current_date
        valor_rec.valor = avg_recovery
        processed_valores.append(valor_rec)
        
    return processed_valores

def calculate_trend(predictions: Dict[str, float], last_actual_value: Optional[float] = None) -> str:
    if not predictions: return "Indeterminada"
    sorted_horizons = sorted(predictions.keys(), key=lambda x: int(x.split('_')[-1]))
    if not sorted_horizons: return "Indeterminada"
    val_start_trend = last_actual_value if last_actual_value is not None else predictions[sorted_horizons[0]]
    val_end_trend = predictions[sorted_horizons[-1]]
    threshold = 0.5 
    if val_start_trend == 0:
        change_percentage = float('inf') if val_end_trend > 0 else 0.0
    else:
        change_percentage = ((val_end_trend - val_start_trend) / abs(val_start_trend)) * 100
    if change_percentage > threshold: return "Alza"
    elif change_percentage < -threshold: return "Baja"
    else: return "Estable"

# --- ENDPOINT DE PREDICCIÓN GENÉRICO ---
@router.post("/forecast/{element_symbol}", response_model=PredictionResponse)
async def predict_recovery_forecast(
    element_symbol: ElementSymbol,
    db: Session = Depends(get_db),
    permission: dict = Depends(permission_required("Supervisor General", "Supervisor de Planta"))
):
    element = element_symbol.value
    try:
        config = ELEMENT_CONFIG[element]
        artifacts = get_artifacts_for_element(element)
        scaler, models, feature_names = artifacts["scaler"], artifacts["models"], artifacts["feature_names"]
        columna_objetivo, num_lags = config["columna_objetivo"], config["num_lags"]
        
        historical_values = get_recovery_data_from_db(db=db, element_name=element, days_limit=90)
        
        if not historical_values:
            return PredictionResponse(element=element, prediction_type="Sin Datos", predictions={}, historical_data=[], trend="Indeterminada", isError=True, detail="No hay datos históricos disponibles para procesar.")

        history_df = pd.DataFrame([{"date": evr.date, columna_objetivo: evr.valor} for evr in historical_values])
        history_df['date'] = pd.to_datetime(history_df['date'])
        history_df = history_df.set_index('date').sort_index().groupby(level=0).mean()
        
        historical_output = [HistoricalDataPoint(date=idx.date(), value=row[columna_objetivo]) for idx, row in history_df.iloc[-15:].iterrows()]
        last_actual_value = history_df.iloc[-1][columna_objetivo]

        max_rolling_window = max(config.get("ventanas_rolling", [0]))
        min_points_for_robust = max(num_lags, max_rolling_window) + 1

        if len(history_df) >= min_points_for_robust:
            print(f"Datos suficientes ({len(history_df)} >= {min_points_for_robust}). Realizando predicción robusta.")
            features_df = generar_caracteristicas_para_prediccion(
                df_historial=history_df,
                nombre_columna_objetivo=columna_objetivo,
                config=config,
                nombres_features_entrenamiento=feature_names
            )
            
            if features_df.isnull().values.any():
                nan_cols = features_df.columns[features_df.isna().any()].tolist()
                return PredictionResponse(element=element, prediction_type="Error de Características", predictions={}, historical_data=historical_output, trend="Indeterminada", isError=True, detail=f"NaNs encontrados en características: {nan_cols}.")

            features_scaled = scaler.transform(features_df)
            
            predictions_output = {f't_plus_{h}': float(models[f't_plus_{h}'].predict(features_scaled)[0]) for h in HORIZONTES}
            trend = calculate_trend(predictions_output, last_actual_value)
            
            return PredictionResponse(element=element, prediction_type="Robusta (ML)", predictions=predictions_output, historical_data=historical_output, trend=trend)
        else:
            print(f"Datos insuficientes ({len(history_df)} < {min_points_for_robust}). Realizando predicción simple.")
            predictions_output = {f't_plus_{h}': last_actual_value for h in HORIZONTES}
            
            return PredictionResponse(
                element=element,
                prediction_type="Simple (Datos Insuficientes)",
                predictions=predictions_output,
                historical_data=historical_output,
                trend="Estable"
            )

    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=503, detail=f"Artefactos de ML no disponibles: {str(re)}")
    except Exception as e:
        print(f"ERROR INESPERADO: {e}") # Loguear el error real para depuración
        raise HTTPException(status_code=500, detail=f"Error inesperado durante la predicción.")