"""
modelo_v1.py - GlobalRide (Avance 2)
Un solo comando:  python modelo_v1.py
Clasificador binario: predice match_exitoso (1 = viaje concretado y ambos califican 4 o 5).
Compara contra una línea base y contra el modelo, con partición 80/20.
"""
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score,
                             confusion_matrix, ConfusionMatrixDisplay)

df = pd.read_csv("datos_limpios.csv")
y = df["match_exitoso"]
X = df.drop(columns=["match_exitoso"])

X_ent, X_pru, y_ent, y_pru = train_test_split(
    X, y, test_size=0.20, random_state=42, stratify=y)
print("Entrenamiento:", X_ent.shape, "| Prueba:", X_pru.shape)

# --- Línea base: emparejar solo por cercanía de ruta (equivale a "misma zona") ---
base_pred = (X_pru["desviacion_ruta_min"] <= 3).astype(int)
print("\nLÍNEA BASE (desviación de ruta <= 3 min)")
print(f"  F1 = {f1_score(y_pru, base_pred):.3f} | precisión = {precision_score(y_pru, base_pred):.3f}"
      f" | recall = {recall_score(y_pru, base_pred):.3f}")

# --- Modelo: regresión logística con preprocesamiento ---
categoricas = ["zona_origen", "zona_destino", "dia_semana"]
numericas = [c for c in X.columns if c not in categoricas]
prepro = ColumnTransformer([
    ("cat", OneHotEncoder(handle_unknown="ignore"), categoricas),
    ("num", StandardScaler(), numericas),
])
modelo = Pipeline([("prepro", prepro), ("clf", LogisticRegression(max_iter=1000))])
modelo.fit(X_ent, y_ent)
pred = modelo.predict(X_pru)

print("\nMODELO: regresión logística")
print(f"  Exactitud = {accuracy_score(y_pru, pred):.3f}")
print(f"  Precisión = {precision_score(y_pru, pred):.3f}")
print(f"  Recall    = {recall_score(y_pru, pred):.3f}")
print(f"  F1        = {f1_score(y_pru, pred):.3f}   (meta del proyecto: >= 0.80)")
print("\nMatriz de confusión [[VN, FP], [FN, VP]]:")
print(confusion_matrix(y_pru, pred))

cv = cross_val_score(modelo, X, y, cv=5, scoring="f1")
print(f"\nValidación cruzada (5 pliegues) F1: {cv.round(3)}  media={cv.mean():.3f}  desv={cv.std():.3f}")

# Qué variables pesan más (coeficientes)
nombres = modelo.named_steps["prepro"].get_feature_names_out()
coefs = pd.Series(modelo.named_steps["clf"].coef_[0], index=nombres).sort_values()
print("\nVariables que más empujan hacia NO match (coeficientes más negativos):")
print(coefs.head(4).round(2).to_string())
print("\nVariables que más empujan hacia match (coeficientes más positivos):")
print(coefs.tail(4).round(2).to_string())

ConfusionMatrixDisplay(confusion_matrix(y_pru, pred), display_labels=["no match", "match"]).plot()
plt.title("GlobalRide - regresión logística (prueba)")
plt.savefig("matriz_globalride.png", dpi=120)
print("\nGuardado: matriz_globalride.png")