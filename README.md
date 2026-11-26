# GlobalRide: predicción de matches de carpool

Proyecto final de **Programación y Machine Learning**, Global University.
Autora: **Julia Robledo Esparza** · Profesor: **Omar Velázquez**

GlobalRide es una app de carpool para estudiantes de Global University. Este repositorio contiene el modelo de machine learning que predice si un viaje compartido tendrá un **match exitoso** entre conductor y pasajero.

## Contenido

| Archivo | Descripción |
|---|---|
| `datos_crudos.csv` | Datos originales |
| `preparar_datos.py` | Limpia los datos y genera `datos_limpios.csv` |
| `datos_limpios.csv` | Datos listos para entrenar |
| `modelo_v1.py` | Primer modelo (Avance 2) y `matriz_globalride.png` |
| `comparar_modelos.py` | Compara 6 algoritmos con la misma partición y validación cruzada (Avance 3) |
| `comparacion_modelos.csv` / `.png` | Tabla y gráfica con los resultados de la comparación |
| `modelo_globalride.joblib` | Modelo elegido, ya entrenado |
| `app_globalride.py` | App web con Streamlit (acceso, mapa, tarifa y match con IA) |
| `ags_datos.py` | Campus, puntos de encuentro de Aguascalientes, rutas y cálculo de tarifa |
| `db.py` | Base de datos: usuarios que entran y ubicaciones de cada viaje |
| `.streamlit/config.toml` | Tema oscuro de la app |

## Cómo ejecutarlo

1. Clona el repositorio y entra a la carpeta:

   ```bash
   git clone https://github.com/juliarob888/globalride.git
   cd globalride
   ```

2. Crea y activa un entorno virtual:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Instala las librerías:

   ```bash
   pip install -r requirements.txt
   ```

4. Ejecuta los scripts en este orden:

   ```bash
   python preparar_datos.py
   python modelo_v1.py
   python comparar_modelos.py
   ```

5. Abre la app:

   ```bash
   streamlit run app_globalride.py
   ```

## Comparación de modelos (Avance 3)

`comparar_modelos.py` entrena sobre la misma partición 80/20 estos modelos:

- Regresión logística
- Naive Bayes
- Árbol de decisión (profundidad 5)
- Árbol podado (`ccp_alpha` elegido por validación cruzada)
- Bosque aleatorio (300 árboles)
- Perceptrón multicapa

Además los compara con una línea base sencilla. El mejor modelo se elige por su **F1 en validación cruzada de 5 pliegues**, no por la prueba, y se guarda en `modelo_globalride.joblib`. La meta del proyecto es **F1 ≥ 0.80**.

## La app

- **Cuenta**: se crea una sola vez (correo institucional `@globaluniversity.edu.mx`, nombre, matrícula, teléfono de 10 dígitos y una clave). La clave se guarda cifrada (PBKDF2 con sal), nunca en texto.
- **Entrar de nuevo**: el teléfono queda recordado; solo se pide la clave (en iPhone, Safari puede llenarla con Face ID desde el llavero). Tras 5 intentos fallidos hay que esperar 60 s.
- **Un solo teléfono por cuenta**: si la cuenta está abierta en otro teléfono no deja entrar; con la clave correcta se puede cerrar la sesión del otro teléfono (por si se pierde). Cerrar sesión libera el teléfono.
- **Busco ride** (3 pasos): eliges dónde te recogen (lista de puntos de encuentro, escribiendo tu colonia, con el GPS del celular o tocando el mapa), cuándo vas, y ves tus **matches**: conductores reales cuya ruta pasa cerca, ordenados por la probabilidad que calcula el modelo de ML.
- **Doy ride** (3 pasos): eliges de dónde sales, cuándo y cuántos lugares tienes; la app traza tu ruta, marca los puntos de encuentro y los estudiantes reales que pidieron ride sobre ella, y puedes **ofrecerles ride**.
- **💬 Matches**: cada match (pendiente → aceptado/rechazado) tiene un **chat** dentro de la app. Al aceptarse, se muestra el teléfono con botones para **llamar** o escribir por **WhatsApp**.
- **Tarifa**: `(gasolina del viaje + $0.90/km de desgaste) / ocupantes + $5`, mínimo $15. El precio por litro se edita en la barra lateral (referencia Ags: Magna $23.79, Premium $25.94, enero 2026).
- Las rutas por calles vienen de OSRM (OpenStreetMap); sin internet se usa una estimación. Las coordenadas de campus y puntos son aproximadas y los conductores/pasajeros mostrados son de demostración.

## Base de datos

`db.py` guarda en dos tablas:

- **usuarios**: correo, nombre, matrícula, teléfono, rol, primer y último acceso, número de accesos.
- **viajes**: cada ride pedido o publicado. Para el pasajero, dónde está y dónde lo recogen; para el conductor, de dónde sale, su ruta y los puntos donde puede recoger (JSON).
- **matches**: pasajero + conductor emparejados, quién lo inició, punto de recogida, probabilidad de la IA y estado.
- **mensajes**: el chat de cada match.

Campus único: **Global University**, Av. Independencia 2134, Trojes de Alonso, CP 20116, Aguascalientes.

Por defecto se usa SQLite (`globalride.db`, ignorado por git). En Streamlit Cloud ese archivo se borra al reiniciar la app; para que los datos sean permanentes, agrega en **Settings → Secrets**:

```toml
DATABASE_URL = "postgresql://usuario:contraseña@host:5432/postgres"   # p. ej. Supabase
ADMIN_EMAILS = ["tu.correo@globaluniversity.edu.mx"]                   # quién ve el panel 🛠️
```
