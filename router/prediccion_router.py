# app/routers/predict.py

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, Any, Optional, List as PyList
from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
# from sqlalchemy.orm import joinedload # Optimizado para no usarlo si no es necesario para este cálculo

import pandas as pd
import numpy as np

# Modelos de base de datos
from models.Ensaye import Ensaye
from models.Elemento import Elemento
# from models.weaks.Circuito import Circuito # No se usa directamente en la lógica actual de get_pb_recovery_data_from_db
from models.associations.elemento_circuito import CircuitoElemento

# Dependencia de base de datos
from db.database import get_db

# Esquemas Pydantic
from schemas.model_ia import PredictionResponse, HistoricalDataPoint # Importa ambos

# Artefactos de ML y lógica de características
from ml.artifacts import get_scaler, get_models, get_scaler_feature_names
from ml.feature_engineering import generar_caracteristicas_temporales_api

# Configuración
from config import COLUMNA_OBJETIVO, HORIZONTES, NUM_LAGS

# Clases internas para el procesamiento de datos desde la BD
class ElementoValorRecuperacionInternal:
    date: date
    valor: float

router = APIRouter(
    prefix="/predicciones",
    tags=['predicciones']
)

def get_pb_recovery_data_from_db(
    db: Session,
    # Opcional: init_date_param: Optional[date] = None,
    # Opcional: final_date_param: Optional[date] = None
) -> PyList[ElementoValorRecuperacionInternal]:
    """
    Obtiene y procesa los datos de recuperación promedio diaria para el elemento 'PB'.
    La recuperación diaria se calcula como:
    (Suma de todas las 'distribucion' de PB de etapas relevantes en todos los ensayes de un día) / (Número de ensayes en ese día)
    """
    # 1. Encontrar el elemento 'PB'
    pb_elemento_obj = db.query(Elemento).filter(func.upper(Elemento.name) == "PB").first()
    if not pb_elemento_obj:
        raise ValueError("Elemento 'PB' no encontrado en la configuración de la base de datos.")

    # 2. Obtener todos los ensayes (solo ID y fecha para eficiencia)
    # Si se añaden init_date_param y final_date_param, filtrar aquí la query de Ensaye.
    # Por ejemplo:
    # ensaye_query = db.query(Ensaye.id, Ensaye.fecha)
    # if init_date_param:
    #     ensaye_query = ensaye_query.filter(func.date(Ensaye.fecha) >= init_date_param)
    # if final_date_param:
    #     ensaye_query = ensaye_query.filter(func.date(Ensaye.fecha) <= final_date_param)
    # all_ensayes_data = ensaye_query.all()
    all_ensayes_data = db.query(Ensaye.id, Ensaye.fecha).all()

    if not all_ensayes_data:
        return []

    # Mapeos:
    # ensaye_id -> fecha (como objeto date)
    # fecha (como objeto date) -> set de ensaye_ids de ese día
    ensaye_id_to_date_map = {ensaye_id: fecha_ens.date() for ensaye_id, fecha_ens in all_ensayes_data}
    date_to_ensaye_ids_map = {}
    for ensaye_id, fecha_ens_obj in ensaye_id_to_date_map.items():
        if fecha_ens_obj not in date_to_ensaye_ids_map:
            date_to_ensaye_ids_map[fecha_ens_obj] = set()
        date_to_ensaye_ids_map[fecha_ens_obj].add(ensaye_id)

    all_ensayes_ids_list = [ensaye_id for ensaye_id, _ in all_ensayes_data]

    # 3. Obtener datos de CircuitoElemento para 'PB' y etapas relevantes
    etapas_relevantes_pb = ["CONCPB", "CONCZN", "CONCFE"] # Según tu ejemplo
    
    # Seleccionar solo las columnas necesarias de CircuitoElemento
    circuitos_pb_data = db.query(
        CircuitoElemento.circuito_ensaye_id,
        CircuitoElemento.distribucion
    ).filter(
        and_(
            CircuitoElemento.circuito_ensaye_id.in_(all_ensayes_ids_list),
            CircuitoElemento.elemento_id == pb_elemento_obj.id,
            CircuitoElemento.circuito_etapa.in_(etapas_relevantes_pb)
        )
    ).all()

    if not circuitos_pb_data:
        return []

    # 4. Acumular la suma total de 'distribucion' de PB por fecha
    daily_pb_total_distribucion = {}  # {date_obj: sum_of_distribucion_for_pb_on_this_date}
    for ce_ensaye_id, ce_distribucion in circuitos_pb_data:
        ensaye_date_obj = ensaye_id_to_date_map.get(ce_ensaye_id)
        if not ensaye_date_obj: # No debería ocurrir si all_ensayes_ids_list es completo
            continue

        if ensaye_date_obj not in daily_pb_total_distribucion:
            daily_pb_total_distribucion[ensaye_date_obj] = 0.0
        daily_pb_total_distribucion[ensaye_date_obj] += ce_distribucion or 0.0

    # 5. Calcular el promedio diario y construir la lista de resultados
    processed_valores: PyList[ElementoValorRecuperacionInternal] = []
    for current_date_obj, total_dist_for_day in sorted(daily_pb_total_distribucion.items()):
        num_ensayes_on_this_day = len(date_to_ensaye_ids_map.get(current_date_obj, set()))
        
        avg_recovery_for_day = 0.0
        if num_ensayes_on_this_day > 0:
            avg_recovery_for_day = total_dist_for_day / num_ensayes_on_this_day
        
        valor_rec = ElementoValorRecuperacionInternal()
        valor_rec.date = current_date_obj
        valor_rec.valor = avg_recovery_for_day
        processed_valores.append(valor_rec)
        
    # La lista ya está ordenada por fecha debido a sorted(daily_pb_total_distribucion.items())
    return processed_valores


