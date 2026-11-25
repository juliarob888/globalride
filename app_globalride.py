"""
app_globalride.py - GlobalRide: carpool para estudiantes de Global University
Un solo comando:  streamlit run app_globalride.py

1) Pantalla de acceso: correo institucional, matrícula y teléfono.
2) Mapa de Aguascalientes y alrededores: el pasajero marca dónde está y la app le
   sugiere el punto de encuentro; el conductor marca de dónde sale y ve por qué
   puntos puede pasar por pasajeros.
3) Tarifa por kilómetro según el precio de la gasolina.
4) El modelo (modelo_globalride.joblib) estima la probabilidad de match exitoso.
   Los datos de entrenamiento y los conductores de la demo son simulados.
"""
import datetime as dt
import json
import re

import folium
import joblib
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

import ags_datos as ags
import db

st.set_page_config(page_title="GlobalRide", page_icon="🚗", layout="wide",
                   initial_sidebar_state="collapsed")

DOMINIO = "globaluniversity.edu.mx"
DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes"]

# ------------------------------------------------------------------ estilos
st.html("""<style>
@import url("https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=Inter:wght@400;500;600&display=swap");
:root{
  --bg:#07070d; --card:rgba(255,255,255,.045); --borde:rgba(255,255,255,.09);
  --texto:#f4f4fb; --suave:#a3a3c2; --morado:#8b5cf6; --rosa:#ec4899; --lima:#c6f432; --cian:#22d3ee;
}
html, body, [data-testid="stAppViewContainer"]{
  background:
    radial-gradient(900px 500px at 8% -10%, rgba(139,92,246,.28), transparent 60%),
    radial-gradient(800px 500px at 105% 10%, rgba(236,72,153,.20), transparent 60%),
    radial-gradient(700px 400px at 50% 120%, rgba(34,211,238,.12), transparent 60%),
    var(--bg) !important;
  color:var(--texto); font-family:'Inter',system-ui,sans-serif;
}
[data-testid="stHeader"]{background:transparent;}
#MainMenu, footer, [data-testid="stToolbar"]{visibility:hidden;}
.block-container{padding-top:1.6rem; max-width:1250px;}
h1,h2,h3,h4{font-family:'Space Grotesk',sans-serif !important; letter-spacing:-.02em;}
.gr-logo{font-family:'Space Grotesk'; font-weight:700; font-size:1.5rem; display:flex; align-items:center; gap:.5rem;}
.gr-logo span{background:linear-gradient(90deg,var(--morado),var(--rosa)); -webkit-background-clip:text; color:transparent;}
.gr-hero{font-family:'Space Grotesk'; font-weight:700; font-size:clamp(2.3rem,5vw,3.9rem); line-height:1.02; margin:.6rem 0 1rem;}
.gr-hero em{font-style:normal; background:linear-gradient(90deg,var(--lima),var(--cian)); -webkit-background-clip:text; color:transparent;}
.gr-sub{color:var(--suave); font-size:1.08rem; max-width:34rem;}
.gr-chips{display:flex; flex-wrap:wrap; gap:.5rem; margin:1.3rem 0;}
.gr-chip{border:1px solid var(--borde); background:var(--card); padding:.4rem .8rem; border-radius:999px; font-size:.88rem;}
.gr-stats{display:flex; gap:2rem; margin-top:1.4rem; flex-wrap:wrap;}
.gr-stats b{display:block; font-family:'Space Grotesk'; font-size:1.8rem;}
.gr-stats small{color:var(--suave);}
.gr-card{background:var(--card); border:1px solid var(--borde); border-radius:20px; padding:1.1rem 1.25rem;
  backdrop-filter:blur(12px); margin-bottom:.8rem;}
.gr-card h4{margin:0 0 .3rem;}
.gr-muted{color:var(--suave); font-size:.9rem;}
.gr-precio{font-family:'Space Grotesk'; font-weight:700; font-size:3rem; line-height:1;
  background:linear-gradient(90deg,var(--lima),var(--cian)); -webkit-background-clip:text; color:transparent;}
.gr-fila{display:flex; justify-content:space-between; padding:.35rem 0; border-bottom:1px dashed var(--borde); font-size:.93rem;}
.gr-fila:last-child{border-bottom:none;}
.gr-badge{display:inline-block; padding:.18rem .6rem; border-radius:999px; font-size:.78rem; font-weight:600;}
.gr-ok{background:rgba(198,244,50,.15); color:var(--lima); border:1px solid rgba(198,244,50,.35);}
.gr-meh{background:rgba(251,191,36,.12); color:#fbbf24; border:1px solid rgba(251,191,36,.35);}
.gr-pin{background:rgba(139,92,246,.15); color:#c4b5fd; border:1px solid rgba(139,92,246,.4);}
.gr-driver{display:flex; gap:.9rem; align-items:center;}
.gr-avatar{width:46px; height:46px; border-radius:14px; display:grid; place-items:center; font-weight:700;
  background:linear-gradient(135deg,var(--morado),var(--rosa)); font-family:'Space Grotesk'; flex-shrink:0;}
.gr-bar{height:6px; border-radius:6px; background:rgba(255,255,255,.08); overflow:hidden; margin-top:.5rem;}
.gr-bar i{display:block; height:100%; background:linear-gradient(90deg,var(--rosa),var(--lima));}
.gr-paso{display:flex; gap:.6rem; align-items:center; color:var(--suave); font-size:.92rem; margin:.25rem 0;}
.gr-paso b{width:24px; height:24px; border-radius:8px; display:grid; place-items:center; background:var(--card);
  border:1px solid var(--borde); color:var(--texto); font-size:.8rem;}
[data-testid="stForm"]{background:var(--card); border:1px solid var(--borde) !important; border-radius:24px; padding:1.4rem;}
.stTextInput input, .stNumberInput input, [data-baseweb="select"]>div, .stTimeInput input{
  background:rgba(255,255,255,.05) !important; border-radius:12px !important;}
.stButton>button, [data-testid="stFormSubmitButton"]>button{
  border-radius:14px; font-weight:600; border:1px solid var(--borde); transition:transform .12s ease;}
.stButton>button[kind="primary"], [data-testid="stFormSubmitButton"]>button{
  background:linear-gradient(90deg,var(--morado),var(--rosa)) !important; border:none !important; color:white !important;}
.stButton>button:hover{transform:translateY(-1px);}
[data-testid="stMetric"]{background:var(--card); border:1px solid var(--borde); border-radius:16px; padding:.7rem 1rem;}
[data-testid="stMetricValue"]{font-family:'Space Grotesk';}
.stTabs [data-baseweb="tab-list"]{gap:.4rem;}
.stTabs [data-baseweb="tab"]{background:var(--card); border-radius:12px; padding:.4rem 1rem; border:1px solid var(--borde);}
.stTabs [aria-selected="true"]{background:linear-gradient(90deg,rgba(139,92,246,.35),rgba(236,72,153,.35));}
iframe{border-radius:20px;}
</style>""")


