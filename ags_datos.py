"""
ags_datos.py - Datos geográficos y cálculos de GlobalRide
Campus, puntos de encuentro de Aguascalientes y alrededores, rutas y tarifa.

Las coordenadas son aproximadas: ajústalas a las ubicaciones reales si hace falta.
"""
import json
import math
import random
import urllib.request

CENTRO_AGS = (21.8853, -102.2916)

# Campus de destino (coinciden con zona_destino del modelo: "Centro" y "Norte")
CAMPUS = {
    "Campus Centro": {"coord": (21.8840, -102.2950), "zona_destino": "Centro"},
    "Campus Norte": {"coord": (21.9300, -102.2950), "zona_destino": "Norte"},
}

# Centros de cada zona del modelo, para clasificar un punto del mapa
ZONAS = {
    "Centro": (21.8820, -102.2960),
    "Norte": (21.9250, -102.2900),
    "Sur": (21.8450, -102.2900),
    "Oriente": (21.8800, -102.2550),
    "Poniente": (21.8900, -102.3300),
    "Jesus Maria": (21.9610, -102.3430),
}

# Puntos de encuentro seguros y conocidos (lugares públicos y bien iluminados)
PUNTOS = [
    {"nombre": "Plaza de la Patria", "coord": (21.8818, -102.2960), "zona": "Centro"},
    {"nombre": "Jardín de San Marcos", "coord": (21.8786, -102.3025), "zona": "Centro"},
    {"nombre": "Central Camionera", "coord": (21.8605, -102.2905), "zona": "Sur"},
    {"nombre": "Plaza Villasunción", "coord": (21.8475, -102.2835), "zona": "Sur"},
    {"nombre": "Parque Rodolfo Landeros", "coord": (21.8375, -102.2845), "zona": "Sur"},
    {"nombre": "Tecnológico de Aguascalientes", "coord": (21.8790, -102.2610), "zona": "Oriente"},
    {"nombre": "Línea Verde (Ojocaliente)", "coord": (21.8700, -102.2480), "zona": "Oriente"},
    {"nombre": "Expoplaza", "coord": (21.8790, -102.3065), "zona": "Poniente"},
    {"nombre": "Av. Aguascalientes Poniente", "coord": (21.8930, -102.3200), "zona": "Poniente"},
    {"nombre": "UAA Ciudad Universitaria", "coord": (21.9135, -102.3155), "zona": "Norte"},
    {"nombre": "Galerías Aguascalientes", "coord": (21.9170, -102.3100), "zona": "Norte"},
    {"nombre": "Plaza Altaria", "coord": (21.9240, -102.2890), "zona": "Norte"},
    {"nombre": "Av. Siglo XXI Norte", "coord": (21.9250, -102.2700), "zona": "Norte"},
    {"nombre": "Jardín Principal Jesús María", "coord": (21.9611, -102.3435), "zona": "Jesus Maria"},
    {"nombre": "Fracc. Valle de los Cactus (JM)", "coord": (21.9450, -102.3300), "zona": "Jesus Maria"},
    {"nombre": "San Francisco de los Romo", "coord": (22.0730, -102.2710), "zona": "Norte"},
]

# Precios de referencia por litro (Aguascalientes, enero 2026). Se pueden editar en la app.
PRECIO_GAS_REF = {"Magna (regular)": 23.79, "Premium": 25.94}


def distancia_km(a, b):
    """Distancia en línea recta (haversine) entre dos (lat, lon)."""
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def zona_de(coord):
    return min(ZONAS, key=lambda z: distancia_km(coord, ZONAS[z]))


def puntos_cercanos(coord, n=3):
    orden = sorted(PUNTOS, key=lambda p: distancia_km(coord, p["coord"]))
    return [dict(p, dist=distancia_km(coord, p["coord"])) for p in orden[:n]]


