# ============================================================
# VERIFICACIÓN DE PÉRDIDA DE HILOS / ISSUES
# ============================================================

import pandas as pd
import numpy as np

# ------------------------------------------------------------
# 1. CARGAR DATASET ORIGINAL
# ------------------------------------------------------------
# Usa aquí el archivo ANTES de eliminar ruido.
# Debe tener issue_number y comment_body_clean_final o comment_body_raw.

original_file = "Dataset_integration_semantico_topk_enriched_final.xlsx"

df_original = pd.read_excel(original_file)

print("Dataset original cargado:")
print(df_original.shape)

print("\nColumnas del dataset original:")
print(df_original.columns.tolist())

# ---

# ------------------------------------------------------------
# 2. USAR DATASET OPERACIONAL ACTUAL
# ------------------------------------------------------------
# Si ya existe df_operational_28 en memoria, úsalo.
# Si no existe, carga el archivo exportado.

# Opción A: si ya está en memoria
#df_operational = df_operational_28.copy()

# Opción B: si no está en memoria, descomenta:
df_operational = pd.read_excel("Dataset_integration_semantico_topk_enriched_final.xlsx")

print("Dataset operacional:")
print(df_operational.shape)

# ---

# ============================================================
# VERIFICACIÓN DE PÉRDIDA DE HILOS / ISSUES
# ============================================================

import pandas as pd
import numpy as np

# ------------------------------------------------------------
# 1. CARGAR DATASET ORIGINAL
# ------------------------------------------------------------
# Usa aquí el archivo ANTES de eliminar ruido.
# Debe tener issue_number y comment_body_clean_final o comment_body_raw.

original_file = "Dataset_integration_semantico_topk_enriched_final.xlsx"

df_original = pd.read_excel(original_file)

print("Dataset original cargado:")
print(df_original.shape)

print("\nColumnas del dataset original:")
print(df_original.columns.tolist())

# ---

# ------------------------------------------------------------
# 3. VALIDAR QUE AMBOS TIENEN issue_number
# ------------------------------------------------------------

print("issue_number en original:", "issue_number" in df_original.columns)
print("issue_number en operacional:", "issue_number" in df_operational.columns)

# ---

# ------------------------------------------------------------
# 4. COMPARAR ISSUES ÚNICOS
# ------------------------------------------------------------

original_issues = set(df_original["issue_number"].dropna().unique())
operational_issues = set(df_operational["issue_number"].dropna().unique())

lost_issues = original_issues - operational_issues
new_issues = operational_issues - original_issues

print("==============================================")
print("COMPARACIÓN DE ISSUES")
print("==============================================")
print("Issues en original:", len(original_issues))
print("Issues en operacional:", len(operational_issues))
print("Issues perdidos:", len(lost_issues))
print("Issues nuevos inesperados:", len(new_issues))

# ---

print(df_original.columns.tolist())

# ---

# ------------------------------------------------------------
# 5. COMPARAR COMENTARIOS POR ISSUE
# ------------------------------------------------------------

original_counts = (
    df_original
    .groupby("issue_number")
    .size()
    .reset_index(name="original_comments")
)

operational_counts = (
    df_operational
    .groupby("issue_number")
    .size()
    .reset_index(name="operational_comments")
)

issue_loss = original_counts.merge(
    operational_counts,
    on="issue_number",
    how="left"
)

issue_loss["operational_comments"] = (
    issue_loss["operational_comments"]
    .fillna(0)
    .astype(int)
)

issue_loss["lost_comments"] = (
    issue_loss["original_comments"]
    -
    issue_loss["operational_comments"]
)

issue_loss["loss_percentage"] = (
    issue_loss["lost_comments"]
    /
    issue_loss["original_comments"]
    * 100
).round(2)

display(
    issue_loss.sort_values(
        "loss_percentage",
        ascending=False
    ).head(30)
)

# ---

df = pd.read_excel(
    "Dataset_integration_semantico_topk_enriched_final.xlsx"
)

print(df.shape)

print(df.columns.tolist())

# ---

cols = [
    "top_microcause_names",
    "top_microcause_scores",
    "community_smells",
    "risks"
]

display(df[cols].head(10))

# ---

# ============================================================
# PASO 1. FUNCIONES PARA PARSEAR LISTAS Y VIÑETAS
# ============================================================

import ast
import pandas as pd
from collections import Counter

def parse_list_cell(value):
    if pd.isna(value):
        return []
    try:
        return ast.literal_eval(str(value))
    except:
        return []

def parse_bullet_cell(value):
    if pd.isna(value):
        return []

    items = []
    for line in str(value).split("\n"):
        line = line.strip()
        line = line.replace("•", "").strip()
        if line:
            items.append(line)
    return items

# ---

# ============================================================
# PASO 2. PARSEAR COLUMNAS TOP-K, SMELLS Y RIESGOS
# ============================================================

df["top_microcause_names_list"] = df["top_microcause_names"].apply(parse_list_cell)
df["top_microcause_scores_list"] = df["top_microcause_scores"].apply(parse_list_cell)

df["community_smells_list"] = df["community_smells"].apply(parse_bullet_cell)
df["risks_list"] = df["risks"].apply(parse_bullet_cell)

display(df[
    [
        "issue_number",
        "top_microcause_names_list",
        "top_microcause_scores_list",
        "community_smells_list",
        "risks_list"
    ]
].head(10))

# ---

# ============================================================
# PASO 3. AGREGAR MICROCAUSAS, SMELLS Y RIESGOS POR ISSUE
# ============================================================

def aggregate_issue(group):

    micro_counter = Counter()
    smell_counter = Counter()
    risk_counter = Counter()
    macro_counter = Counter()

    for _, row in group.iterrows():

        macro_counter[row["final_cause_for_analysis"]] += 1

        micro_names = row["top_microcause_names_list"]
        micro_scores = row["top_microcause_scores_list"]

        for name, score in zip(micro_names, micro_scores):
            micro_counter[name] += float(score)

        for smell in row["community_smells_list"]:
            smell_counter[smell] += 1

        for risk in row["risks_list"]:
            risk_counter[risk] += 1

    return pd.Series({
        "comment_count": len(group),
        "dominant_macrocauses": macro_counter.most_common(5),
        "dominant_microcauses": micro_counter.most_common(5),
        "dominant_community_smells": smell_counter.most_common(5),
        "dominant_risks": risk_counter.most_common(5),
        "issue_text": "\n\n".join(group["comment_body_clean_final"].astype(str))
    })

# ---

# ============================================================
# PASO 4. DATASET ADAPTATIVO POR ISSUE
# ============================================================

df_issue_adaptive = (
    df
    .sort_values(["issue_number", "comment_created_at"])
    .groupby("issue_number")
    .apply(aggregate_issue)
    .reset_index()
)

print("Dataset adaptativo por issue:")
print(df_issue_adaptive.shape)

display(df_issue_adaptive.head())

# ---

# ============================================================
# PASO 6. MÉTRICAS ADAPTATIVAS POR ISSUE
# ============================================================

def count_items(x):
    if isinstance(x, list):
        return len(x)
    return 0

def top_frequency(x):
    if isinstance(x, list) and len(x) > 0:
        return x[0][1]
    return 0

df_issue_adaptive["macro_diversity"] = (
    df_issue_adaptive["dominant_macrocauses"]
    .apply(count_items)
)

df_issue_adaptive["micro_diversity"] = (
    df_issue_adaptive["dominant_microcauses"]
    .apply(count_items)
)

df_issue_adaptive["risk_diversity"] = (
    df_issue_adaptive["dominant_risks"]
    .apply(count_items)
)

df_issue_adaptive["smell_diversity"] = (
    df_issue_adaptive["dominant_community_smells"]
    .apply(count_items)
)

df_issue_adaptive["top_macro_frequency"] = (
    df_issue_adaptive["dominant_macrocauses"]
    .apply(top_frequency)
)

df_issue_adaptive["top_micro_score"] = (
    df_issue_adaptive["dominant_microcauses"]
    .apply(top_frequency)
)