@st.cache_resource
def cargar_modelo():
    return joblib.load("modelo_globalride.joblib")


@st.cache_data(show_spinner=False, ttl=3600)
def ruta_cache(origen, destino):
    return ags.ruta(origen, destino)


def a_decimal(t):
    return round(t.hour + t.minute / 60, 2)


def a_hora(h):
    hh = int(h)
    return f"{hh:02d}:{int(round((h - hh) * 60)) % 60:02d}"


def iniciales(nombre):
    return "".join(p[0] for p in nombre.split()[:2]).upper() or "GR"


# ------------------------------------------------------------------ acceso
def validar(correo, matricula, telefono, nombre):
    errores = []
    if not re.fullmatch(rf"[a-z0-9._-]+@{re.escape(DOMINIO)}", correo.strip().lower()):
        errores.append(f"Usa tu correo institucional (termina en @{DOMINIO}).")
    if not re.fullmatch(r"[A-Za-z0-9]{6,12}", matricula.strip()):
        errores.append("La matrícula debe tener de 6 a 12 letras o números, sin espacios.")
    tel = re.sub(r"[\s\-()]", "", telefono)
    tel = tel[3:] if tel.startswith("+52") else tel
    if not re.fullmatch(r"\d{10}", tel):
        errores.append("El teléfono debe tener 10 dígitos.")
    if len(nombre.strip()) < 2:
        errores.append("Escribe tu nombre.")
    return errores, tel


