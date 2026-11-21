"""
app_globalride.py - Prototipo de GlobalRide
Un solo comando:  streamlit run app_globalride.py
Carga el modelo elegido (modelo_globalride.joblib) y estima la probabilidad
de que un viaje propuesto entre conductor y pasajero sea un match exitoso.
Los datos de entrenamiento son simulados (ver README_datos.md).
"""
import joblib
import pandas as pd
import streamlit as st

st.set_page_config(page_title="GlobalRide", page_icon="🚗")

@st.cache_resource
def cargar_modelo():
    return joblib.load("modelo_globalride.joblib")

modelo = cargar_modelo()

st.title("🚗 GlobalRide")
st.caption("Carpool para estudiantes de Global University · Prototipo de matching con aprendizaje automático")
st.write("Captura los datos del viaje y el modelo estima si el match entre conductor y pasajero sería exitoso "
         "(viaje concretado y ambos califican con 4 o 5 estrellas).")

col1, col2 = st.columns(2)
with col1:
    st.subheader("Ruta y horario")
    zona_origen = st.selectbox("Zona de origen del pasajero",
                               ["Centro", "Jesus Maria", "Norte", "Oriente", "Poniente", "Sur"])
    zona_destino = st.selectbox("Zona de destino", ["Centro", "Norte"])
    dia_semana = st.selectbox("Día de la semana", ["lunes", "martes", "miercoles", "jueves", "viernes"])
    distancia_km = st.slider("Distancia del viaje (km)", 1.0, 22.0, 9.0, 0.5)
    desviacion_ruta_min = st.slider("Desvío de ruta del conductor (min)", 0.0, 30.0, 3.0, 0.5)
    hora_salida = st.slider("Hora de salida (24 h, ej. 8.5 = 8:30)", 5.0, 19.0, 8.0, 0.25)
    diferencia_horaria_min = st.slider("Diferencia entre horarios de ambos (min)", 0, 80, 10)
with col2:
    st.subheader("Condiciones del viaje")
    asientos_disponibles = st.slider("Asientos disponibles", 1, 4, 2)
    cooperacion_mxn = st.slider("Cooperación para gasolina (MXN)", 5, 70, 30)
    calificacion_conductor = st.slider("Calificación promedio del conductor", 3.0, 5.0, 4.5, 0.1)
    viajes_previos_pasajero = st.slider("Viajes previos del pasajero", 0, 10, 3)

if st.button("Calcular match", type="primary"):
    fila = pd.DataFrame([{
        "zona_origen": zona_origen, "zona_destino": zona_destino, "distancia_km": distancia_km,
        "desviacion_ruta_min": desviacion_ruta_min, "hora_salida": hora_salida,
        "diferencia_horaria_min": diferencia_horaria_min, "dia_semana": dia_semana,
        "asientos_disponibles": asientos_disponibles, "cooperacion_mxn": cooperacion_mxn,
        "calificacion_conductor": calificacion_conductor,
        "viajes_previos_pasajero": viajes_previos_pasajero}])
    prob = float(modelo.predict_proba(fila)[0][1])
    st.metric("Probabilidad de match exitoso", f"{prob * 100:.1f} %")
    st.progress(prob)
    if prob >= 0.5:
        st.success("✅ Match recomendado: este viaje tiene buenas probabilidades de concretarse.")
    else:
        st.warning("⚠️ Match poco probable: conviene sugerir otro conductor o ajustar horario o ruta.")

st.divider()
st.caption("Modelo: regresión logística (F1 ≈ 0.80 en prueba). Entrenado con 1,000 viajes simulados a partir de "
           "una encuesta; no usa datos personales reales.")