df_issue_adaptive["top_smell_frequency"] = (
    df_issue_adaptive["dominant_community_smells"]
    .apply(top_frequency)
)

df_issue_adaptive["top_risk_frequency"] = (
    df_issue_adaptive["dominant_risks"]
    .apply(top_frequency)
)

display(df_issue_adaptive.head())

# ---

from collections import Counter

macro_counter = Counter()

for macros in df_issue_adaptive["dominant_macrocauses"]:
    for macro, freq in macros:
        macro_counter[macro] += freq

macro_df = (
    pd.DataFrame(
        macro_counter.items(),
        columns=["macrocause", "frequency"]
    )
    .sort_values("frequency", ascending=False)
)

display(macro_df)

# ---

# ============================================================
# FASE II - PASO 2. MICROCAUSAS DOMINANTES GLOBALES
# ============================================================

from collections import Counter
import pandas as pd

micro_counter = Counter()

for micros in df_issue_adaptive["dominant_microcauses"]:
    for micro, score in micros:
        micro_counter[micro] += score

micro_df = (
    pd.DataFrame(
        micro_counter.items(),
        columns=["microcause", "aggregated_score"]
    )
    .sort_values("aggregated_score", ascending=False)
)

display(micro_df.head(20))

# ---

from collections import Counter

smell_counter = Counter()

for smells in df_issue_adaptive["dominant_community_smells"]:
    for smell, freq in smells:
        smell_counter[smell] += freq

smell_df = (
    pd.DataFrame(
        smell_counter.items(),
        columns=["community_smell", "frequency"]
    )
    .sort_values("frequency", ascending=False)
)

display(smell_df)

# ---

# ============================================================
# FASE III. SOCIAL DEBT INDEX
# PASO 1. VARIABLES BASE POR ISSUE
# ============================================================

def list_len(x):
    if isinstance(x, list):
        return len(x)
    return 0

def top_value(x):
    if isinstance(x, list) and len(x) > 0:
        return x[0][1]
    return 0

df_issue_adaptive["macro_diversity"] = (
    df_issue_adaptive["dominant_macrocauses"].apply(list_len)
)

df_issue_adaptive["micro_diversity"] = (
    df_issue_adaptive["dominant_microcauses"].apply(list_len)
)

df_issue_adaptive["smell_diversity"] = (
    df_issue_adaptive["dominant_community_smells"].apply(list_len)
)

df_issue_adaptive["risk_diversity"] = (
    df_issue_adaptive["dominant_risks"].apply(list_len)
)

df_issue_adaptive["top_macro_frequency"] = (
    df_issue_adaptive["dominant_macrocauses"].apply(top_value)
)

df_issue_adaptive["top_micro_score"] = (
    df_issue_adaptive["dominant_microcauses"].apply(top_value)
)

df_issue_adaptive["top_smell_frequency"] = (
    df_issue_adaptive["dominant_community_smells"].apply(top_value)
)

df_issue_adaptive["top_risk_frequency"] = (
    df_issue_adaptive["dominant_risks"].apply(top_value)
)

display(
    df_issue_adaptive[
        [
            "issue_number",
            "comment_count",
            "macro_diversity",
            "micro_diversity",
            "smell_diversity",
            "risk_diversity",
            "top_macro_frequency",
            "top_micro_score",
            "top_smell_frequency",
            "top_risk_frequency"
        ]
    ].head(10)
)

# ---

# ============================================================
# FASE III. SOCIAL DEBT INDEX
# PASO 2. NORMALIZACIÓN DE VARIABLES
# ============================================================

from sklearn.preprocessing import MinMaxScaler

sdi_features = [
    "comment_count",
    "macro_diversity",
    "micro_diversity",
    "smell_diversity",
    "risk_diversity",
    "top_macro_frequency",
    "top_micro_score",
    "top_smell_frequency",
    "top_risk_frequency"
]

scaler = MinMaxScaler()

normalized_values = scaler.fit_transform(
    df_issue_adaptive[sdi_features]
)

df_sdi_norm = pd.DataFrame(
    normalized_values,
    columns=[f"{col}_norm" for col in sdi_features]
)

df_issue_adaptive = pd.concat(
    [
        df_issue_adaptive.reset_index(drop=True),
        df_sdi_norm
    ],
    axis=1
)

display(
    df_issue_adaptive[
        ["issue_number"] + [f"{col}_norm" for col in sdi_features]
    ].head(10)
)

# ---

# ============================================================
# PASO 3. ESTADÍSTICAS DESCRIPTIVAS
# ============================================================

cols = [
    "comment_count",
    "macro_diversity",
    "micro_diversity",
    "smell_diversity",
    "risk_diversity",
    "top_macro_frequency",
    "top_micro_score",
    "top_smell_frequency",
    "top_risk_frequency"
]

display(
    df_issue_adaptive[cols]
    .describe()
    .round(3)
)

# ---

# ============================================================
# PASO 4. SOCIAL DEBT INDEX v1
# ============================================================

sdi_variables = [
    "comment_count_norm",
    "macro_diversity_norm",
    "top_macro_frequency_norm",
    "top_micro_score_norm",
    "top_smell_frequency_norm",
    "top_risk_frequency_norm"
]

df_issue_adaptive["social_debt_index"] = (
    df_issue_adaptive[sdi_variables]
    .mean(axis=1)
)

display(
    df_issue_adaptive[
        [
            "issue_number",
            "social_debt_index"
        ]
    ]
    .sort_values(
        "social_debt_index",
        ascending=False
    )
    .head(20)
)

# ---

# ============================================================
# PASO 5. COMPONENTES DE LOS ISSUES CON MAYOR SDI
# ============================================================

top_sdi_issues = (
    df_issue_adaptive
    .sort_values("social_debt_index", ascending=False)
    .head(20)
)

display(
    top_sdi_issues[
        [
            "issue_number",
            "social_debt_index",
            "comment_count",
            "macro_diversity",
            "top_macro_frequency",
            "top_micro_score",
            "top_smell_frequency",
            "top_risk_frequency"
        ]
    ]
)

# ---

# ============================================================
# PASO 6. CLASIFICAR NIVEL DE DEUDA SOCIAL
# Low / Medium / High
# ============================================================

q1 = df_issue_adaptive["social_debt_index"].quantile(0.33)
q2 = df_issue_adaptive["social_debt_index"].quantile(0.66)

def classify_social_debt_level(score):
    if score <= q1:
        return "Low Social Debt"
    elif score <= q2:
        return "Medium Social Debt"
    else:
        return "High Social Debt"

df_issue_adaptive["social_debt_level"] = (
    df_issue_adaptive["social_debt_index"]
    .apply(classify_social_debt_level)
)

print("Umbral Low/Medium:", q1)
print("Umbral Medium/High:", q2)

display(
    df_issue_adaptive["social_debt_level"]
    .value_counts()
    .reset_index()
    .rename(columns={"index": "social_debt_level", "social_debt_level": "count"})
)

# ---

# ============================================================
# PASO 7. VALIDACIÓN INTERNA DEL SOCIAL DEBT INDEX
# Comparación de variables por nivel de deuda social
# ============================================================

validation_by_level = (
    df_issue_adaptive
    .groupby("social_debt_level")
    [
        [
            "social_debt_index",
            "comment_count",
            "macro_diversity",
            "top_macro_frequency",
            "top_micro_score",
            "top_smell_frequency",
            "top_risk_frequency"
        ]
    ]
    .mean()
    .round(3)
)

display(validation_by_level)

# ---

# ============================================================
# PASO 8. COMMUNITY SMELLS DOMINANTES POR NIVEL DE DEUDA SOCIAL
# ============================================================

from collections import Counter
import pandas as pd

rows = []

for level, group in df_issue_adaptive.groupby("social_debt_level"):
    smell_counter = Counter()

    for smells in group["dominant_community_smells"]:
        for smell, freq in smells:
            smell_counter[smell] += freq

    for smell, frequency in smell_counter.most_common(10):
        rows.append({
            "social_debt_level": level,
            "community_smell": smell,
            "frequency": frequency
        })