def pantalla_acceso():
    izq, der = st.columns([1.15, 1], gap="large")
    with izq:
        st.markdown("""
        <div class="gr-logo">🚗 <span>GlobalRide</span></div>
        <div class="gr-hero">Llega a la uni<br>sin gastar <em>de más.</em></div>
        <p class="gr-sub">Comparte ride con gente de tu universidad. Tú marcas dónde estás,
        nosotros te decimos dónde te recogen y cuánto te toca poner de gas. Sin sorpresas.</p>
        <div class="gr-chips">
          <span class="gr-chip">🎓 Solo comunidad Global University</span>
          <span class="gr-chip">📍 Toda Ags + Jesús María + SFR</span>
          <span class="gr-chip">⛽ Tarifa justa por km</span>
          <span class="gr-chip">🤖 Match con IA</span>
        </div>
        <div class="gr-stats">
          <div><b>16</b><small>puntos de encuentro</small></div>
          <div><b>1</b><small>campus · Av. Independencia</small></div>
          <div><b>desde $15</b><small>por viaje, según km y gas</small></div>
        </div>
        """, unsafe_allow_html=True)

    with der:
        with st.form("acceso"):
            st.markdown("### Entra a tu cuenta")
            st.caption("Verificamos que seas parte de la comunidad universitaria.")
            correo = st.text_input("Correo institucional", placeholder=f"tu.matricula@{DOMINIO}")
            nombre = st.text_input("¿Cómo te llamas?", placeholder="Nombre y apellido")
            c1, c2 = st.columns(2)
            matricula = c1.text_input("ID / matrícula", placeholder="Ej. GU24AB0000")
            telefono = c2.text_input("Teléfono", placeholder="449 123 4567")
            rol = st.radio("¿Qué vas a hacer hoy?", ["🙋 Busco ride", "🚘 Doy ride"], horizontal=True)
            acepto = st.checkbox("Acepto compartir mi teléfono solo con mis matches confirmados.")
            entrar = st.form_submit_button("Entrar a GlobalRide →", use_container_width=True)

        if entrar:
            errores, tel = validar(correo, matricula, telefono, nombre)
            if not acepto:
                errores.append("Debes aceptar el uso de tu teléfono para coordinar viajes.")
            if errores:
                for e in errores:
                    st.error(e)
            else:
                usuario = {
                    "correo": correo.strip().lower(), "nombre": nombre.strip().title(),
                    "matricula": matricula.strip().upper(), "telefono": tel,
                    "rol": "pasajero" if "Busco" in rol else "conductor",
                }
                try:
                    db.registrar_usuario(usuario)
                except Exception as e:
                    st.error(f"No pudimos guardar tu registro, intenta de nuevo. ({e.__class__.__name__})")
                    return
                st.session_state.usuario = usuario
                st.rerun()


# ------------------------------------------------------------------ mapa
def mapa_base(alto_zoom=12):
    m = folium.Map(location=ags.CENTRO_AGS, zoom_start=alto_zoom, tiles=None, control_scale=True)
    for nombre, capa in [("Google Maps", "m"), ("Google Satélite", "s"), ("Google Híbrido", "y")]:
        folium.TileLayer(tiles=f"https://mt1.google.com/vt/lyrs={capa}&x={{x}}&y={{y}}&z={{z}}&hl=es",
                         attr="Map data © Google", name=nombre, max_zoom=20).add_to(m)
    folium.LayerControl(position="topright").add_to(m)
    for nombre, c in ags.CAMPUS.items():
        folium.Marker(c["coord"], tooltip=f"🎓 {nombre} · {c['direccion']}",
                      icon=folium.DivIcon(html=_pin("🎓", "#8b5cf6", 38), icon_size=(38, 38),
                                          icon_anchor=(19, 19))).add_to(m)
    for p in ags.PUNTOS:
        folium.Marker(p["coord"], tooltip=f"📍 {p['nombre']} · {p['zona']}",
                      icon=folium.DivIcon(html=_pin("", "#22d3ee", 14), icon_size=(14, 14),
                                          icon_anchor=(7, 7))).add_to(m)
    return m


def _pin(emoji, color, tam):
    return (f'<div style="width:{tam}px;height:{tam}px;border-radius:50%;background:{color};'
            f'display:grid;place-items:center;font-size:{tam * .5}px;'
            f'box-shadow:0 0 0 4px {color}44,0 0 18px {color};border:2px solid #fff;">{emoji}</div>')


def link_google_maps(origen, destino, paradas=()):
    """Liga para abrir la ruta en Google Maps (app o web), con paradas opcionales."""
    url = ("https://www.google.com/maps/dir/?api=1&travelmode=driving"
           f"&origin={origen[0]},{origen[1]}&destination={destino[0]},{destino[1]}")
    if paradas:
        url += "&waypoints=" + "%7C".join(f"{p[0]},{p[1]}" for p in list(paradas)[:9])
    return url


