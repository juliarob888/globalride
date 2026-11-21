"""
comparacion_modelos.py - GlobalRide (Avance 3: comparacion de modelos)
Un solo comando:  python comparacion_modelos.py
Compara 6 modelos sobre datos_limpios.csv con la misma particion 80/20.
El mejor modelo se elige por validacion cruzada en entrenamiento (no por la prueba).
"""
import numpy as np
import pandas as pd
import joblib
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings("ignore")
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import GaussianNB
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score,
                             confusion_matrix)

df = pd.read_csv("datos_limpios.csv")
y = df["match_exitoso"]
X = df.drop(columns=["match_exitoso"])
X_ent, X_pru, y_ent, y_pru = train_test_split(X, y, test_size=0.20, random_state=42, stratify=y)
print("Entrenamiento:", X_ent.shape, "| Prueba:", X_pru.shape, "| proporcion de matches:", round(y.mean(), 3))

categoricas = ["zona_origen", "zona_destino", "dia_semana"]
numericas = [c for c in X.columns if c not in categoricas]

def prepro():
    return ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categoricas),
        ("num", StandardScaler(), numericas)])

def armar(clf):
    return Pipeline([("prepro", prepro()), ("clf", clf)])

# --- Arbol podado: ccp_alpha elegido por validacion cruzada SOLO con entrenamiento ---
cv = StratifiedKFold(5, shuffle=True, random_state=42)
base_arbol = armar(DecisionTreeClassifier(random_state=42))
Xp = base_arbol.named_steps["prepro"].fit_transform(X_ent)
alphas = DecisionTreeClassifier(random_state=42).cost_complexity_pruning_path(Xp, y_ent).ccp_alphas
alphas = np.unique(np.round(alphas[:-1], 5))[::max(1, len(alphas)//15)]
mejor_a, mejor_f1 = 0.0, -1
for al in alphas:
    s = cross_val_score(armar(DecisionTreeClassifier(random_state=42, ccp_alpha=al)), X_ent, y_ent, cv=cv, scoring="f1").mean()
    if s > mejor_f1: mejor_a, mejor_f1 = al, s
print(f"ccp_alpha elegido por validacion cruzada: {mejor_a:.5f} (F1 CV = {mejor_f1:.3f})")

modelos = {
    "Regresion logistica": armar(LogisticRegression(max_iter=1000)),
    "Naive Bayes": armar(GaussianNB()),
    "Arbol (profundidad 5)": armar(DecisionTreeClassifier(max_depth=5, random_state=42)),
    "Arbol podado": armar(DecisionTreeClassifier(random_state=42, ccp_alpha=mejor_a)),
    "Bosque aleatorio (300)": armar(RandomForestClassifier(n_estimators=300, random_state=42)),
    "Perceptron multicapa (64,)": armar(MLPClassifier(hidden_layer_sizes=(64,), max_iter=500, random_state=42)),
}

filas = []
base_pred = (X_pru["desviacion_ruta_min"] <= 3).astype(int)
filas.append({"modelo": "Linea base (desviacion <= 3 min)", "f1_cv": np.nan,
              "exactitud": accuracy_score(y_pru, base_pred), "precision": precision_score(y_pru, base_pred),
              "recall": recall_score(y_pru, base_pred), "f1_prueba": f1_score(y_pru, base_pred)})
ajustados = {}
for nombre, m in modelos.items():
    f1cv = cross_val_score(m, X_ent, y_ent, cv=cv, scoring="f1").mean()
    m.fit(X_ent, y_ent); ajustados[nombre] = m
    p = m.predict(X_pru)
    filas.append({"modelo": nombre, "f1_cv": f1cv, "exactitud": accuracy_score(y_pru, p),
                  "precision": precision_score(y_pru, p), "recall": recall_score(y_pru, p),
                  "f1_prueba": f1_score(y_pru, p)})
tabla = pd.DataFrame(filas).round(4)
print("\n" + tabla.to_string(index=False))
tabla.to_csv("comparacion_modelos.csv", index=False)

# El mejor se elige por F1 de validacion cruzada (no por la prueba)
elegido = tabla.dropna(subset=["f1_cv"]).sort_values("f1_cv", ascending=False).iloc[0]["modelo"]
print(f"\nModelo elegido (mayor F1 en validacion cruzada): {elegido}")
mejor = ajustados[elegido]
p = mejor.predict(X_pru)
print("Matriz de confusion [[VN, FP], [FN, VP]]:")
print(confusion_matrix(y_pru, p))
print(f"F1 en prueba = {f1_score(y_pru, p):.3f}  (meta del proyecto: >= 0.80)")
joblib.dump(mejor, "modelo_globalride.joblib")
print("Guardado: modelo_globalride.joblib")

# Grafica de comparacion
t = tabla.sort_values("f1_prueba")
plt.figure(figsize=(8, 4.5))
plt.barh(t["modelo"], t["f1_prueba"], color="tab:blue")
plt.axvline(0.80, color="red", linestyle="--", label="meta F1 = 0.80")
plt.xlabel("F1 en prueba"); plt.title("GlobalRide - comparacion de modelos")
plt.legend(); plt.tight_layout(); plt.savefig("comparacion_modelos.png", dpi=120)
print("Guardado: comparacion_modelos.csv y comparacion_modelos.png")