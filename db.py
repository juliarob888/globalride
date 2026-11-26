"""
db.py - Base de datos de GlobalRide

Guarda:
  - usuarios: cuentas (correo, nombre, matrícula, teléfono, rol, clave cifrada) y en qué
              teléfono está abierta cada una (solo se permite uno a la vez).
  - dispositivos: qué cuenta usó por última vez cada teléfono, para no volver a pedir todo.
  - viajes:   cada ride pedido o publicado, con las ubicaciones:
              * pasajero  -> dónde está y dónde lo recogen
              * conductor -> de dónde sale, su ruta y los puntos donde puede recoger
  - matches:  pasajero + conductor que se emparejaron (pendiente / aceptado / rechazado)
  - mensajes: el chat de cada match

Por defecto usa un archivo SQLite (globalride.db). Para que los datos NO se borren
en Streamlit Cloud, agrega en los "Secrets" de la app una base en internet, p. ej.:
    DATABASE_URL = "postgresql://usuario:contraseña@host:5432/postgres"
"""
import datetime as dt
import hashlib
import hmac
import json
import secrets

import pandas as pd
import streamlit as st
from sqlalchemy import (Column, DateTime, Float, Integer, MetaData, String, Table, Text,
                        create_engine, func, inspect, or_, select, text, update)

meta = MetaData()

usuarios = Table(
    "usuarios", meta,
    Column("correo", String(120), primary_key=True),
    Column("nombre", String(120)),
    Column("matricula", String(20)),
    Column("telefono", String(15)),
    Column("rol", String(15)),
    Column("primer_acceso", DateTime),
    Column("ultimo_acceso", DateTime),
    Column("accesos", Integer, default=1),
    Column("clave_hash", String(128)),        # la clave NUNCA se guarda tal cual, solo su hash
    Column("clave_sal", String(64)),
    Column("dispositivo_activo", String(64)), # el único teléfono donde la cuenta está abierta
    Column("sesion_desde", DateTime),
)

dispositivos = Table(
    "dispositivos", meta,
    Column("id", String(64), primary_key=True),   # identificador guardado en el navegador del teléfono
    Column("correo", String(120)),
    Column("ultimo_uso", DateTime),
)

viajes = Table(
    "viajes", meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("correo", String(120), index=True),
    Column("rol", String(15)),                 # pasajero | conductor
    Column("creado", DateTime),
    Column("dia", String(12)),
    Column("hora", String(5)),
    Column("ubicacion_lat", Float),            # pasajero: dónde está · conductor: de dónde sale
    Column("ubicacion_lon", Float),
    Column("recogida_nombre", String(120)),    # pasajero: dónde lo recogen
    Column("recogida_lat", Float),
    Column("recogida_lon", Float),
    Column("paradas", Text),                   # conductor: JSON con los puntos donde puede recoger
    Column("destino", String(120)),
    Column("km", Float),
    Column("cooperacion", Float),
    Column("detalle", String(200)),            # con quién va / cuántos lugares
    Column("ruta", Text),                      # conductor: JSON con la ruta [[lat, lon], ...]
    Column("asientos", Integer),               # conductor: lugares libres
)

matches = Table(
    "matches", meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("pasajero", String(120), index=True),
    Column("conductor", String(120), index=True),
    Column("iniciado_por", String(15)),        # pasajero | conductor
    Column("recogida_nombre", String(120)),
    Column("recogida_lat", Float),
    Column("recogida_lon", Float),
    Column("dia", String(12)),
    Column("hora", String(5)),
    Column("cooperacion", Float),
    Column("prob", Float),                     # probabilidad de match que calculó la IA
    Column("estado", String(12), default="pendiente"),
    Column("creado", DateTime),
)

mensajes = Table(
    "mensajes", meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("match_id", Integer, index=True),
    Column("de", String(120)),
    Column("texto", Text),
    Column("creado", DateTime),
)


def _url():
    try:
        return st.secrets["DATABASE_URL"]
    except Exception:
        return "sqlite:///globalride.db"