def dibujar_mapa(m, clave):
    salida = st_folium(m, key=clave, height=520, use_container_width=True,
                       returned_objects=["last_clicked"])
    clic = (salida or {}).get("last_clicked")
    if clic:
        punto = (round(clic["lat"], 5), round(clic["lng"], 5))
        if st.session_state.get(f"{clave}_punto") != punto:
            st.session_state[f"{clave}_punto"] = punto
            st.rerun()


# ------------------------------------------------------------------ panel común
def ajustes_viaje(prefijo):
    campus = ags.CAMPUS_NOMBRE
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"""<div class="gr-card" style="padding:.6rem 1rem;margin:0">
      <div class="gr-muted">🎓 Destino</div><b>{campus}</b>
      <div class="gr-muted" style="font-size:.78rem">{ags.CAMPUS[campus]['direccion']}</div></div>""",
                unsafe_allow_html=True)
    hoy = dt.date.today().weekday()
    dia = c2.selectbox("Día", DIAS, index=hoy if hoy < 5 else 0, key=f"{prefijo}_dia")
    hora = c3.time_input("Hora de salida", dt.time(7, 30), step=900, key=f"{prefijo}_hora")
    return campus, dia, hora


def bloque_tarifa(km, minutos, real, t, precio, tipo_gas, titulo="Tu cooperación"):
    origen_ruta = "ruta por calles" if real else "estimación (sin conexión a rutas)"
    st.markdown(f"""
    <div class="gr-card">
      <div class="gr-muted">{titulo}</div>
      <div class="gr-precio">${t['por_pasajero']}</div>
      <div class="gr-muted" style="margin:.3rem 0 .8rem;">MXN · {km:.1f} km · ~{minutos:.0f} min · {origen_ruta}</div>
      <div class="gr-fila"><span>⛽ {tipo_gas}</span><b>${precio:.2f}/L</b></div>
      <div class="gr-fila"><span>Gasolina del viaje ({t['litros']:.2f} L)</span><b>${t['gasolina']:.2f}</b></div>
      <div class="gr-fila"><span>Desgaste del auto ($0.90/km)</span><b>${t['desgaste']:.2f}</b></div>
      <div class="gr-fila"><span>Se divide entre</span><b>{t['ocupantes']} personas</b></div>
      <div class="gr-fila"><span>Servicio</span><b>$5.00</b></div>
      <div class="gr-fila"><span>Equivale a</span><b>${t['por_km']:.2f} por km</b></div>
    </div>
    """, unsafe_allow_html=True)


def prob_match(zona_origen, zona_destino, km, desvio, hora, dif, dia, asientos, coop, calif, previos):
    fila = pd.DataFrame([{
        "zona_origen": zona_origen, "zona_destino": zona_destino, "distancia_km": km,
        "desviacion_ruta_min": desvio, "hora_salida": hora, "diferencia_horaria_min": dif,
        "dia_semana": dia, "asientos_disponibles": asientos, "cooperacion_mxn": coop,
        "calificacion_conductor": calif, "viajes_previos_pasajero": previos}])
    return float(cargar_modelo().predict_proba(fila)[0][1])


