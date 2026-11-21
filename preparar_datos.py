"""
preparar_datos.py - GlobalRide (Avance 2)
Un solo comando:  python preparar_datos.py
1) Si no existe datos_crudos.csv, lo simula con supuestos documentados.
2) Limpia: duplicados, texto, tipos, faltantes.
3) Guarda datos_limpios.csv (12 columnas) y muestra un resumen.
"""
import os
import numpy as np
import pandas as pd

SEMILLA = 42
N_VIAJES = 1000
ZONAS = ["Centro", "Norte", "Sur", "Oriente", "Poniente", "Jesus Maria"]
DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes"]


def simular_crudos(ruta):
    """Simula 1000 solicitudes de viaje (supuestos de la encuesta) y les mete suciedad."""
    rng = np.random.default_rng(SEMILLA)
    n = N_VIAJES
    zona_origen = rng.choice(ZONAS, n, p=[0.25, 0.18, 0.17, 0.15, 0.15, 0.10])
    zona_destino = rng.choice(["Centro", "Norte"], n, p=[0.45, 0.55])  # campus principal y campus norte
    distancia = np.clip(rng.normal(9, 4, n), 1, 30)
    desviacion = np.clip(rng.exponential(5, n), 0, 30)
    hora = np.clip(rng.normal(8.5, 3.0, n), 5, 21)
    dif_horaria = np.clip(np.abs(rng.normal(0, 18, n)), 0, 90)
    dia = rng.choice(DIAS, n)
    asientos = rng.integers(1, 5, n)
    coop = np.clip(rng.normal(30, 12, n), 5, 80).round(0)
    calif = np.clip(rng.normal(4.4, 0.4, n), 3, 5).round(2)
    viajes_prev = rng.poisson(3, n)

    # Regla de la etiqueta: puntaje que mezcla factores + azar (no es una regla exacta)
    puntaje = (1.6
               - 0.16 * desviacion
               - 0.045 * dif_horaria
               + 0.9 * (calif - 4.4)
               + 0.12 * np.minimum(viajes_prev, 8)
               - 0.02 * np.abs(coop - 3 * distancia)   # cooperación justa ~ $3 por km
               + 0.1 * (asientos >= 2)
               + 0.6 * (zona_origen == "Centro"))
    prob = 1 / (1 + np.exp(-puntaje))
    match = (rng.random(n) < prob).astype(int)

    h = np.floor(hora).astype(int)
    m = ((hora - h) * 60).astype(int)
    df = pd.DataFrame({
        "zona_origen": zona_origen, "zona_destino": zona_destino,
        "distancia_km": distancia.round(1), "desviacion_ruta_min": desviacion.round(1),
        "hora_salida": [f"{a:02d}:{b:02d}" for a, b in zip(h, m)],
        "diferencia_horaria_min": dif_horaria.round(0),
        "dia_semana": dia, "asientos_disponibles": asientos,
        "cooperacion_mxn": coop, "calificacion_conductor": calif,
        "viajes_previos_pasajero": viajes_prev, "match_exitoso": match,
    })
    # Suciedad realista para practicar la limpieza
    df["cooperacion_mxn"] = df["cooperacion_mxn"].astype(float)
    df.loc[rng.choice(n, 40, replace=False), "cooperacion_mxn"] = np.nan
    df.loc[rng.choice(n, 30, replace=False), "calificacion_conductor"] = np.nan
    df.loc[rng.choice(n, 60, replace=False), "zona_origen"] = df["zona_origen"].str.upper()
    df.loc[rng.choice(n, 50, replace=False), "dia_semana"] = df["dia_semana"].str.capitalize() + " "
    duplicados = df.sample(40, random_state=SEMILLA)
    df = pd.concat([df, duplicados], ignore_index=True).sample(frac=1, random_state=SEMILLA)
    df.to_csv(ruta, index=False)
    print(f"[simulacion] {ruta} creado: {df.shape[0]} filas")


def limpiar_texto(df):
    for col in ["zona_origen", "zona_destino", "dia_semana"]:
        df[col] = df[col].str.strip().str.lower()
    df["zona_origen"] = df["zona_origen"].str.title()
    df["zona_destino"] = df["zona_destino"].str.title()
    return df


def hora_a_decimal(texto):
    h, m = texto.split(":")
    return round(int(h) + int(m) / 60, 2)


def main():
    if not os.path.exists("datos_crudos.csv"):
        simular_crudos("datos_crudos.csv")

    df = pd.read_csv("datos_crudos.csv")
    print("\n--- ANTES DE LIMPIAR ---")
    print("Filas y columnas:", df.shape)
    print("Duplicados:", df.duplicated().sum())
    print("Faltantes por columna:")
    print(df.isna().sum()[df.isna().sum() > 0].to_string())

    df = df.drop_duplicates()
    df = limpiar_texto(df)
    df["hora_salida"] = df["hora_salida"].apply(hora_a_decimal)
    # Faltantes: se rellenan con la mediana (no se tiran filas)
    for col in ["cooperacion_mxn", "calificacion_conductor"]:
        df[col] = df[col].fillna(df[col].median())
    df = df.reset_index(drop=True)

    df.to_csv("datos_limpios.csv", index=False)
    print("\n--- DESPUES DE LIMPIAR ---")
    print("Filas y columnas:", df.shape)
    print("Faltantes totales:", int(df.isna().sum().sum()))
    print("\nProporcion de la etiqueta match_exitoso:")
    print(df["match_exitoso"].value_counts(normalize=True).round(3).to_string())
    print("\nPrimeras filas:")
    print(df.head().to_string())
    print("\nGuardado: datos_limpios.csv")


if __name__ == "__main__":
    main()