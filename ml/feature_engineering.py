# ml/feature_engineering.py

import pandas as pd
import numpy as np

def generar_caracteristicas_temporales(df_entrada: pd.DataFrame, nombre_columna_objetivo: str, config: dict) -> pd.DataFrame:
    """
    Función interna que replica EXACTAMENTE la creación de features del notebook de entrenamiento.
    """
    df = df_entrada.copy()
    serie_objetivo = df[nombre_columna_objetivo]
    
    num_lags = config["num_lags"]
    ventanas_rolling = config["ventanas_rolling"]
    periodo_estacional = config["periodo_estacional"]

    # 1. Lags
    for i in range(1, num_lags + 1):
        df[f'lag_{i}'] = serie_objetivo.shift(i)

    # 2. Ventanas Móviles (con shift(1) como en el notebook)
    for ventana in ventanas_rolling:
        shifted_series = serie_objetivo.shift(1)
        df[f'rolling_mean_{ventana}'] = shifted_series.rolling(window=ventana).mean()
        df[f'rolling_std_{ventana}'] = shifted_series.rolling(window=ventana).std()
        df[f'rolling_min_{ventana}'] = shifted_series.rolling(window=ventana).min()
        df[f'rolling_max_{ventana}'] = shifted_series.rolling(window=ventana).max()

    # 3. Características de Fecha
    df['dia_semana'] = df.index.dayofweek
    df['dia_mes'] = df.index.day
    df['dia_ano'] = df.index.dayofyear
    df['mes'] = df.index.month
    df['trimestre'] = df.index.quarter
    df['semana_iso'] = df.index.isocalendar().week.astype(int)
    df['ano'] = df.index.year
    
    dow_dummies = pd.get_dummies(df['dia_semana'], prefix='dia_sem', drop_first=False)
    df = pd.concat([df, dow_dummies], axis=1)

    # 4. Fourier
    for k in range(1, (periodo_estacional // 2) + 1):
        df[f'sin_semanal_{k}'] = np.sin(2 * np.pi * k * df['dia_semana'] / periodo_estacional)
        df[f'cos_semanal_{k}'] = np.cos(2 * np.pi * k * df['dia_semana'] / periodo_estacional)
        
    # 5. Tendencia
    df['tendencia_idx'] = np.arange(len(df.index))
    
    # 6. Momentum / Diff (Calculado directamente sobre la serie, como en el notebook)
    df['diff_1'] = serie_objetivo.diff(periods=1)
    df[f'diff_estacional_{periodo_estacional}'] = serie_objetivo.diff(periods=periodo_estacional)
    df['momentum_custom_4'] = serie_objetivo.diff(periods=4)
    
    return df


def generar_caracteristicas_para_prediccion(
    df_historial: pd.DataFrame, 
    nombre_columna_objetivo: str,
    config: dict,
    nombres_features_entrenamiento: list
) -> pd.DataFrame:
    """
    Función principal para la API. Genera características para el historial
    y devuelve solo la última fila válida para la predicción.
    """
    if df_historial.empty:
        raise ValueError("El DataFrame de historial no puede estar vacío.")

    # 1. Generar características para todo el historial disponible
    df_con_features = generar_caracteristicas_temporales(
        df_entrada=df_historial,
        nombre_columna_objetivo=nombre_columna_objetivo,
        config=config
    )

    # 2. Tomar la última fila. Esta fila contiene todas las features calculadas
    #    basadas en el último punto de datos conocido.
    latest_features = df_con_features.iloc[-1:]

    # 3. Asegurar el orden correcto de las columnas y rellenar cualquier posible NaN
    #    (que no debería ocurrir en la última fila si hay suficientes datos).
    return latest_features.reindex(columns=nombres_features_entrenamiento, fill_value=0)