# ------------------------------------------------------------------ pasajero
def vista_pasajero(precio, tipo_gas):
    campus, dia, hora = ajustes_viaje("p")
    destino = ags.CAMPUS[campus]["coord"]
    yo = st.session_state.get("mapa_p_punto")

    col_mapa, col_info = st.columns([1.6, 1], gap="large")
    with col_info:
        if not yo:
            st.markdown("""
            <div class="gr-card"><h4>¿Dónde estás?</h4>
              <div class="gr-paso"><b>1</b> Toca el mapa donde estás (tu casa, tu depa…)</div>
              <div class="gr-paso"><b>2</b> Te mostramos el punto seguro más cercano para que te recojan</div>
              <div class="gr-paso"><b>3</b> Ves cuánto te toca de gas y eliges conductor</div>
            </div>""", unsafe_allow_html=True)
        else:
            cercanos = ags.puntos_cercanos(yo, 3)
            opciones = ["📍 Que pasen por mí aquí"] + [f"{p['nombre']} · {p['dist'] * 1000:.0f} m a pie"
                                                      for p in cercanos]
            sel = st.radio("¿Dónde te recogen?", opciones, index=1 if cercanos[0]["dist"] < 1.2 else 0)
            recogida = yo if sel == opciones[0] else cercanos[opciones.index(sel) - 1]["coord"]
            nombre_recogida = "Tu ubicación" if sel == opciones[0] else cercanos[opciones.index(sel) - 1]["nombre"]

            linea, km, minutos, real = ruta_cache(recogida, destino)
            t = ags.tarifa(km, precio, 14, pasajeros=1)
            bloque_tarifa(km, minutos, real, t, precio, tipo_gas)
            st.link_button("🗺️ Abrir ruta en Google Maps", link_google_maps(recogida, destino),
                           use_container_width=True)

    with col_mapa:
        m = mapa_base()
        if yo:
            folium.Marker(yo, tooltip="Tú estás aquí",
                          icon=folium.DivIcon(html=_pin("🙋", "#ec4899", 34), icon_size=(34, 34),
                                              icon_anchor=(17, 17))).add_to(m)
            folium.PolyLine(linea, color="#c6f432", weight=5, opacity=.9).add_to(m)
            if recogida != yo:
                folium.PolyLine([yo, recogida], color="#ec4899", weight=3, dash_array="6 8").add_to(m)
                folium.Marker(recogida, tooltip=f"Te recogen en: {nombre_recogida}",
                              icon=folium.DivIcon(html=_pin("🚏", "#c6f432", 32), icon_size=(32, 32),
                                                  icon_anchor=(16, 16))).add_to(m)
            m.fit_bounds([yo, destino], padding=(40, 40))
        dibujar_mapa(m, "mapa_p")
        st.caption("🟣 Campus · 🔵 Puntos de encuentro · Toca el mapa para cambiar tu ubicación.")

    if not yo:
        return

    st.markdown(f"### Conductores que van a {campus} 🚘")
    hora_dec = a_decimal(hora)
    zona_o = ags.zona_de(recogida)
    correo = st.session_state.usuario["correo"]
    previos = db.contar_viajes(correo)
    lista = []
    for c in ags.conductores_cerca(recogida, hora_dec):
        tc = ags.tarifa(km, precio, c["rendimiento"], pasajeros=1)
        p = prob_match(zona_o, ags.CAMPUS[campus]["zona_destino"], km, c["desvio_min"], c["hora"],
                       abs(c["hora"] - hora_dec) * 60, dia, c["asientos"], tc["por_pasajero"],
                       c["calificacion"], previos)
        lista.append((p, c, tc))
    lista.sort(key=lambda x: -x[0])

    cols = st.columns(2)
    for i, (p, c, tc) in enumerate(lista):
        with cols[i % 2]:
            badge = ('<span class="gr-badge gr-ok">🔥 Match recomendado</span>' if p >= .5
                     else '<span class="gr-badge gr-meh">Match poco probable</span>')
            st.markdown(f"""
            <div class="gr-card">
              <div class="gr-driver">
                <div class="gr-avatar">{c['nombre'][:2].upper()}</div>
                <div style="flex:1">
                  <b>{c['nombre']}</b> · <span class="gr-muted">{c['carrera']}</span><br>
                  <span class="gr-muted">⭐ {c['calificacion']} · {c['auto']} · {c['asientos']} lugar(es) · sale {a_hora(c['hora'])}</span>
                </div>
                <div style="text-align:right"><b style="font-size:1.4rem">${tc['por_pasajero']}</b></div>
              </div>
              <div style="margin-top:.7rem;display:flex;justify-content:space-between;align-items:center">
                {badge}<span class="gr-muted">IA: {p * 100:.0f}% de match</span>
              </div>
              <div class="gr-bar"><i style="width:{p * 100:.0f}%"></i></div>
            </div>""", unsafe_allow_html=True)
            if st.button(f"Pedir ride con {c['nombre']}", key=f"pedir_{i}", use_container_width=True,
                         type="primary" if i == 0 else "secondary"):
                db.guardar_viaje(
                    correo=correo, rol="pasajero", dia=dia, hora=a_hora(hora_dec),
                    ubicacion_lat=yo[0], ubicacion_lon=yo[1],
                    recogida_nombre=nombre_recogida, recogida_lat=recogida[0], recogida_lon=recogida[1],
                    destino=campus, km=round(km, 2), cooperacion=tc["por_pasajero"],
                    detalle=f"Con {c['nombre']} ({c['auto']}), sale {a_hora(c['hora'])}")
                st.toast(f"¡Listo! {c['nombre']} te recoge en {nombre_recogida} a las {a_hora(c['hora'])} 🚗")
                st.balloons()