@st.cache_resource
def motor():
    url = _url()
    if url.startswith("postgres://"):  # Supabase/Heroku a veces la dan así
        url = url.replace("postgres://", "postgresql://", 1)
    eng = create_engine(url, pool_pre_ping=True)
    meta.create_all(eng)
    # Si las tablas ya existían de una versión anterior, les agregamos las columnas nuevas
    nuevas = {"viajes": [("ruta", "TEXT"), ("asientos", "INTEGER")],
              "usuarios": [("clave_hash", "VARCHAR(128)"), ("clave_sal", "VARCHAR(64)"),
                           ("dispositivo_activo", "VARCHAR(64)"), ("sesion_desde", "TIMESTAMP")]}
    for tabla_n, cols in nuevas.items():
        existentes = {c["name"] for c in inspect(eng).get_columns(tabla_n)}
        with eng.begin() as c:
            for col, tipo in cols:
                if col not in existentes:
                    c.execute(text(f"ALTER TABLE {tabla_n} ADD COLUMN {col} {tipo}"))
    return eng


def es_permanente():
    return not _url().startswith("sqlite")


def ahora():
    return dt.datetime.now().replace(microsecond=0)


def registrar_usuario(u):
    """Guarda al usuario la primera vez y actualiza sus datos en cada acceso."""
    with motor().begin() as c:
        r = c.execute(update(usuarios).where(usuarios.c.correo == u["correo"]).values(
            nombre=u["nombre"], matricula=u["matricula"], telefono=u["telefono"], rol=u["rol"],
            ultimo_acceso=ahora(), accesos=usuarios.c.accesos + 1))
        if r.rowcount == 0:
            c.execute(usuarios.insert().values(
                correo=u["correo"], nombre=u["nombre"], matricula=u["matricula"],
                telefono=u["telefono"], rol=u["rol"], primer_acceso=ahora(),
                ultimo_acceso=ahora(), accesos=1))


# ------------------------------------------------------------------ cuentas y teléfonos
def _hash(clave, sal):
    return hashlib.pbkdf2_hmac("sha256", clave.encode(), bytes.fromhex(sal), 200_000).hex()


def usuario(correo):
    with motor().connect() as c:
        r = c.execute(select(usuarios).where(usuarios.c.correo == correo)).mappings().first()
    return dict(r) if r else None


def crear_cuenta(u, clave):
    """Crea la cuenta. Regresa False si ese correo ya tiene cuenta con clave."""
    actual = usuario(u["correo"])
    if actual and actual.get("clave_hash"):
        return False
    sal = secrets.token_hex(16)
    datos = dict(nombre=u["nombre"], matricula=u["matricula"], telefono=u["telefono"], rol=u["rol"],
                 clave_sal=sal, clave_hash=_hash(clave, sal), ultimo_acceso=ahora())
    with motor().begin() as c:
        if actual:  # usuario de la versión anterior (sin clave): le ponemos clave
            c.execute(update(usuarios).where(usuarios.c.correo == u["correo"]).values(**datos))
        else:
            c.execute(usuarios.insert().values(correo=u["correo"], primer_acceso=ahora(), accesos=0, **datos))
    return True


def verificar_clave(correo, clave):
    u = usuario(correo)
    if not u or not u.get("clave_hash"):
        return None
    return u if hmac.compare_digest(_hash(clave, u["clave_sal"]), u["clave_hash"]) else None


def correo_de_dispositivo(disp):
    with motor().connect() as c:
        return c.execute(select(dispositivos.c.correo).where(dispositivos.c.id == disp)).scalar()


def dispositivo_activo(correo):
    with motor().connect() as c:
        return c.execute(select(usuarios.c.dispositivo_activo).where(usuarios.c.correo == correo)).scalar()


def activar_dispositivo(correo, disp, rol=None):
    """Abre la cuenta en este teléfono (y la cierra en cualquier otro)."""
    valores = dict(dispositivo_activo=disp, sesion_desde=ahora(), ultimo_acceso=ahora(),
                   accesos=usuarios.c.accesos + 1)
    if rol:
        valores["rol"] = rol
    with motor().begin() as c:
        c.execute(update(usuarios).where(usuarios.c.correo == correo).values(**valores))
        r = c.execute(update(dispositivos).where(dispositivos.c.id == disp)
                      .values(correo=correo, ultimo_uso=ahora()))
        if r.rowcount == 0:
            c.execute(dispositivos.insert().values(id=disp, correo=correo, ultimo_uso=ahora()))


def liberar_dispositivo(correo, disp):
    """Cierra la sesión en este teléfono (queda libre para abrirla en otro)."""
    with motor().begin() as c:
        c.execute(update(usuarios).where(usuarios.c.correo == correo,
                                         usuarios.c.dispositivo_activo == disp)
                  .values(dispositivo_activo=None))


def olvidar_dispositivo(disp):
    with motor().begin() as c:
        c.execute(dispositivos.delete().where(dispositivos.c.id == disp))