smells_by_level = pd.DataFrame(rows)

display(smells_by_level)

# ---

# ============================================================
# PASO 9. RIESGOS DOMINANTES POR NIVEL DE DEUDA SOCIAL
# ============================================================

from collections import Counter
import pandas as pd

rows = []

for level, group in df_issue_adaptive.groupby("social_debt_level"):
    risk_counter = Counter()

    for risks in group["dominant_risks"]:
        for risk, freq in risks:
            risk_counter[risk] += freq

    for risk, frequency in risk_counter.most_common(10):
        rows.append({
            "social_debt_level": level,
            "risk": risk,
            "frequency": frequency
        })

risks_by_level = pd.DataFrame(rows)

display(risks_by_level)

# ---

# ============================================================
# PASO 10. MICROCAUSAS DOMINANTES POR NIVEL DE DEUDA SOCIAL
# ============================================================

from collections import Counter
import pandas as pd

rows = []

for level, group in df_issue_adaptive.groupby("social_debt_level"):
    micro_counter = Counter()

    for micros in group["dominant_microcauses"]:
        for micro, score in micros:
            micro_counter[micro] += score

    for micro, score in micro_counter.most_common(15):
        rows.append({
            "social_debt_level": level,
            "microcause": micro,
            "aggregated_score": score
        })

microcauses_by_level = pd.DataFrame(rows)

display(microcauses_by_level)

# ---

# ============================================================
# PASO 11. MACROCAUSAS DOMINANTES POR NIVEL DE DEUDA SOCIAL
# ============================================================

from collections import Counter
import pandas as pd

rows = []

for level, group in df_issue_adaptive.groupby("social_debt_level"):
    macro_counter = Counter()

    for macros in group["dominant_macrocauses"]:
        for macro, freq in macros:
            macro_counter[macro] += freq

    for macro, frequency in macro_counter.most_common(10):
        rows.append({
            "social_debt_level": level,
            "macrocause": macro,
            "frequency": frequency
        })

macrocauses_by_level = pd.DataFrame(rows)

display(macrocauses_by_level)

# ---

# ============================================================
# PASO 12. PERFIL RESUMEN DEL MODELO ADAPTATIVO POR NIVEL
# ============================================================

summary_profile = (
    df_issue_adaptive
    .groupby("social_debt_level")
    .agg(
        issue_count=("issue_number", "count"),
        mean_sdi=("social_debt_index", "mean"),
        mean_comments=("comment_count", "mean"),
        mean_macro_diversity=("macro_diversity", "mean"),
        mean_top_macro_frequency=("top_macro_frequency", "mean"),
        mean_top_micro_score=("top_micro_score", "mean"),
        mean_top_smell_frequency=("top_smell_frequency", "mean"),
        mean_top_risk_frequency=("top_risk_frequency", "mean")
    )
    .round(3)
    .reset_index()
)

display(summary_profile)

# ---

# ============================================================
# PASO 13. EXPORTAR RESULTADO FINAL DEL MODELO ADAPTATIVO
# ============================================================

output_file = "adaptive_social_debt_issue_model.xlsx"

df_issue_adaptive.to_excel(output_file, index=False)

print("Archivo exportado:", output_file)
print("Dimensiones:", df_issue_adaptive.shape)

# ---

# ============================================================
# FASE IV. MODELOS PREDICTIVOS
# PASO 14. DISTRIBUCIÓN DE LA VARIABLE OBJETIVO
# ============================================================

display(
    df_issue_adaptive["social_debt_level"]
    .value_counts()
    .reset_index()
    .rename(columns={
        "index": "social_debt_level",
        "social_debt_level": "count"
    })
)

display(
    df_issue_adaptive["social_debt_level"]
    .value_counts(normalize=True)
    .mul(100)
    .round(2)
    .reset_index()
    .rename(columns={
        "index": "social_debt_level",
        "social_debt_level": "percentage"
    })
)

# ---

# ============================================================
# FASE IV. MODELOS PREDICTIVOS
# PASO 15. MODELO BASELINE TF-IDF + LOGISTIC REGRESSION
# Objetivo: predecir social_debt_level desde issue_text
# ============================================================

from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, accuracy_score, f1_score, confusion_matrix
import pandas as pd

# -----------------------------
# 1. Definir X e y
# -----------------------------
X = df_issue_adaptive["issue_text"].astype(str)
y = df_issue_adaptive["social_debt_level"]

# -----------------------------
# 2. División train/test estratificada
# -----------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.30,
    random_state=42,
    stratify=y
)

# -----------------------------
# 3. Pipeline baseline
# -----------------------------
baseline_model = Pipeline([
    (
        "tfidf",
        TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),
            min_df=2
        )
    ),
    (
        "clf",
        LogisticRegression(
            max_iter=1000,
            class_weight="balanced",
            random_state=42
        )
    )
])

# -----------------------------
# 4. Entrenar
# -----------------------------
baseline_model.fit(X_train, y_train)

# -----------------------------
# 5. Predecir
# -----------------------------
y_pred = baseline_model.predict(X_test)

# -----------------------------
# 6. Métricas
# -----------------------------
accuracy = accuracy_score(y_test, y_pred)
macro_f1 = f1_score(y_test, y_pred, average="macro")
weighted_f1 = f1_score(y_test, y_pred, average="weighted")

print("Accuracy:", round(accuracy, 4))
print("Macro F1:", round(macro_f1, 4))
print("Weighted F1:", round(weighted_f1, 4))

print("\nClassification report:")
print(classification_report(y_test, y_pred))

# -----------------------------
# 7. Matriz de confusión
# -----------------------------
labels = baseline_model.classes_

cm = confusion_matrix(y_test, y_pred, labels=labels)

cm_df = pd.DataFrame(
    cm,
    index=[f"True {label}" for label in labels],
    columns=[f"Pred {label}" for label in labels]
)

display(cm_df)

# ---

# ============================================================
# FASE IV. MODELOS PREDICTIVOS
# PASO 16. MODELO TF-IDF + LINEAR SVM
# Objetivo: predecir social_debt_level desde issue_text
# ============================================================

from sklearn.svm import LinearSVC
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import classification_report, accuracy_score, f1_score, confusion_matrix
import pandas as pd

svm_model = Pipeline([
    (
        "tfidf",
        TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),
            min_df=2
        )
    ),
    (
        "clf",
        LinearSVC(
            class_weight="balanced",
            random_state=42
        )
    )
])

# Entrenar
svm_model.fit(X_train, y_train)

# Predecir
y_pred_svm = svm_model.predict(X_test)

# Métricas
accuracy_svm = accuracy_score(y_test, y_pred_svm)
macro_f1_svm = f1_score(y_test, y_pred_svm, average="macro")
weighted_f1_svm = f1_score(y_test, y_pred_svm, average="weighted")

print("Accuracy:", round(accuracy_svm, 4))
print("Macro F1:", round(macro_f1_svm, 4))
print("Weighted F1:", round(weighted_f1_svm, 4))

print("\nClassification report:")
print(classification_report(y_test, y_pred_svm))

# Matriz de confusión
labels = svm_model.classes_

cm_svm = confusion_matrix(y_test, y_pred_svm, labels=labels)

cm_svm_df = pd.DataFrame(
    cm_svm,
    index=[f"True {label}" for label in labels],
    columns=[f"Pred {label}" for label in labels]
)

display(cm_svm_df)

# ---

# ============================================================
# FASE IV. MODELOS PREDICTIVOS
# PASO 17. MODELO CON VARIABLES ESTRUCTURADAS DEL MODELO ADAPTATIVO
# Random Forest
# ============================================================

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score, f1_score, confusion_matrix
import pandas as pd

# -----------------------------
# 1. Variables estructuradas
# -----------------------------
structured_features = [
    "comment_count",
    "macro_diversity",
    "top_macro_frequency",
    "top_micro_score",
    "top_smell_frequency",
    "top_risk_frequency"
]