# ------------------------------------------------------------------ conductor
def vista_conductor(precio, tipo_gas):
    campus, dia, hora = ajustes_viaje("c")
    destino = ags.CAMPUS[campus]["coord"]
    c1, c2, c3 = st.columns(3)
    asientos = c1.slider("Lugares libres", 1, 4, 3)
    rendimiento = c2.slider("Rendimiento de tu auto (km/L)", 8, 22, 14)
    radio = c3.slider("Desvío máximo para recoger (km)", 0.3, 3.0, 1.0, 0.1)
    salida = st.session_state.get("mapa_c_punto")

    col_mapa, col_info = st.columns([1.6, 1], gap="large")
    paradas = []
    if salida:
        linea, km, minutos, real = ruta_cache(salida, destino)
        for p in ags.PUNTOS:
            d = ags.distancia_a_ruta(p["coord"], linea)
            if d <= radio:
                paradas.append(dict(p, desvio=d, esperando=ags.pasajeros_esperando(p["nombre"])))
        # ordenar en el sentido del viaje: lo más lejos del campus primero
        paradas.sort(key=lambda p: -ags.distancia_km(p["coord"], destino))
        reales = []
        for _, r in db.pasajeros_esperando(dia).iterrows():
            punto = (r["recogida_lat"], r["recogida_lon"])
            d = ags.distancia_a_ruta(punto, linea)
            if d <= radio:
                reales.append({"nombre": r["nombre"], "lugar": r["recogida_nombre"], "coord": punto,
                               "hora": r["hora"], "desvio": d})
        interesados = sum(len(p["esperando"]) for p in paradas) + len(reales)
        llevar = min(asientos, interesados)
        t = ags.tarifa(km, precio, rendimiento, pasajeros=max(1, llevar))

    with col_info:
        if not salida:
            st.markdown("""
            <div class="gr-card"><h4>¿De dónde sales?</h4>
              <div class="gr-paso"><b>1</b> Toca el mapa en tu punto de salida</div>
              <div class="gr-paso"><b>2</b> Trazamos tu ruta al campus</div>
              <div class="gr-paso"><b>3</b> Te marcamos dónde puedes pasar por gente y cuánto recuperas de gas</div>
            </div>""", unsafe_allow_html=True)
        else:
            bloque_tarifa(km, minutos, real, t, precio, tipo_gas, titulo="Cada pasajero te coopera")
            m1, m2 = st.columns(2)
            m1.metric("Recuperas", f"${t['por_pasajero'] * llevar}", f"{llevar} pasajero(s)")
            m2.metric("Gas del viaje", f"${t['gasolina']:.0f}")
            con_gente = [r["coord"] for r in reales] + [p["coord"] for p in paradas if p["esperando"]]
            st.link_button("🗺️ Navegar con Google Maps (con paradas)",
                           link_google_maps(salida, destino, con_gente), use_container_width=True)

    with col_mapa:
        m = mapa_base()
        if salida:
            folium.PolyLine(linea, color="#c6f432", weight=5, opacity=.9).add_to(m)
            folium.Circle(salida, radius=radio * 1000, color="#ec4899", fill=False, weight=1,
                          dash_array="4 6").add_to(m)
            folium.Marker(salida, tooltip="Sales de aquí",
                          icon=folium.DivIcon(html=_pin("🚘", "#ec4899", 34), icon_size=(34, 34),
                                              icon_anchor=(17, 17))).add_to(m)
            for p in paradas:
                folium.Marker(p["coord"], tooltip=f"🚏 {p['nombre']} · {len(p['esperando'])} esperando",
                              icon=folium.DivIcon(html=_pin(str(len(p["esperando"])), "#c6f432", 26),
                                                  icon_size=(26, 26), icon_anchor=(13, 13))).add_to(m)
            for r in reales:
                folium.Marker(r["coord"], tooltip=f"🙋 {r['nombre']} · {r['lugar']} · {r['hora']}",
                              icon=folium.DivIcon(html=_pin("🙋", "#ec4899", 28), icon_size=(28, 28),
                                                  icon_anchor=(14, 14))).add_to(m)
            m.fit_bounds([salida, destino], padding=(40, 40))
        dibujar_mapa(m, "mapa_c")
        st.caption("🟢 Paradas sobre tu ruta (el número = estudiantes esperando) · Toca el mapa para cambiar tu salida.")

    if not salida:
        return
    if reales:
        st.markdown("### Estudiantes que pidieron ride sobre tu ruta 🙋")
        cols = st.columns(3)
        for i, r in enumerate(reales):
            with cols[i % 3]:
                st.markdown(f"""
                <div class="gr-card">
                  <span class="gr-badge gr-ok">Solicitud real · {dia} {r['hora']}</span>
                  <h4 style="margin-top:.5rem">{r['nombre']}</h4>
                  <div class="gr-muted">📍 {r['lugar']} · a {r['desvio'] * 1000:.0f} m de tu ruta</div>
                </div>""", unsafe_allow_html=True)
    st.markdown("### Dónde puedes pasar por ellos 🚏")
    if not paradas:
        st.info("No hay puntos de encuentro sobre tu ruta. Sube el desvío máximo para ver más opciones.")
        return
    cols = st.columns(3)
    for i, p in enumerate(paradas):
        gente = ", ".join(f"{e['nombre']} ({e['carrera']})" for e in p["esperando"]) or "Nadie por ahora"
        with cols[i % 3]:
            st.markdown(f"""
            <div class="gr-card">
              <span class="gr-badge gr-pin">Parada {i + 1} · {p['zona']}</span>
              <h4 style="margin-top:.5rem">{p['nombre']}</h4>
              <div class="gr-muted">A {p['desvio'] * 1000:.0f} m de tu ruta</div>
              <div style="margin-top:.5rem">👥 {gente}</div>
            </div>""", unsafe_allow_html=True)
    if st.button("Publicar mi ride 🚀", type="primary", use_container_width=True):
        puntos = ([{"nombre": p["nombre"], "lat": p["coord"][0], "lon": p["coord"][1]} for p in paradas]
                  + [{"nombre": f"{r['nombre']} · {r['lugar']}", "lat": r["coord"][0], "lon": r["coord"][1]}
                     for r in reales])
        db.guardar_viaje(
            correo=st.session_state.usuario["correo"], rol="conductor", dia=dia,
            hora=hora.strftime("%H:%M"), ubicacion_lat=salida[0], ubicacion_lon=salida[1],
            paradas=puntos, destino=campus, km=round(km, 2), cooperacion=t["por_pasajero"],
            detalle=f"{asientos} lugar(es), rendimiento {rendimiento} km/L")
        st.toast("¡Ride publicado! Te avisamos cuando alguien se una 🙌")
        st.balloons()


