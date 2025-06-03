import pandas as pd
import numpy as np
from config import (
    COLUMNA_OBJETIVO,
    NUM_LAGS,
    VENTANAS_ROLLING,
    PERIODO_ESTACIONAL_PRINCIPAL,
    TRAINING_START_DATE_FOR_TREND # Importante para la consistencia de 'tendencia_idx'
)

def generar_caracteristicas_temporales_api(
    df_entrada: pd.DataFrame,
    nombre_columna_objetivo: str = COLUMNA_OBJETIVO,
    num_lags: int = NUM_LAGS,
    ventanas_rolling: list = VENTANAS_ROLLING,
    periodo_estacional_principal: int = PERIODO_ESTACIONAL_PRINCIPAL,
    training_feature_columns: list = None, # Lista de columnas que el scaler espera
    training_start_date: pd.Timestamp = TRAINING_START_DATE_FOR_TREND
):
    if not isinstance(df_entrada.index, pd.DatetimeIndex):
        raise ValueError("El DataFrame de entrada debe tener un DatetimeIndex.")
    if not training_feature_columns:
        raise ValueError("'training_feature_columns' (proveniente de scaler.feature_names_in_) es requerido.")

    df = df_entrada.copy()
    serie_objetivo = df[nombre_columna_objetivo]

    # 1. Lags
    for i in range(1, num_lags + 1):
        df[f'lag_{i}'] = serie_objetivo.shift(i)

    # 2. Rolling Window
    for ventana in ventanas_rolling:
        df[f'rolling_mean_{ventana}'] = serie_objetivo.rolling(window=ventana, min_periods=1).mean().shift(1)
        df[f'rolling_std_{ventana}'] = serie_objetivo.rolling(window=ventana, min_periods=1).std().shift(1)
        df[f'rolling_min_{ventana}'] = serie_objetivo.rolling(window=ventana, min_periods=1).min().shift(1)
        df[f'rolling_max_{ventana}'] = serie_objetivo.rolling(window=ventana, min_periods=1).max().shift(1)

    # 3. Date/Time
    df['dia_semana'] = df.index.dayofweek
    df['dia_mes'] = df.index.day
    df['dia_ano'] = df.index.dayofyear
    df['mes'] = df.index.month
    df['trimestre'] = df.index.quarter
    df['semana_iso'] = df.index.isocalendar().week.astype(int)
    df['ano'] = df.index.year

    df_dow_dummies = pd.get_dummies(df['dia_semana'], prefix='dia_sem', drop_first=False)
    for i in range(7):
        col_name = f'dia_sem_{i}'
        if col_name not in df_dow_dummies.columns and col_name in training_feature_columns:
            df_dow_dummies[col_name] = 0 # Asegura que exista si el scaler la espera
    
    # Solo añade las columnas dummy que realmente se usaron en el entrenamiento
    expected_dow_cols = [f'dia_sem_{i}' for i in range(7) if f'dia_sem_{i}' in training_feature_columns]
    df = pd.concat([df, df_dow_dummies[expected_dow_cols]], axis=1)


    # 4. Fourier
    if periodo_estacional_principal == 7:
        for k in range(1, (periodo_estacional_principal // 2) + 1):
            sin_col = f'sin_semanal_{k}'
            cos_col = f'cos_semanal_{k}'
            if sin_col in training_feature_columns:
                 df[sin_col] = np.sin(2 * np.pi * k * df['dia_semana'] / periodo_estacional_principal)
            if cos_col in training_feature_columns:
                 df[cos_col] = np.cos(2 * np.pi * k * df['dia_semana'] / periodo_estacional_principal)

    # 5. Trend
    if 'tendencia_idx' in training_feature_columns:
        if training_start_date:
            df['tendencia_idx'] = (df.index - training_start_date).days
        else:
            print("ADVERTENCIA: 'tendencia_idx' podría ser inconsistente. Define 'TRAINING_START_DATE_FOR_TREND' en config.py.")
            # Si no se proporciona training_start_date, esta es una aproximación que puede no ser correcta
            # dependiendo de cómo se entrenó el modelo y la longitud de df_entrada.
            # Es mejor asegurarse de que training_start_date esté configurado.
            df['tendencia_idx'] = np.arange(len(df.index)) + (df_entrada.iloc[0]['tendencia_idx_base'] if 'tendencia_idx_base' in df_entrada.columns else 0)


    # 6. Momentum / Rate of Change
    # Genera estas características solo si están en training_feature_columns
    if 'diff_1' in training_feature_columns:
        df['diff_1'] = serie_objetivo.diff(periods=1)
    estacional_diff_col = f'diff_estacional_{periodo_estacional_principal}'
    if periodo_estacional_principal > 1 and estacional_diff_col in training_feature_columns:
        df[estacional_diff_col] = serie_objetivo.diff(periods=periodo_estacional_principal)
    if 'momentum_custom_4' in training_feature_columns:
        df['momentum_custom_4'] = serie_objetivo - serie_objetivo.shift(4)
    
    # Asegura que solo se devuelvan las columnas que el scaler espera, en el orden correcto
    final_features_df = pd.DataFrame(index=df.index)
    missing_cols_for_scaler = []
    for col in training_feature_columns:
        if col in df.columns:
            final_features_df[col] = df[col]
        else:
            # Esta columna era esperada por el scaler pero no se pudo generar.
            # Esto podría indicar un problema en la lógica de arriba o que la característica
            # venía de una fuente externa durante el entrenamiento.
            # Por ahora, llenamos con NaN y dejamos que el manejo de errores posterior lo detecte.
            final_features_df[col] = np.nan
            missing_cols_for_scaler.append(col)
    
    if missing_cols_for_scaler:
        print(f"Advertencia: Las siguientes columnas esperadas por el scaler no se pudieron generar y se llenaron con NaN: {missing_cols_for_scaler}")

    return final_features_df