X_struct = df_issue_adaptive[structured_features]
y_struct = df_issue_adaptive["social_debt_level"]

# -----------------------------
# 2. División train/test estratificada
# -----------------------------
X_train_s, X_test_s, y_train_s, y_test_s = train_test_split(
    X_struct,
    y_struct,
    test_size=0.30,
    random_state=42,
    stratify=y_struct
)

# -----------------------------
# 3. Modelo Random Forest
# -----------------------------
rf_model = RandomForestClassifier(
    n_estimators=300,
    max_depth=None,
    class_weight="balanced",
    random_state=42
)

# -----------------------------
# 4. Entrenar
# -----------------------------
rf_model.fit(X_train_s, y_train_s)

# -----------------------------
# 5. Predecir
# -----------------------------
y_pred_rf = rf_model.predict(X_test_s)

# -----------------------------
# 6. Métricas
# -----------------------------
accuracy_rf = accuracy_score(y_test_s, y_pred_rf)
macro_f1_rf = f1_score(y_test_s, y_pred_rf, average="macro")
weighted_f1_rf = f1_score(y_test_s, y_pred_rf, average="weighted")

print("Accuracy:", round(accuracy_rf, 4))
print("Macro F1:", round(macro_f1_rf, 4))
print("Weighted F1:", round(weighted_f1_rf, 4))

print("\nClassification report:")
print(classification_report(y_test_s, y_pred_rf))

# -----------------------------
# 7. Matriz de confusión
# -----------------------------
labels = rf_model.classes_

cm_rf = confusion_matrix(y_test_s, y_pred_rf, labels=labels)

cm_rf_df = pd.DataFrame(
    cm_rf,
    index=[f"True {label}" for label in labels],
    columns=[f"Pred {label}" for label in labels]
)

display(cm_rf_df)

# -----------------------------
# 8. Importancia de variables
# -----------------------------
feature_importance = pd.DataFrame({
    "feature": structured_features,
    "importance": rf_model.feature_importances_
}).sort_values("importance", ascending=False)

display(feature_importance)

# ---

# ============================================================
# PASO 18. TABLA COMPARATIVA DE MODELOS
# ============================================================

model_results = pd.DataFrame([
    {
        "model": "TF-IDF + Logistic Regression",
        "input_type": "Issue text",
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "weighted_f1": weighted_f1
    },
    {
        "model": "TF-IDF + Linear SVM",
        "input_type": "Issue text",
        "accuracy": accuracy_svm,
        "macro_f1": macro_f1_svm,
        "weighted_f1": weighted_f1_svm
    },
    {
        "model": "Random Forest",
        "input_type": "Adaptive structured features",
        "accuracy": accuracy_rf,
        "macro_f1": macro_f1_rf,
        "weighted_f1": weighted_f1_rf
    }
])

model_results = model_results.round(4)

display(model_results)

# ---

# ============================================================
# PASO 19. EXPORTAR TABLA COMPARATIVA DE MODELOS
# ============================================================

output_models = "model_comparison_social_debt.xlsx"

model_results.to_excel(output_models, index=False)

print("Archivo exportado:", output_models)
print("Dimensiones:", model_results.shape)

# ---

# ============================================================
# PASO 20. CROSS-VALIDATION ESTRATIFICADA
# Comparación más robusta de modelos
# ============================================================

from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.metrics import make_scorer, accuracy_score, f1_score
import pandas as pd

# -----------------------------
# 1. Definir validación cruzada
# -----------------------------
cv = StratifiedKFold(
    n_splits=5,
    shuffle=True,
    random_state=42
)

# -----------------------------
# 2. Métricas
# -----------------------------
scoring = {
    "accuracy": "accuracy",
    "macro_f1": "f1_macro",
    "weighted_f1": "f1_weighted"
}

# -----------------------------
# 3. Modelos a comparar
# -----------------------------
models_cv = {
    "TF-IDF + Logistic Regression": baseline_model,
    "TF-IDF + Linear SVM": svm_model,
    "Random Forest + Adaptive Features": rf_model
}

# -----------------------------
# 4. Datos de entrada por modelo
# -----------------------------
model_inputs = {
    "TF-IDF + Logistic Regression": (X, y),
    "TF-IDF + Linear SVM": (X, y),
    "Random Forest + Adaptive Features": (X_struct, y_struct)
}

# -----------------------------
# 5. Ejecutar cross-validation
# -----------------------------
cv_results_rows = []

for model_name, model in models_cv.items():
    X_model, y_model = model_inputs[model_name]

    scores = cross_validate(
        model,
        X_model,
        y_model,
        cv=cv,
        scoring=scoring,
        return_train_score=False
    )

    cv_results_rows.append({
        "model": model_name,
        "accuracy_mean": scores["test_accuracy"].mean(),
        "accuracy_std": scores["test_accuracy"].std(),
        "macro_f1_mean": scores["test_macro_f1"].mean(),
        "macro_f1_std": scores["test_macro_f1"].std(),
        "weighted_f1_mean": scores["test_weighted_f1"].mean(),
        "weighted_f1_std": scores["test_weighted_f1"].std()
    })

cv_results = pd.DataFrame(cv_results_rows).round(4)

display(cv_results)

# ---

# ============================================================
# PASO 21. EXPORTAR RESULTADOS DE CROSS-VALIDATION
# ============================================================

output_cv = "cross_validation_social_debt_models.xlsx"

cv_results.to_excel(output_cv, index=False)

print("Archivo exportado:", output_cv)
print("Dimensiones:", cv_results.shape)

# ---

# ============================================================
# PASO 22. IMPORTANCIA PROMEDIO DE VARIABLES
# Random Forest con validación cruzada
# ============================================================

from sklearn.model_selection import StratifiedKFold
from sklearn.ensemble import RandomForestClassifier
import pandas as pd
import numpy as np

cv = StratifiedKFold(
    n_splits=5,
    shuffle=True,
    random_state=42
)

feature_importance_rows = []

for fold, (train_idx, test_idx) in enumerate(cv.split(X_struct, y_struct), start=1):

    X_train_fold = X_struct.iloc[train_idx]
    X_test_fold = X_struct.iloc[test_idx]
    y_train_fold = y_struct.iloc[train_idx]
    y_test_fold = y_struct.iloc[test_idx]

    rf_fold = RandomForestClassifier(
        n_estimators=300,
        max_depth=None,
        class_weight="balanced",
        random_state=42
    )

    rf_fold.fit(X_train_fold, y_train_fold)

    for feature, importance in zip(structured_features, rf_fold.feature_importances_):
        feature_importance_rows.append({
            "fold": fold,
            "feature": feature,
            "importance": importance
        })

feature_importance_cv = pd.DataFrame(feature_importance_rows)

feature_importance_summary = (
    feature_importance_cv
    .groupby("feature")
    .agg(
        mean_importance=("importance", "mean"),
        std_importance=("importance", "std")
    )
    .sort_values("mean_importance", ascending=False)
    .round(4)
    .reset_index()
)

display(feature_importance_summary)

# ---

# ============================================================
# PASO 23. SBERT + LOGISTIC REGRESSION
# Objetivo: predecir social_debt_level desde issue_text
# ============================================================

from sentence_transformers import SentenceTransformer
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, f1_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
import pandas as pd
import numpy as np

# -----------------------------
# 1. Definir X e y
# -----------------------------
X_text = df_issue_adaptive["issue_text"].astype(str).tolist()
y_sbert = df_issue_adaptive["social_debt_level"]

# -----------------------------
# 2. Cargar modelo SBERT
# -----------------------------
sbert_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

# -----------------------------
# 3. Generar embeddings
# -----------------------------
X_sbert = sbert_model.encode(
    X_text,
    show_progress_bar=True,
    normalize_embeddings=True
)

print("Dimensiones embeddings:", X_sbert.shape)

# ---

# ============================================================
# PASO 24. SBERT + LOGISTIC REGRESSION
# Validación cruzada estratificada
# ============================================================

from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
import pandas as pd

cv = StratifiedKFold(
    n_splits=5,
    shuffle=True,
    random_state=42
)