def guardar_viaje(**datos):
    if "paradas" in datos and not isinstance(datos["paradas"], str):
        datos["paradas"] = json.dumps(datos["paradas"], ensure_ascii=False)
    with motor().begin() as c:
        c.execute(viajes.insert().values(creado=ahora(), **datos))


def viajes_de(correo):
    q = select(viajes).where(viajes.c.correo == correo).order_by(viajes.c.creado.desc())
    return pd.read_sql(q, motor())


def contar_viajes(correo):
    with motor().connect() as c:
        return c.execute(select(func.count()).select_from(viajes)
                         .where(viajes.c.correo == correo)).scalar() or 0


def pasajeros_esperando(dia, dias_atras=7):
    """Pasajeros reales que pidieron ride ese día de la semana en los últimos días."""
    desde = ahora() - dt.timedelta(days=dias_atras)
    q = (select(viajes.c.correo, viajes.c.recogida_nombre, viajes.c.recogida_lat, viajes.c.recogida_lon,
                viajes.c.hora, usuarios.c.nombre)
         .join(usuarios, usuarios.c.correo == viajes.c.correo)
         .where(viajes.c.rol == "pasajero", viajes.c.dia == dia, viajes.c.creado >= desde))
    return pd.read_sql(q, motor())


def conductores_disponibles(dia, dias_atras=7):
    """Rides publicados por conductores reales para ese día de la semana (con su ruta)."""
    desde = ahora() - dt.timedelta(days=dias_atras)
    q = (select(viajes.c.id, viajes.c.correo, viajes.c.hora, viajes.c.ruta, viajes.c.asientos,
                viajes.c.detalle, usuarios.c.nombre)
         .join(usuarios, usuarios.c.correo == viajes.c.correo)
         .where(viajes.c.rol == "conductor", viajes.c.dia == dia, viajes.c.creado >= desde)
         .order_by(viajes.c.creado.desc()))
    df = pd.read_sql(q, motor())
    return df.drop_duplicates("correo")  # el ride más reciente de cada conductor


def crear_match(pasajero, conductor, iniciado_por, **datos):
    """Crea el match (o regresa el que ya existe entre esas dos personas ese día)."""
    with motor().begin() as c:
        ya = c.execute(select(matches.c.id).where(
            matches.c.pasajero == pasajero, matches.c.conductor == conductor,
            matches.c.dia == datos.get("dia"), matches.c.estado.in_(["pendiente", "aceptado"]))).scalar()
        if ya:
            return ya, False
        r = c.execute(matches.insert().values(pasajero=pasajero, conductor=conductor,
                                              iniciado_por=iniciado_por, estado="pendiente",
                                              creado=ahora(), **datos))
        return r.inserted_primary_key[0], True


def matches_de(correo):
    """Matches donde participa la persona, con nombre y teléfono de ambos."""
    up, uc = usuarios.alias("up"), usuarios.alias("uc")
    q = (select(matches, up.c.nombre.label("nombre_pasajero"), up.c.telefono.label("tel_pasajero"),
                uc.c.nombre.label("nombre_conductor"), uc.c.telefono.label("tel_conductor"))
         .join(up, up.c.correo == matches.c.pasajero)
         .join(uc, uc.c.correo == matches.c.conductor)
         .where(or_(matches.c.pasajero == correo, matches.c.conductor == correo))
         .order_by(matches.c.creado.desc()))
    return pd.read_sql(q, motor())


def cambiar_estado(match_id, estado):
    with motor().begin() as c:
        c.execute(update(matches).where(matches.c.id == match_id).values(estado=estado))


def enviar_mensaje(match_id, de, texto_msg):
    with motor().begin() as c:
        c.execute(mensajes.insert().values(match_id=match_id, de=de, texto=texto_msg[:500], creado=ahora()))


def mensajes_de(match_id):
    q = select(mensajes).where(mensajes.c.match_id == match_id).order_by(mensajes.c.id)
    return pd.read_sql(q, motor())


TABLAS = {"usuarios": usuarios, "viajes": viajes, "matches": matches, "mensajes": mensajes}


def tabla(nombre):
    t = TABLAS[nombre]
    orden = t.c.ultimo_acceso if nombre == "usuarios" else t.c.creado
    df = pd.read_sql(select(t).order_by(orden.desc()), motor())
    return df.drop(columns=["clave_hash", "clave_sal", "dispositivo_activo"], errors="ignore")
