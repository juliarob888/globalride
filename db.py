"""
db.py - Base de datos de GlobalRide

Guarda:
  - usuarios: quién entra a la app (correo, nombre, matrícula, teléfono, rol).
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
import json

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
    # Si la tabla viajes ya existía de una versión anterior, le agregamos las columnas nuevas
    existentes = {c["name"] for c in inspect(eng).get_columns("viajes")}
    with eng.begin() as c:
        for col, tipo in [("ruta", "TEXT"), ("asientos", "INTEGER")]:
            if col not in existentes:
                c.execute(text(f"ALTER TABLE viajes ADD COLUMN {col} {tipo}"))
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
    return pd.read_sql(select(t).order_by(orden.desc()), motor())