sbert_lr_model = Pipeline([
    (
        "scaler",
        StandardScaler()
    ),
    (
        "clf",
        LogisticRegression(
            max_iter=2000,
            class_weight="balanced",
            random_state=42
        )
    )
])

scoring = {
    "accuracy": "accuracy",
    "macro_f1": "f1_macro",
    "weighted_f1": "f1_weighted"
}

scores_sbert_lr = cross_validate(
    sbert_lr_model,
    X_sbert,
    y_sbert,
    cv=cv,
    scoring=scoring,
    return_train_score=False
)

sbert_lr_results = pd.DataFrame([{
    "model": "SBERT + Logistic Regression",
    "input_type": "Issue text embeddings",
    "accuracy_mean": scores_sbert_lr["test_accuracy"].mean(),
    "accuracy_std": scores_sbert_lr["test_accuracy"].std(),
    "macro_f1_mean": scores_sbert_lr["test_macro_f1"].mean(),
    "macro_f1_std": scores_sbert_lr["test_macro_f1"].std(),
    "weighted_f1_mean": scores_sbert_lr["test_weighted_f1"].mean(),
    "weighted_f1_std": scores_sbert_lr["test_weighted_f1"].std()
}]).round(4)

display(sbert_lr_results)

# ---

# ============================================================
# PASO 25. TABLA FINAL COMPARATIVA CON SBERT
# ============================================================

final_model_results = pd.DataFrame([
    {
        "model": "TF-IDF + Logistic Regression",
        "input_type": "Issue text",
        "accuracy_mean": cv_results.loc[
            cv_results["model"] == "TF-IDF + Logistic Regression",
            "accuracy_mean"
        ].values[0],
        "macro_f1_mean": cv_results.loc[
            cv_results["model"] == "TF-IDF + Logistic Regression",
            "macro_f1_mean"
        ].values[0],
        "weighted_f1_mean": cv_results.loc[
            cv_results["model"] == "TF-IDF + Logistic Regression",
            "weighted_f1_mean"
        ].values[0]
    },
    {
        "model": "TF-IDF + Linear SVM",
        "input_type": "Issue text",
        "accuracy_mean": cv_results.loc[
            cv_results["model"] == "TF-IDF + Linear SVM",
            "accuracy_mean"
        ].values[0],
        "macro_f1_mean": cv_results.loc[
            cv_results["model"] == "TF-IDF + Linear SVM",
            "macro_f1_mean"
        ].values[0],
        "weighted_f1_mean": cv_results.loc[
            cv_results["model"] == "TF-IDF + Linear SVM",
            "weighted_f1_mean"
        ].values[0]
    },
    {
        "model": "SBERT + Logistic Regression",
        "input_type": "Issue text embeddings",
        "accuracy_mean": sbert_lr_results["accuracy_mean"].values[0],
        "macro_f1_mean": sbert_lr_results["macro_f1_mean"].values[0],
        "weighted_f1_mean": sbert_lr_results["weighted_f1_mean"].values[0]
    },
    {
        "model": "Random Forest + Adaptive Features",
        "input_type": "Adaptive structured features",
        "accuracy_mean": cv_results.loc[
            cv_results["model"] == "Random Forest + Adaptive Features",
            "accuracy_mean"
        ].values[0],
        "macro_f1_mean": cv_results.loc[
            cv_results["model"] == "Random Forest + Adaptive Features",
            "macro_f1_mean"
        ].values[0],
        "weighted_f1_mean": cv_results.loc[
            cv_results["model"] == "Random Forest + Adaptive Features",
            "weighted_f1_mean"
        ].values[0]
    }
])

final_model_results = final_model_results.round(4)

display(final_model_results)

# ---

# =========================================================================
# PASO 26. COMPARACIÓN DE VARIOS MODELOS SBERT
# Objetivo: comparar embeddings semánticos para predecir social_debt_level
# =========================================================================

from sentence_transformers import SentenceTransformer
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
import pandas as pd

# -----------------------------
# 1. Datos
# -----------------------------
X_text = df_issue_adaptive["issue_text"].astype(str).tolist()
y_embed = df_issue_adaptive["social_debt_level"]

# -----------------------------
# 2. Validación cruzada
# -----------------------------
cv = StratifiedKFold(
    n_splits=5,
    shuffle=True,
    random_state=42
)

scoring = {
    "accuracy": "accuracy",
    "macro_f1": "f1_macro",
    "weighted_f1": "f1_weighted"
}

# -----------------------------
# 3. Modelos de embeddings a comparar
# -----------------------------
embedding_models = [
    "paraphrase-multilingual-MiniLM-L12-v2",
    "all-MiniLM-L6-v2",
    "all-mpnet-base-v2",
    "multi-qa-mpnet-base-dot-v1"
]

embedding_results = []

# -----------------------------
# 4. Evaluar cada modelo
# -----------------------------
for model_name in embedding_models:

    print("\n======================================")
    print("Modelo de embeddings:", model_name)
    print("======================================")

    emb_model = SentenceTransformer(model_name)

    X_emb = emb_model.encode(
        X_text,
        show_progress_bar=True,
        normalize_embeddings=True
    )

    clf = Pipeline([
        ("scaler", StandardScaler()),
        (
            "clf",
            LogisticRegression(
                max_iter=2000,
                class_weight="balanced",
                random_state=42
            )
        )
    ])

    scores = cross_validate(
        clf,
        X_emb,
        y_embed,
        cv=cv,
        scoring=scoring,
        return_train_score=False
    )

    embedding_results.append({
        "embedding_model": model_name,
        "accuracy_mean": scores["test_accuracy"].mean(),
        "accuracy_std": scores["test_accuracy"].std(),
        "macro_f1_mean": scores["test_macro_f1"].mean(),
        "macro_f1_std": scores["test_macro_f1"].std(),
        "weighted_f1_mean": scores["test_weighted_f1"].mean(),
        "weighted_f1_std": scores["test_weighted_f1"].std(),
        "embedding_dim": X_emb.shape[1]
    })

embedding_results_df = (
    pd.DataFrame(embedding_results)
    .sort_values("macro_f1_mean", ascending=False)
    .round(4)
)

display(embedding_results_df)

# ---

# ============================================================
# PASO 27. TABLA FINAL COMPARATIVA DE TODOS LOS MODELOS
# ============================================================

best_embedding_row = (
    embedding_results_df
    .sort_values("macro_f1_mean", ascending=False)
    .iloc[0]
)

final_model_results = pd.DataFrame([
    {
        "model": "TF-IDF + Logistic Regression",
        "input_type": "Issue text",
        "accuracy_mean": cv_results.loc[
            cv_results["model"] == "TF-IDF + Logistic Regression",
            "accuracy_mean"
        ].values[0],
        "macro_f1_mean": cv_results.loc[
            cv_results["model"] == "TF-IDF + Logistic Regression",
            "macro_f1_mean"
        ].values[0],
        "weighted_f1_mean": cv_results.loc[
            cv_results["model"] == "TF-IDF + Logistic Regression",
            "weighted_f1_mean"
        ].values[0]
    },
    {
        "model": "TF-IDF + Linear SVM",
        "input_type": "Issue text",
        "accuracy_mean": cv_results.loc[
            cv_results["model"] == "TF-IDF + Linear SVM",
            "accuracy_mean"
        ].values[0],
        "macro_f1_mean": cv_results.loc[
            cv_results["model"] == "TF-IDF + Linear SVM",
            "macro_f1_mean"
        ].values[0],
        "weighted_f1_mean": cv_results.loc[
            cv_results["model"] == "TF-IDF + Linear SVM",
            "weighted_f1_mean"
        ].values[0]
    },
    {
        "model": f"Best SBERT ({best_embedding_row['embedding_model']})",
        "input_type": "Issue text embeddings",
        "accuracy_mean": best_embedding_row["accuracy_mean"],
        "macro_f1_mean": best_embedding_row["macro_f1_mean"],
        "weighted_f1_mean": best_embedding_row["weighted_f1_mean"]
    },
    {
        "model": "Random Forest + Adaptive Features",
        "input_type": "Adaptive structured features",
        "accuracy_mean": cv_results.loc[
            cv_results["model"] == "Random Forest + Adaptive Features",
            "accuracy_mean"
        ].values[0],
        "macro_f1_mean": cv_results.loc[
            cv_results["model"] == "Random Forest + Adaptive Features",
            "macro_f1_mean"
        ].values[0],
        "weighted_f1_mean": cv_results.loc[
            cv_results["model"] == "Random Forest + Adaptive Features",
            "weighted_f1_mean"
        ].values[0]
    }
])