# ------------------------------------------------------------------ app
def app():
    u = st.session_state.usuario

    with st.sidebar:
        st.markdown("### ⛽ Precio de la gasolina")
        tipo_gas = st.radio("Tipo", list(ags.PRECIO_GAS_REF), label_visibility="collapsed")
        precio = st.number_input("Precio por litro (MXN)", 15.0, 40.0, ags.PRECIO_GAS_REF[tipo_gas], 0.01,
                                 help="Valor de referencia para Aguascalientes. Actualízalo con el precio de hoy.")
        st.caption("Referencia Ags: Magna $23.79 · Premium $25.94 (ene 2026). Cámbialo si subió o bajó.")
        st.divider()
        if st.button("Cerrar sesión", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    h1, h2 = st.columns([3, 1.3])
    with h1:
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:1rem">
          <div class="gr-logo">🚗 <span>GlobalRide</span></div>
          <span class="gr-badge gr-pin">⛽ {tipo_gas.split()[0]} ${precio:.2f}/L</span>
        </div>""", unsafe_allow_html=True)
    with h2:
        st.markdown(f"""
        <div class="gr-driver" style="justify-content:flex-end">
          <div style="text-align:right"><b>Hola, {u['nombre'].split()[0]} 👋</b><br>
          <span class="gr-muted">{u['matricula']} · {u['telefono'][:3]} {u['telefono'][3:6]} {u['telefono'][6:]}</span></div>
          <div class="gr-avatar">{iniciales(u['nombre'])}</div>
        </div>""", unsafe_allow_html=True)
    st.write("")

    nombres = ["🙋 Busco ride", "🚘 Doy ride", "🧾 Mis viajes"]
    admin = es_admin(u["correo"])
    if admin:
        nombres.append("🛠️ Base de datos")
    pestanas = st.tabs(nombres, default=nombres[1] if u["rol"] == "conductor" else nombres[0])
    t_pas, t_con, t_mis = pestanas[:3]
    with t_pas:
        vista_pasajero(precio, tipo_gas)
    with t_con:
        vista_conductor(precio, tipo_gas)
    with t_mis:
        mis = db.viajes_de(u["correo"])
        if len(mis):
            vista = mis.rename(columns={"creado": "Registrado", "rol": "Rol", "dia": "Día", "hora": "Hora",
                                        "recogida_nombre": "Recogida", "destino": "Destino", "km": "Km",
                                        "cooperacion": "Cooperación $", "detalle": "Detalle"})
            st.dataframe(vista[["Registrado", "Rol", "Día", "Hora", "Recogida", "Km", "Cooperación $", "Detalle"]],
                         use_container_width=True, hide_index=True)
        else:
            st.info("Aún no tienes viajes. ¡Pide o publica tu primer ride!")
        st.markdown(f"""
        <div class="gr-card"><h4>Tu perfil</h4>
          <div class="gr-fila"><span>Correo</span><b>{u['correo']}</b></div>
          <div class="gr-fila"><span>Matrícula</span><b>{u['matricula']}</b></div>
          <div class="gr-fila"><span>Teléfono</span><b>{u['telefono']}</b></div>
        </div>""", unsafe_allow_html=True)

    if admin:
        with pestanas[3]:
            panel_admin()

    st.caption("Modelo de match: regresión logística (F1 ≈ 0.80), entrenado con 1,000 viajes simulados. "
               "Los conductores con calificación y auto son de demostración; las solicitudes marcadas "
               "como «real» vienen de la base de datos. Rutas: OpenStreetMap / OSRM.")


# ------------------------------------------------------------------ admin
def es_admin(correo):
    """Correos con acceso al panel, definidos en los Secrets: ADMIN_EMAILS = ["a@...", "b@..."]."""
    try:
        return correo in [c.strip().lower() for c in st.secrets["ADMIN_EMAILS"]]
    except Exception:
        return False


def panel_admin():
    if not db.es_permanente():
        st.warning("La base de datos es un archivo local (SQLite). En Streamlit Cloud se borra cuando la app "
                   "se reinicia. Para que sea permanente, agrega DATABASE_URL en los Secrets.")
    us, vj = db.tabla("usuarios"), db.tabla("viajes")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Usuarios registrados", len(us))
    m2.metric("Viajes registrados", len(vj))
    m3.metric("Pasajeros", int((vj["rol"] == "pasajero").sum()) if len(vj) else 0)
    m4.metric("Conductores", int((vj["rol"] == "conductor").sum()) if len(vj) else 0)

    if len(vj):
        st.markdown("#### Mapa de ubicaciones registradas")
        m = mapa_base(alto_zoom=11)
        for _, r in vj.iterrows():
            if r["rol"] == "pasajero" and pd.notna(r["recogida_lat"]):
                folium.CircleMarker((r["recogida_lat"], r["recogida_lon"]), radius=7, color="#ec4899",
                                    fill=True, tooltip=f"🙋 Recogida: {r['recogida_nombre']} · {r['correo']}").add_to(m)
            elif r["rol"] == "conductor" and pd.notna(r["ubicacion_lat"]):
                folium.CircleMarker((r["ubicacion_lat"], r["ubicacion_lon"]), radius=7, color="#c6f432",
                                    fill=True, tooltip=f"🚘 Salida conductor · {r['correo']}").add_to(m)
                for pt in json.loads(r["paradas"] or "[]"):
                    folium.CircleMarker((pt["lat"], pt["lon"]), radius=4, color="#22d3ee", fill=True,
                                        tooltip=f"🚏 Puede recoger en: {pt['nombre']}").add_to(m)
        st_folium(m, key="mapa_admin", height=450, use_container_width=True, returned_objects=[])
        st.caption("🩷 Dónde recogen a pasajeros · 💚 De dónde salen conductores · 🩵 Dónde pueden recoger")

    st.markdown("#### Usuarios")
    st.dataframe(us, use_container_width=True, hide_index=True)
    st.download_button("Descargar usuarios (CSV)", us.to_csv(index=False).encode("utf-8"),
                       "usuarios_globalride.csv", "text/csv")
    st.markdown("#### Viajes y ubicaciones")
    st.dataframe(vj, use_container_width=True, hide_index=True)
    st.download_button("Descargar viajes (CSV)", vj.to_csv(index=False).encode("utf-8"),
                       "viajes_globalride.csv", "text/csv")


if "usuario" not in st.session_state:
    pantalla_acceso()
else:
    app()