def ruta(origen, destino):
    """Ruta por calles con OSRM (servicio público). Si falla, línea recta x1.35.
    Devuelve (lista de (lat, lon), km, minutos, es_real)."""
    url = ("https://router.project-osrm.org/route/v1/driving/"
           f"{origen[1]:.5f},{origen[0]:.5f};{destino[1]:.5f},{destino[0]:.5f}"
           "?overview=full&geometries=geojson")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "globalride-demo"})
        with urllib.request.urlopen(req, timeout=5) as r:
            datos = json.load(r)
        mejor = datos["routes"][0]
        puntos = [(lat, lon) for lon, lat in mejor["geometry"]["coordinates"]]
        return puntos, mejor["distance"] / 1000, mejor["duration"] / 60, True
    except Exception:
        km = distancia_km(origen, destino) * 1.35
        return [origen, destino], km, km / 28 * 60, False  # ~28 km/h promedio en ciudad


def distancia_a_ruta(coord, linea):
    """Distancia aproximada (km) de un punto al trazo de la ruta."""
    if len(linea) < 2:
        return distancia_km(coord, linea[0])
    lat0 = math.radians(coord[0])
    kx, ky = 111.32 * math.cos(lat0), 110.57  # km por grado

    def xy(p):
        return ((p[1] - coord[1]) * kx, (p[0] - coord[0]) * ky)

    mejor = float("inf")
    paso = max(1, len(linea) // 400)  # submuestreo para rutas largas
    pts = linea[::paso] + [linea[-1]]
    for a, b in zip(pts, pts[1:]):
        (ax, ay), (bx, by) = xy(a), xy(b)
        dx, dy = bx - ax, by - ay
        L = dx * dx + dy * dy
        t = 0 if L == 0 else max(0, min(1, -(ax * dx + ay * dy) / L))
        mejor = min(mejor, math.hypot(ax + t * dx, ay + t * dy))
    return mejor


def tarifa(km, precio_litro, rendimiento_km_l, pasajeros=1):
    """Cooperación sugerida por pasajero.
    Gasolina del viaje + desgaste del auto ($0.90/km), dividido entre todos los
    ocupantes (el conductor también paga su parte), más $5 de servicio. Mínimo $15."""
    litros = km / rendimiento_km_l
    gasolina = litros * precio_litro
    desgaste = 0.90 * km
    ocupantes = pasajeros + 1
    por_persona = (gasolina + desgaste) / ocupantes + 5
    total = max(15, round(por_persona))
    return {"litros": litros, "gasolina": gasolina, "desgaste": desgaste,
            "ocupantes": ocupantes, "por_pasajero": total, "por_km": total / km if km else 0}


NOMBRES = ["Sofi", "Diego", "Valeria", "Emiliano", "Regina", "Santiago", "Ximena", "Mateo",
           "Renata", "Leo", "Camila", "Iker", "Fer", "Andrés", "Majo", "Rodrigo"]
CARRERAS = ["Ing. Industrial", "Diseño", "Derecho", "Negocios Int.", "Psicología",
            "Mercadotecnia", "Arquitectura", "Ing. en Software", "Comunicación"]
AUTOS = ["Versa gris", "Aveo blanco", "Jetta negro", "Mazda 3 rojo", "Rio azul",
         "March plata", "Golf blanco", "Onix gris", "Vento azul"]


def conductores_cerca(coord, hora_decimal, n=4):
    """Conductores simulados para la demo (deterministas según el punto)."""
    rng = random.Random(f"{coord[0]:.3f},{coord[1]:.3f}")
    lista = []
    for _ in range(n):
        lista.append({
            "nombre": rng.choice(NOMBRES),
            "carrera": rng.choice(CARRERAS),
            "auto": rng.choice(AUTOS),
            "calificacion": round(rng.uniform(3.8, 5.0), 1),
            "hora": max(5.0, min(19.0, hora_decimal + rng.choice([-30, -15, -10, 0, 5, 10, 20, 40]) / 60)),
            "asientos": rng.randint(1, 4),
            "desvio_min": round(rng.uniform(0.5, 12), 1),
            "rendimiento": rng.choice([11, 13, 14, 15, 16]),
        })
    return lista


def pasajeros_esperando(punto_nombre):
    rng = random.Random("esperando:" + punto_nombre)
    return [{"nombre": n, "carrera": rng.choice(CARRERAS)}
            for n in rng.sample(NOMBRES, rng.randint(0, 3))]