final_model_results = (
    final_model_results
    .sort_values("macro_f1_mean", ascending=False)
    .round(4)
)

display(final_model_results)

# ---

# ============================================================
# PASO 28. EXPORTAR COMPARACIÓN FINAL DE MODELOS
# ============================================================

output_final_models = "final_model_comparison_social_debt.xlsx"

final_model_results.to_excel(output_final_models, index=False)

print("Archivo exportado:", output_final_models)
print("Dimensiones:", final_model_results.shape)

# ---

# ============================================================
# PASO 29. RESUMEN INTERPRETATIVO POR NIVEL DE DEUDA SOCIAL
# ============================================================

# Tomamos los principales hallazgos que ya calculamos:
# summary_profile
# macrocauses_by_level
# microcauses_by_level
# smells_by_level
# risks_by_level

def top_items_as_text(df_source, level_col, item_col, value_col, level, top_n=3):
    subset = (
        df_source[df_source[level_col] == level]
        .sort_values(value_col, ascending=False)
        .head(top_n)
    )
    return "; ".join(
        [
            f"{row[item_col]} ({round(row[value_col], 3)})"
            for _, row in subset.iterrows()
        ]
    )

rows = []

for level in ["Low Social Debt", "Medium Social Debt", "High Social Debt"]:

    profile = summary_profile[
        summary_profile["social_debt_level"] == level
    ].iloc[0]

    rows.append({
        "social_debt_level": level,
        "issue_count": profile["issue_count"],
        "mean_sdi": profile["mean_sdi"],
        "mean_comments": profile["mean_comments"],
        "mean_macro_diversity": profile["mean_macro_diversity"],
        "top_macrocauses": top_items_as_text(
            macrocauses_by_level,
            "social_debt_level",
            "macrocause",
            "frequency",
            level,
            top_n=3
        ),
        "top_microcauses": top_items_as_text(
            microcauses_by_level,
            "social_debt_level",
            "microcause",
            "aggregated_score",
            level,
            top_n=3
        ),
        "top_community_smells": top_items_as_text(
            smells_by_level,
            "social_debt_level",
            "community_smell",
            "frequency",
            level,
            top_n=3
        ),
        "top_risks": top_items_as_text(
            risks_by_level,
            "social_debt_level",
            "risk",
            "frequency",
            level,
            top_n=3
        )
    })

adaptive_level_summary = pd.DataFrame(rows)

display(adaptive_level_summary)

# ---

# ============================================================
# PASO 30. DIAGNÓSTICO ADAPTATIVO BÁSICO POR ISSUE
# ============================================================

def get_top_name(x):
    """
    Extrae el nombre del primer elemento de una lista tipo:
    [('Missing Link', 9), ('Power Distance', 4)]
    """
    if isinstance(x, list) and len(x) > 0:
        return x[0][0]
    return None

def get_top_value(x):
    """
    Extrae el valor del primer elemento de una lista tipo:
    [('Missing Link', 9), ('Power Distance', 4)]
    """
    if isinstance(x, list) and len(x) > 0:
        return x[0][1]
    return None

df_issue_diagnosis = df_issue_adaptive.copy()

# -----------------------------
# 1. Extraer elementos dominantes
# -----------------------------
df_issue_diagnosis["dominant_macrocause"] = (
    df_issue_diagnosis["dominant_macrocauses"].apply(get_top_name)
)

df_issue_diagnosis["dominant_macrocause_frequency"] = (
    df_issue_diagnosis["dominant_macrocauses"].apply(get_top_value)
)

df_issue_diagnosis["dominant_microcause"] = (
    df_issue_diagnosis["dominant_microcauses"].apply(get_top_name)
)

df_issue_diagnosis["dominant_microcause_score"] = (
    df_issue_diagnosis["dominant_microcauses"].apply(get_top_value)
)

df_issue_diagnosis["dominant_community_smell"] = (
    df_issue_diagnosis["dominant_community_smells"].apply(get_top_name)
)

df_issue_diagnosis["dominant_community_smell_frequency"] = (
    df_issue_diagnosis["dominant_community_smells"].apply(get_top_value)
)

df_issue_diagnosis["dominant_risk"] = (
    df_issue_diagnosis["dominant_risks"].apply(get_top_name)
)

df_issue_diagnosis["dominant_risk_frequency"] = (
    df_issue_diagnosis["dominant_risks"].apply(get_top_value)
)

# -----------------------------
# 2. Seleccionar columnas de diagnóstico
# -----------------------------
diagnosis_cols = [
    "issue_number",
    "social_debt_index",
    "social_debt_level",
    "comment_count",
    "dominant_macrocause",
    "dominant_macrocause_frequency",
    "dominant_microcause",
    "dominant_microcause_score",
    "dominant_community_smell",
    "dominant_community_smell_frequency",
    "dominant_risk",
    "dominant_risk_frequency"
]

adaptive_issue_diagnosis = (
    df_issue_diagnosis[diagnosis_cols]
    .sort_values("social_debt_index", ascending=False)
)

display(adaptive_issue_diagnosis.head(20))

# ---

# ============================================================
# PASO 32. DIAGNÓSTICO ADAPTATIVO EN COLUMNAS INDIVIDUALES
# Top-3 macrocausas, microcausas, smells y riesgos
# ============================================================

def extract_item_name(x, position):
    """
    Extrae el nombre del elemento en una posición específica.
    position = 0 para el primero, 1 para el segundo, 2 para el tercero.
    """
    if isinstance(x, list) and len(x) > position:
        return x[position][0]
    return None

def extract_item_value(x, position):
    """
    Extrae el valor del elemento en una posición específica.
    """
    if isinstance(x, list) and len(x) > position:
        return x[position][1]
    return None

df_issue_diagnosis_expanded = df_issue_adaptive.copy()

# -----------------------------
# 1. Macrocausas top-3
# -----------------------------
for i in range(3):
    df_issue_diagnosis_expanded[f"macrocause_{i+1}"] = (
        df_issue_diagnosis_expanded["dominant_macrocauses"]
        .apply(lambda x: extract_item_name(x, i))
    )
    df_issue_diagnosis_expanded[f"macrocause_{i+1}_frequency"] = (
        df_issue_diagnosis_expanded["dominant_macrocauses"]
        .apply(lambda x: extract_item_value(x, i))
    )

# -----------------------------
# 2. Microcausas top-3
# -----------------------------
for i in range(3):
    df_issue_diagnosis_expanded[f"microcause_{i+1}"] = (
        df_issue_diagnosis_expanded["dominant_microcauses"]
        .apply(lambda x: extract_item_name(x, i))
    )
    df_issue_diagnosis_expanded[f"microcause_{i+1}_score"] = (
        df_issue_diagnosis_expanded["dominant_microcauses"]
        .apply(lambda x: extract_item_value(x, i))
    )

# -----------------------------
# 3. Community smells top-3
# -----------------------------
for i in range(3):
    df_issue_diagnosis_expanded[f"community_smell_{i+1}"] = (
        df_issue_diagnosis_expanded["dominant_community_smells"]
        .apply(lambda x: extract_item_name(x, i))
    )
    df_issue_diagnosis_expanded[f"community_smell_{i+1}_frequency"] = (
        df_issue_diagnosis_expanded["dominant_community_smells"]
        .apply(lambda x: extract_item_value(x, i))
    )