def calculate_trend(predictions: Dict[str, float], last_actual_value: Optional[float] = None) -> str:
    """
    Calcula una tendencia simple basada en las predicciones.
    """
    if not predictions:
        return "Indeterminada"

    sorted_horizons = sorted(predictions.keys(), key=lambda x: int(x.split('_')[-1]))
    if not sorted_horizons:
        return "Indeterminada"

    # Valor inicial para la comparación de tendencia
    val_start_trend = last_actual_value if last_actual_value is not None else predictions[sorted_horizons[0]]
    
    # Valor final (la última predicción)
    val_end_trend = predictions[sorted_horizons[-1]]

    threshold_percentage = 0.5 # Ejemplo: 0.5% de cambio relativo al valor inicial
    
    if val_start_trend == 0: # Evitar división por cero
        if val_end_trend > 0: change_percentage = float('inf')
        elif val_end_trend < 0: change_percentage = float('-inf')
        else: change_percentage = 0.0
    else:
        change_percentage = ((val_end_trend - val_start_trend) / abs(val_start_trend)) * 100

    if change_percentage > threshold_percentage:
        return "Alza"
    elif change_percentage < -threshold_percentage:
        return "Baja"
    else:
        return "Estable"

# --- Endpoint de Predicción ---
@router.post("/pb_recovery_forecast/", response_model=PredictionResponse)
async def predict_pb_recovery_from_db(
    db: Session = Depends(get_db)
    # Opcional: Considera añadir parámetros de Query para init_date y final_date
    # y pasarlos a get_pb_recovery_data_from_db si necesitas controlar el rango de historial.
):
    global_scaler, global_models, global_scaler_feature_names = None, None, None
    try:
        global_scaler = get_scaler()
        global_models = get_models()
        global_scaler_feature_names = get_scaler_feature_names()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=f"Artefactos de ML no disponibles: {str(e)}")

    try:
        # Nota: Si añades parámetros de fecha al endpoint, pásalos aquí:
        # pb_valores_internal: PyList[ElementoValorRecuperacionInternal] = get_pb_recovery_data_from_db(
        #     db=db, init_date_param=parsed_init_date, final_date_param=parsed_final_date
        # )
        pb_valores_internal: PyList[ElementoValorRecuperacionInternal] = get_pb_recovery_data_from_db(db=db)
    except ValueError as ve: # Ej., si 'PB' no se encuentra
        raise HTTPException(status_code=404, detail=str(ve))
        
    if not pb_valores_internal:
        # Considera qué devolver si no hay datos históricos en absoluto
        return PredictionResponse(
            predictions={},
            historical_pb_recovery=[],
            trend="No hay datos históricos de PB disponibles para procesar."
        )

    historical_data_points = [{"date": evr.date, COLUMNA_OBJETIVO: evr.valor} for evr in pb_valores_internal]
    
    history_df = pd.DataFrame(historical_data_points)
    if history_df.empty: # Doble chequeo, aunque pb_valores_internal ya lo cubriría
        return PredictionResponse(
            predictions={},
            historical_pb_recovery=[],
            trend="El DataFrame de datos históricos de PB está vacío."
        )

    history_df['date'] = pd.to_datetime(history_df['date'])
    history_df = history_df.set_index('date').sort_index()
    
    if history_df.index.has_duplicates:
        history_df = history_df.groupby(history_df.index).mean()
    
    # --- Preparar historial para la respuesta ---
    historical_recovery_output: PyList[HistoricalDataPoint] = []
    last_actual_value_for_trend: Optional[float] = None
    if not history_df.empty:
        last_15_days_df = history_df.iloc[-15:] 
        for record_date_idx, row in last_15_days_df.iterrows():
            record_date = record_date_idx.date() 
            value = row[COLUMNA_OBJETIVO]
            historical_recovery_output.append(HistoricalDataPoint(date=record_date, value=value))
        if not last_15_days_df.empty:
            last_actual_value_for_trend = last_15_days_df.iloc[-1][COLUMNA_OBJETIVO]

    # --- Validar y generar características para predicción ---
    min_required_points = NUM_LAGS + 1 # O max(NUM_LAGS, mayor_ventana_rolling) + 1
    if len(history_df) < min_required_points:
        return PredictionResponse(
            predictions={},
            historical_pb_recovery=historical_recovery_output,
            trend=f"Insuficientes datos históricos ({len(history_df)}) para predicción. Se requieren {min_required_points}."
        )

    try:
        features_df = generar_caracteristicas_temporales_api(
            df_entrada=history_df[[COLUMNA_OBJETIVO]], 
            nombre_columna_objetivo=COLUMNA_OBJETIVO,
            training_feature_columns=global_scaler_feature_names
        )
    except ValueError as ve:
        return PredictionResponse(
            predictions={}, historical_pb_recovery=historical_recovery_output,
            trend=f"Error generando características: {str(ve)}"
        )

    latest_features_raw = features_df.iloc[-1:]
    if latest_features_raw.isnull().values.any():
        nan_cols = latest_features_raw.columns[latest_features_raw.isnull().any(axis=0)].tolist()
        return PredictionResponse(
            predictions={}, historical_pb_recovery=historical_recovery_output,
            trend=f"NaNs en características finales: {nan_cols}."
        )
    
    try:
        features_scaled = global_scaler.transform(latest_features_raw[global_scaler_feature_names])
    except Exception as e:
        return PredictionResponse(
            predictions={}, historical_pb_recovery=historical_recovery_output,
            trend=f"Error al escalar características: {str(e)}"
        )

    # --- Realizar Predicciones ---
    predictions_output: Dict[str, float] = {}
    # (El bucle de predicciones se mantiene igual)
    for h in HORIZONTES:
        model_name = f't_plus_{h}'
        model = global_models.get(model_name)
        if model:
            try:
                y_pred_h = model.predict(features_scaled)[0]
                predictions_output[model_name] = float(y_pred_h)
            except Exception as e:
                return PredictionResponse(
                    predictions=predictions_output, # Podrían ser predicciones parciales
                    historical_pb_recovery=historical_recovery_output,
                    trend=f"Error en predicción para {model_name}: {str(e)}"
                )
        else:
            return PredictionResponse(
                predictions=predictions_output,
                historical_pb_recovery=historical_recovery_output,
                trend=f"Modelo {model_name} no encontrado."
            )
    
    # --- Calcular Tendencia ---
    trend_description = calculate_trend(predictions_output, last_actual_value_for_trend)
    
    return PredictionResponse(
        predictions=predictions_output,
        historical_pb_recovery=historical_recovery_output,
        trend=trend_description
    )