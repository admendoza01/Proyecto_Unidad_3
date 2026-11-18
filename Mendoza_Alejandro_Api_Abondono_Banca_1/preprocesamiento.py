import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Traducción de los valores del formulario/API (schemas.py) a las categorías
# EXACTAS con las que se entrenó el preprocesador (preprocesador_banca.joblib).
# Si el OrdinalEncoder recibe una categoría que no conoce, lanza error; el
# OneHotEncoder (handle_unknown='ignore') la ignora en silencio y deja todo a 0.
# ---------------------------------------------------------------------------
MAPA_ESTUDIOS = {
    "Sin estudios": "Primaria",    # SUPUESTO: no existe en el entrenamiento
    "Primarios": "Primaria",
    "Secundarios": "Secundaria",
    "FP": "Secundaria",            # SUPUESTO: no existe en el entrenamiento
    "Universitarios": "Grado",
    "Posgrado": "Master",
}
MAPA_SATISFACCION = {1: "Muy Bajo", 2: "Bajo", 3: "Medio", 4: "Alto", 5: "Muy Alto"}
MAPA_TIPO_CUENTA = {
    "Corriente": "Corriente",
    "Ahorro": "Ahorro",
    "Nómina": "Nomina",
    "Premium": "Inversion",        # SUPUESTO: el entrenamiento no tiene 'Premium'
}
MAPA_CANAL = {
    "Oficina": "Oficina",
    "Web": "Web",
    "App": "App Movil",
    "Teléfono": "Telefono",
}

def preparar_datos_crudos(df_entrada: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica las reglas deterministas de negocio sobre datos crudos:
    - Descarte de identificadores y columnas sin uso en inferencia.
    - Conversión de centinelas a np.nan.
    - Limpieza tipográfica de cadenas de texto.
    - Feature Engineering: cálculo de ratios y tramos.
    """
    df = df_entrada.copy()

    # 0. Traducción de las categorías de la API a las del entrenamiento
    if 'nivel_estudios' in df.columns:
        df['nivel_estudios'] = df['nivel_estudios'].replace(MAPA_ESTUDIOS)
    if 'nivel_satisfaccion' in df.columns:
        df['nivel_satisfaccion'] = df['nivel_satisfaccion'].replace(MAPA_SATISFACCION)
    if 'tipo_cuenta' in df.columns:
        df['tipo_cuenta'] = df['tipo_cuenta'].replace(MAPA_TIPO_CUENTA)
    if 'canal_preferido' in df.columns:
        df['canal_preferido'] = df['canal_preferido'].replace(MAPA_CANAL)

    # 1. Descarte de columnas no utilizables en inferencia
    columnas_descarte = ['id_cliente', 'salario_mensual_aprox', 'comentarios_cliente', 'motivo_cancelacion']
    df = df.drop(columns=columnas_descarte, errors='ignore')

    # 2. Sanitización de centinelas numéricos a NaN
    if 'edad' in df.columns:
        df.loc[(df['edad'] <= 0) | (df['edad'] > 120), 'edad'] = np.nan
    if 'ingresos_anuales' in df.columns:
        df.loc[df['ingresos_anuales'] <= 0, 'ingresos_anuales'] = np.nan
    if 'saldo_cuenta' in df.columns:
        df['saldo_cuenta'] = df['saldo_cuenta'].replace(-999, np.nan)

    # 3. Limpieza tipográfica y centinelas categóricos a NaN
    if 'tipo_cuenta' in df.columns:
        df['tipo_cuenta'] = df['tipo_cuenta'].astype(str).str.strip().str.capitalize()
        df['tipo_cuenta'] = df['tipo_cuenta'].replace({'Desconocido': np.nan, '?': np.nan, 'Nan': np.nan})

    if 'canal_preferido' in df.columns:
        df['canal_preferido'] = df['canal_preferido'].astype(str).str.strip()
        df['canal_preferido'] = df['canal_preferido'].replace({'???': np.nan, 'Nan': np.nan})

    if 'nivel_estudios' in df.columns:
        df['nivel_estudios'] = df['nivel_estudios'].astype(str).str.strip().replace({'Nan': np.nan, 'nan': np.nan})

    # 4. Feature Engineering (Variables derivadas de negocio)
    if 'saldo_cuenta' in df.columns and 'ingresos_anuales' in df.columns:
        df['ratio_saldo_ingresos'] = df['saldo_cuenta'] / (df['ingresos_anuales'] + 1)

    if 'saldo_cuenta' in df.columns and 'num_productos' in df.columns:
        df['saldo_por_producto'] = df['saldo_cuenta'] / df['num_productos']

    if 'edad' in df.columns:
        limites_edad = [0, 30, 55, 120]
        etiquetas_edad = ['Joven', 'Adulto', 'Senior']
        df['grupo_edad'] = pd.cut(df['edad'], bins=limites_edad, labels=etiquetas_edad).astype(str)

    if 'antiguedad_meses' in df.columns:
        df['antiguedad_anios'] = df['antiguedad_meses'] / 12.0
        df = df.drop(columns=['antiguedad_meses'])

    return df