# -----------------------------
# 4. Riesgos top-3
# -----------------------------
for i in range(3):
    df_issue_diagnosis_expanded[f"risk_{i+1}"] = (
        df_issue_diagnosis_expanded["dominant_risks"]
        .apply(lambda x: extract_item_name(x, i))
    )
    df_issue_diagnosis_expanded[f"risk_{i+1}_frequency"] = (
        df_issue_diagnosis_expanded["dominant_risks"]
        .apply(lambda x: extract_item_value(x, i))
    )

# -----------------------------
# 5. Seleccionar columnas finales de diagnóstico
# -----------------------------
expanded_diagnosis_cols = [
    "issue_number",
    "social_debt_index",
    "social_debt_level",
    "comment_count",

    "macrocause_1",
    "macrocause_1_frequency",
    "macrocause_2",
    "macrocause_2_frequency",
    "macrocause_3",
    "macrocause_3_frequency",

    "microcause_1",
    "microcause_1_score",
    "microcause_2",
    "microcause_2_score",
    "microcause_3",
    "microcause_3_score",

    "community_smell_1",
    "community_smell_1_frequency",
    "community_smell_2",
    "community_smell_2_frequency",
    "community_smell_3",
    "community_smell_3_frequency",

    "risk_1",
    "risk_1_frequency",
    "risk_2",
    "risk_2_frequency",
    "risk_3",
    "risk_3_frequency"
]

adaptive_issue_diagnosis_expanded = (
    df_issue_diagnosis_expanded[expanded_diagnosis_cols]
    .sort_values("social_debt_index", ascending=False)
)

display(adaptive_issue_diagnosis_expanded.head(20))

# ---

display(
    adaptive_issue_diagnosis_expanded[
        [
            "issue_number",
            "social_debt_index",
            "social_debt_level",
            "microcause_1",
            "microcause_1_score",
            "microcause_2",
            "microcause_2_score",
            "microcause_3",
            "microcause_3_score"
        ]
    ].head(20)
)

# ---

# ============================================================
# PASO 33. VERIFICAR COLUMNAS DE ESTRATEGIAS EN EL DATASET
# ============================================================

strategy_cols = [
    col for col in df.columns
    if "strateg" in col.lower()
]

print(strategy_cols)

display(
    df[
        [
            "issue_number",
            "primary_microcause_name",
            "preventive_strategies",
            "corrective_strategies"
        ]
    ].head(10)
)

# ---

# ============================================================
# PASO 34. AGREGAR ESTRATEGIAS PREVENTIVAS Y CORRECTIVAS POR ISSUE
# ============================================================

from collections import Counter
import pandas as pd

def parse_strategy_cell(value):
    """
    Convierte una celda tipo:
    • PS-004_InterfaceClarificationWorkshops
    • PS-017_TimelyFeedbackMechanism

    en una lista:
    ['PS-004_InterfaceClarificationWorkshops', 'PS-017_TimelyFeedbackMechanism']
    """
    if pd.isna(value):
        return []

    items = []
    for line in str(value).split("\n"):
        line = line.strip()
        line = line.replace("•", "").strip()
        if line:
            items.append(line)
    return items


# -----------------------------
# 1. Parsear estrategias
# -----------------------------
df["preventive_strategies_list"] = (
    df["preventive_strategies"]
    .apply(parse_strategy_cell)
)

df["corrective_strategies_list"] = (
    df["corrective_strategies"]
    .apply(parse_strategy_cell)
)


# -----------------------------
# 2. Agregar estrategias por issue
# -----------------------------
strategy_rows = []

for issue_number, group in df.groupby("issue_number"):

    preventive_counter = Counter()
    corrective_counter = Counter()

    for _, row in group.iterrows():

        for strategy in row["preventive_strategies_list"]:
            preventive_counter[strategy] += 1

        for strategy in row["corrective_strategies_list"]:
            corrective_counter[strategy] += 1

    strategy_rows.append({
        "issue_number": issue_number,
        "top_preventive_strategies": preventive_counter.most_common(3),
        "top_corrective_strategies": corrective_counter.most_common(3)
    })

issue_strategies = pd.DataFrame(strategy_rows)

display(issue_strategies.head(10))

# ---

# ============================================================
# PASO 35. UNIR DIAGNÓSTICO ADAPTATIVO CON ESTRATEGIAS
# ============================================================

adaptive_issue_diagnosis_final = adaptive_issue_diagnosis_expanded.merge(
    issue_strategies,
    on="issue_number",
    how="left"
)

display(
    adaptive_issue_diagnosis_final
    .sort_values("social_debt_index", ascending=False)
    .head(20)
)

print("Dimensiones diagnóstico final:", adaptive_issue_diagnosis_final.shape)

# ---

# ============================================================
# PASO 36. EXPANDIR ESTRATEGIAS EN COLUMNAS INDIVIDUALES
# ============================================================

def extract_strategy_name(x, position):
    if isinstance(x, list) and len(x) > position:
        return x[position][0]
    return None

def extract_strategy_value(x, position):
    if isinstance(x, list) and len(x) > position:
        return x[position][1]
    return None

df_final_diagnosis_expanded = adaptive_issue_diagnosis_final.copy()

# -----------------------------
# 1. Estrategias preventivas top-3
# -----------------------------
for i in range(3):
    df_final_diagnosis_expanded[f"preventive_strategy_{i+1}"] = (
        df_final_diagnosis_expanded["top_preventive_strategies"]
        .apply(lambda x: extract_strategy_name(x, i))
    )
    df_final_diagnosis_expanded[f"preventive_strategy_{i+1}_frequency"] = (
        df_final_diagnosis_expanded["top_preventive_strategies"]
        .apply(lambda x: extract_strategy_value(x, i))
    )

# -----------------------------
# 2. Estrategias correctivas top-3
# -----------------------------
for i in range(3):
    df_final_diagnosis_expanded[f"corrective_strategy_{i+1}"] = (
        df_final_diagnosis_expanded["top_corrective_strategies"]
        .apply(lambda x: extract_strategy_name(x, i))
    )
    df_final_diagnosis_expanded[f"corrective_strategy_{i+1}_frequency"] = (
        df_final_diagnosis_expanded["top_corrective_strategies"]
        .apply(lambda x: extract_strategy_value(x, i))
    )

# -----------------------------
# 3. Eliminar columnas tipo lista si quieres una tabla limpia
# -----------------------------
df_final_diagnosis_clean = df_final_diagnosis_expanded.drop(
    columns=[
        "top_preventive_strategies",
        "top_corrective_strategies"
    ]
)

display(df_final_diagnosis_clean.head(20))

print("Dimensiones diagnóstico limpio:", df_final_diagnosis_clean.shape)

# ---

# ============================================================
# PASO 37. EXPORTAR DIAGNÓSTICO ADAPTATIVO FINAL
# ============================================================

output_diagnosis = "adaptive_social_debt_diagnosis_final.xlsx"

df_final_diagnosis_clean.to_excel(output_diagnosis, index=False)

print("Archivo exportado:", output_diagnosis)
print("Dimensiones:", df_final_diagnosis_clean.shape)

# ---

# ============================================================
# PASO 38. FUNCIÓN PARA CONSULTAR DIAGNÓSTICO DE UN ISSUE
# ============================================================

