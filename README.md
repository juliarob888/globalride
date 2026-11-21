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
| `app_globalride.py` | Interfaz web con Streamlit |

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