def diagnose_issue(issue_number, diagnosis_df=df_final_diagnosis_clean):
    """
    Consulta el diagnóstico adaptativo de un issue específico.
    Devuelve nivel de deuda social, causas, smells, riesgos y estrategias.
    """

    result = diagnosis_df[
        diagnosis_df["issue_number"] == issue_number
    ]

    if result.empty:
        print(f"No se encontró el issue {issue_number} en el diagnóstico final.")
        return None

    row = result.iloc[0]

    print("====================================================")
    print(f"DIAGNÓSTICO ADAPTATIVO DEL ISSUE {issue_number}")
    print("====================================================")

    print("\n1. Nivel de deuda social")
    print("----------------------------------------------------")
    print("Social Debt Index:", round(row["social_debt_index"], 4))
    print("Nivel:", row["social_debt_level"])
    print("Cantidad de comentarios:", row["comment_count"])

    print("\n2. Macrocausas principales")
    print("----------------------------------------------------")
    for i in range(1, 4):
        cause = row.get(f"macrocause_{i}")
        freq = row.get(f"macrocause_{i}_frequency")
        if pd.notna(cause):
            print(f"{i}. {cause} ({freq})")

    print("\n3. Microcausas principales")
    print("----------------------------------------------------")
    for i in range(1, 4):
        cause = row.get(f"microcause_{i}")
        score = row.get(f"microcause_{i}_score")
        if pd.notna(cause):
            print(f"{i}. {cause} (score acumulado: {round(score, 3)})")

    print("\n4. Community smells principales")
    print("----------------------------------------------------")
    for i in range(1, 4):
        smell = row.get(f"community_smell_{i}")
        freq = row.get(f"community_smell_{i}_frequency")
        if pd.notna(smell):
            print(f"{i}. {smell} ({freq})")

    print("\n5. Riesgos principales")
    print("----------------------------------------------------")
    for i in range(1, 4):
        risk = row.get(f"risk_{i}")
        freq = row.get(f"risk_{i}_frequency")
        if pd.notna(risk):
            print(f"{i}. {risk} ({freq})")

    print("\n6. Estrategias preventivas recomendadas")
    print("----------------------------------------------------")
    for i in range(1, 4):
        strategy = row.get(f"preventive_strategy_{i}")
        freq = row.get(f"preventive_strategy_{i}_frequency")
        if pd.notna(strategy):
            print(f"{i}. {strategy} ({freq})")

    print("\n7. Estrategias correctivas recomendadas")
    print("----------------------------------------------------")
    for i in range(1, 4):
        strategy = row.get(f"corrective_strategy_{i}")
        freq = row.get(f"corrective_strategy_{i}_frequency")
        if pd.notna(strategy):
            print(f"{i}. {strategy} ({freq})")

    return row

# ---

diagnose_issue(60423)

# ---

# ============================================================
# PASO 40. INTERPRETACIÓN AUTOMÁTICA MEJORADA EN ESPAÑOL
# ============================================================

def translate_social_debt_level(level):
    mapping = {
        "High Social Debt": "alta deuda social",
        "Medium Social Debt": "deuda social media",
        "Low Social Debt": "baja deuda social"
    }
    return mapping.get(level, level)


def generate_issue_report(issue_number, diagnosis_df=df_final_diagnosis_clean):
    """
    Genera un reporte interpretativo en español para un issue específico.
    """

    result = diagnosis_df[
        diagnosis_df["issue_number"] == issue_number
    ]

    if result.empty:
        return f"No se encontró el issue {issue_number} en el diagnóstico final."

    row = result.iloc[0]

    level_es = translate_social_debt_level(row["social_debt_level"])

    report = f"""
El issue {issue_number} presenta un nivel de {level_es}, con un Social Debt Index de {round(row['social_debt_index'], 3)} y {int(row['comment_count'])} comentarios analizados.

El diagnóstico adaptativo indica que las principales macrocausas asociadas al issue son: {row['macrocause_1']}, {row['macrocause_2']} y {row['macrocause_3']}. Estas macrocausas sugieren que la deuda social del issue se relaciona con una combinación de factores técnicos, comunicativos y organizacionales.

A nivel de microcausas, las señales más relevantes son: {row['microcause_1']}, {row['microcause_2']} y {row['microcause_3']}. Esto permite identificar con mayor precisión los factores específicos que explican la acumulación de deuda social en el issue.

Los community smells dominantes son: {row['community_smell_1']}, {row['community_smell_2']} y {row['community_smell_3']}. Estos patrones indican posibles desconexiones entre actores, tareas, decisiones y dependencias técnicas dentro de la comunidad de desarrollo.

Los principales riesgos asociados son: {row['risk_1']}, {row['risk_2']} y {row['risk_3']}. Por tanto, el issue puede derivar en problemas de documentación, mantenimiento, compatibilidad, retrabajo o pérdida de coordinación, según las evidencias observadas.

Como estrategias preventivas, el modelo recomienda priorizar: {row['preventive_strategy_1']}, {row['preventive_strategy_2']} y {row['preventive_strategy_3']}. Estas estrategias buscan reducir la probabilidad de que las causas identificadas se repitan o se intensifiquen.

Como estrategias correctivas, el modelo recomienda considerar: {row['corrective_strategy_1']}, {row['corrective_strategy_2']} y {row['corrective_strategy_3']}. Estas acciones están orientadas a mitigar los efectos ya presentes y apoyar la recuperación del issue.

En síntesis, el issue {issue_number} evidencia una acumulación de señales sociotécnicas que justifican una intervención adaptativa. El diagnóstico integra causas, community smells, riesgos y estrategias, permitiendo pasar de una clasificación de deuda social a una recomendación accionable.
"""

    return report.strip()


# Probar con el issue más crítico
print(generate_issue_report(60423))

# ---

# ============================================================
# PASO 39. GENERAR INTERPRETACIÓN AUTOMÁTICA DEL DIAGNÓSTICO
# ============================================================

def generate_issue_interpretation(issue_number, diagnosis_df=df_final_diagnosis_clean):
    """
    Genera una interpretación textual automática del diagnóstico adaptativo.
    """

    result = diagnosis_df[
        diagnosis_df["issue_number"] == issue_number
    ]

    if result.empty:
        return f"No se encontró el issue {issue_number} en el diagnóstico final."

    row = result.iloc[0]

    text = f"""
El issue {issue_number} presenta un nivel de {row['social_debt_level']} con un Social Debt Index de {round(row['social_debt_index'], 3)} y {int(row['comment_count'])} comentarios analizados.

El diagnóstico indica que las principales macrocausas asociadas al issue son:
1) {row['macrocause_1']},
2) {row['macrocause_2']}, y
3) {row['macrocause_3']}.

A nivel de microcausas, las señales más fuertes son:
1) {row['microcause_1']},
2) {row['microcause_2']}, y
3) {row['microcause_3']}.

Los community smells dominantes son:
1) {row['community_smell_1']},
2) {row['community_smell_2']}, y
3) {row['community_smell_3']}.

Los principales riesgos asociados son:
1) {row['risk_1']},
2) {row['risk_2']}, y
3) {row['risk_3']}.

Como estrategias preventivas, el modelo recomienda priorizar:
1) {row['preventive_strategy_1']},
2) {row['preventive_strategy_2']}, y
3) {row['preventive_strategy_3']}.

Como estrategias correctivas, el modelo recomienda considerar:
1) {row['corrective_strategy_1']},
2) {row['corrective_strategy_2']}, y
3) {row['corrective_strategy_3']}.

En síntesis, este issue refleja una acumulación de deuda social asociada con problemas sociotécnicos recurrentes, donde las causas, smells, riesgos y estrategias sugieren la necesidad de intervención adaptativa tanto preventiva como correctiva.
"""

    return text.strip()


# Probar con el issue más crítico
print(generate_issue_interpretation(60423))

# ---

# ============================================================
# PASO 41. GENERAR REPORTE AUTOMÁTICO PARA TODOS LOS ISSUES
# ============================================================

df_final_diagnosis_clean["adaptive_diagnosis_report"] = (
    df_final_diagnosis_clean["issue_number"]
    .apply(lambda issue: generate_issue_report(issue))
)

display(
    df_final_diagnosis_clean[
        [
            "issue_number",
            "social_debt_index",
            "social_debt_level",
            "adaptive_diagnosis_report"
        ]
    ].head(10)
)

print("Dimensiones con reporte textual:", df_final_diagnosis_clean.shape)

# ---

# ============================================================
# PASO 42. EXPORTAR DIAGNÓSTICO FINAL CON REPORTE TEXTUAL
# ============================================================

output_final_report = "adaptive_social_debt_diagnosis_final_with_report.xlsx"

df_final_diagnosis_clean.to_excel(output_final_report, index=False)

print("Archivo exportado:", output_final_report)
print("Dimensiones:", df_final_diagnosis_clean.shape)