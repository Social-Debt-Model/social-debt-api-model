#!/usr/bin/env python3
"""
=============================================================================
AUDITORÍA COMPLETA DE PARIDAD — Social Debt API Model
=============================================================================
Compara paso a paso los archivos de referencia del Colab contra los archivos
de auditoría generados por la API.

Uso:
    cd /ruta/del/repo
    python3 data/auditoria_completa.py

Archivos esperados:
  Paso 1: data/paso 1/dataset_clean_final.xlsx
          data/paso 1/dataset_prueba_cliente_auditoria_paso1.xlsx
  Paso 2: data/paso 2/dataset_limpio_final.xlsx
          data/paso 2/dataset_prueba_cliente_auditoria_paso2.xlsx
  Paso 3: data/paso 3/dataset_mapeo.xlsx
          data/paso 3/dataset_prueba_cliente_auditoria_paso3.xlsx
  Paso 4: data/paso 4/Dataset_integration_semantico_topk_enriched_final.xlsx
          data/paso 4/dataset_prueba_cliente_auditoria_paso4.xlsx
  Paso 5: data/paso 5/adaptive_social_debt_diagnosis_final.xlsx
          data/paso 5/dataset_prueba_cliente_auditoria_paso5.xlsx
=============================================================================
"""

import os
import sys
import math
import pandas as pd

# ── Colores ANSI ──────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

# ── Directorio raíz: un nivel arriba de /data ─────────────────────────────────
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── Helpers de impresión ──────────────────────────────────────────────────────
def header(title: str):
    w = 70
    print()
    print(BOLD + CYAN + "=" * w + RESET)
    print(BOLD + CYAN + f"  {title}" + RESET)
    print(BOLD + CYAN + "=" * w + RESET)

def ok(msg: str):    print(f"  {GREEN}✔  {msg}{RESET}")
def fail(msg: str):  print(f"  {RED}✘  {msg}{RESET}")
def warn(msg: str):  print(f"  {YELLOW}⚠  {msg}{RESET}")
def info(msg: str):  print(f"     {msg}")
def section(t: str): print(f"\n  {BOLD}── {t} ──{RESET}")

def load(relpath: str, sheet: str = None) -> pd.DataFrame:
    full = os.path.join(BASE, "data", relpath)
    if not os.path.exists(full):
        print(f"\n{RED}ERROR: archivo no encontrado → {full}{RESET}")
        sys.exit(1)
    return pd.read_excel(full, sheet_name=sheet) if sheet else pd.read_excel(full)

def nan_to_str(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and math.isnan(v):
        return ""
    return str(v).strip()

def float_close(a, b, tol=1e-4) -> bool:
    def to_f(x):
        try:
            f = float(x)
            return None if math.isnan(f) else f
        except (ValueError, TypeError):
            return None
    fa, fb = to_f(a), to_f(b)
    if fa is None and fb is None:
        return True
    if fa is None or fb is None:
        return False
    return abs(fa - fb) <= tol


# =============================================================================
# PASO 1 — Limpieza de texto (carácter a carácter)
# =============================================================================
def audit_paso1() -> bool:
    header("PASO 1 · Limpieza de Texto — Comparación carácter a carácter")

    colab = load("paso 1/dataset_clean_final.xlsx")
    api   = load("paso 1/dataset_prueba_cliente_auditoria_paso1.xlsx")

    section("Conteo de filas")
    info(f"Colab: {len(colab)} filas  |  API: {len(api)} filas")
    if len(colab) == len(api):
        ok("Mismo número de filas")
    else:
        warn(f"Diferente número de filas")

    merged = pd.merge(
        colab[["comment_id", "comment_body_clean_final"]].rename(
            columns={"comment_body_clean_final": "texto_colab"}),
        api[["comment_id", "cleaned_text"]].rename(
            columns={"cleaned_text": "texto_api"}),
        on="comment_id", how="inner"
    )

    section(f"Comparación de texto limpiado ({len(merged)} comentarios en común)")

    diffs = []
    for _, row in merged.iterrows():
        tc = nan_to_str(row["texto_colab"])
        ta = nan_to_str(row["texto_api"])
        if tc != ta:
            first_diff = next(
                (i for i, (a, b) in enumerate(zip(tc, ta)) if a != b),
                min(len(tc), len(ta))
            )
            diffs.append({
                "comment_id": row["comment_id"],
                "char_pos"  : first_diff,
                "colab"     : tc[:100],
                "api"       : ta[:100],
            })

    if not diffs:
        ok(f"PARIDAD PERFECTA — {len(merged)} textos idénticos carácter a carácter")
    else:
        fail(f"{len(diffs)} de {len(merged)} textos difieren")
        for d in diffs[:10]:
            info(f"  comment_id={d['comment_id']}  primera diferencia en posición {d['char_pos']}")
            info(f"    Colab: {repr(d['colab'][:80])}")
            info(f"    API  : {repr(d['api'][:80])}")
        if len(diffs) > 10:
            info(f"  … y {len(diffs)-10} más.")

    return len(diffs) == 0


# =============================================================================
# PASO 2 — Detección de Ruido
# =============================================================================
def audit_paso2() -> bool:
    header("PASO 2 · Detección de Ruido")

    colab = load("paso 2/dataset_limpio_final.xlsx")
    api   = load("paso 2/dataset_prueba_cliente_auditoria_paso2.xlsx")

    section("Conteo de filas")
    info(f"Colab (solo comentarios LIMPIOS): {len(colab)} filas")
    info(f"API (todos los comentarios):      {len(api)} filas")

    api_clean = api[api["is_noise"] == False]
    info(f"API (is_noise=False):             {len(api_clean)} filas")

    if len(colab) == len(api_clean):
        ok("Mismo número de comentarios limpios")
    else:
        fail(f"Diferente número de limpios (Colab={len(colab)}, API={len(api_clean)})")

    section("Verificación de comment_ids (Colab vs API limpios)")

    colab_ids     = set(colab["comment_id"].astype(str))
    api_clean_ids = set(api_clean["comment_id"].astype(str))
    solo_colab = colab_ids - api_clean_ids
    solo_api   = api_clean_ids - colab_ids

    if not solo_colab and not solo_api:
        ok("Todos los comment_ids del Colab coinciden en la API como comentarios limpios")
    else:
        if solo_colab:
            fail(f"{len(solo_colab)} comment_ids del Colab NO están en la API como limpios:")
            for cid in list(solo_colab)[:10]:
                info(f"    {cid}")
        if solo_api:
            warn(f"{len(solo_api)} comment_ids de la API (limpios) extra (no estaban en Colab):")
            for cid in list(solo_api)[:10]:
                info(f"    {cid}")

    section("Distribución de ruido (API)")
    for lvl, cnt in api["noise_level"].value_counts().items():
        info(f"  {lvl}: {cnt}")

    return len(solo_colab) == 0 and len(solo_api) == 0


# =============================================================================
# PASO 3 — Clasificación de Macrocausa
# =============================================================================
def audit_paso3() -> bool:
    header("PASO 3 · Clasificación de Macrocausa — Comparación por comment_id")

    colab = load("paso 3/dataset_mapeo.xlsx")
    api   = load("paso 3/dataset_prueba_cliente_auditoria_paso3.xlsx")

    api_clean = api[api["is_noise"] == False]

    section("Conteo de filas")
    info(f"Colab: {len(colab)} filas  |  API (sin ruido): {len(api_clean)} filas")

    merged = pd.merge(
        colab[["comment_id", "final_cause_code"]].rename(
            columns={"final_cause_code": "code_colab"}),
        api_clean[["comment_id", "macro_cause_code"]].rename(
            columns={"macro_cause_code": "code_api"}),
        on="comment_id", how="inner"
    )

    section(f"Comparación de código de macrocausa ({len(merged)} comentarios en común)")

    diffs = merged[merged["code_colab"].astype(str) != merged["code_api"].astype(str)]

    if diffs.empty:
        ok(f"PARIDAD PERFECTA — {len(merged)} macrocódigos idénticos")
    else:
        fail(f"{len(diffs)} de {len(merged)} comentarios con macrocausa diferente:")
        for _, row in diffs.iterrows():
            info(f"  comment_id={row['comment_id']}  "
                 f"Colab={row['code_colab']}  API={row['code_api']}")

    only_colab = set(colab["comment_id"].astype(str)) - set(api_clean["comment_id"].astype(str))
    only_api   = set(api_clean["comment_id"].astype(str)) - set(colab["comment_id"].astype(str))
    if only_colab:
        warn(f"{len(only_colab)} comment_ids del Colab no presentes en la API")
    if only_api:
        warn(f"{len(only_api)} comment_ids de la API no presentes en el Colab")

    return diffs.empty


# =============================================================================
# PASO 4 — Integración Semántica (Microcausas)
# =============================================================================
def audit_paso4() -> bool:
    header("PASO 4 · Integración Semántica — Microcausas (nombre, orden y score)")

    colab = load("paso 4/Dataset_integration_semantico_topk_enriched_final.xlsx")
    api   = load("paso 4/dataset_prueba_cliente_auditoria_paso4.xlsx")

    api_clean = api[api["is_noise"] == False].sort_values(
        ["issue_number", "comment_id"]).reset_index(drop=True)
    colab_s = colab.sort_values(
        ["issue_number", "comment_id"]).reset_index(drop=True)

    section("Conteo de filas")
    info(f"Colab: {len(colab_s)} filas  |  API (sin ruido): {len(api_clean)} filas")

    section("Verificación de comment_ids y orden")
    if len(colab_s) == len(api_clean):
        ids_match = (colab_s["comment_id"].astype(str) == api_clean["comment_id"].astype(str)).all()
        if ids_match:
            ok("Todos los comment_ids coinciden en el mismo orden")
        else:
            n = (colab_s["comment_id"].astype(str) != api_clean["comment_id"].astype(str)).sum()
            fail(f"{n} comment_ids no coinciden o están en diferente orden")
    else:
        warn("Diferente número de filas — verificación de orden omitida")

    section("Comparación microcausas 1, 2 y 3 (nombre + score, tolerancia ±0.0001)")

    SCORE_TOL  = 1e-4
    name_diffs = []
    score_diffs= []
    perfect    = 0

    for i, (c_row, a_row) in enumerate(zip(colab_s.itertuples(), api_clean.itertuples())):
        row_ok = True
        for k in range(1, 4):
            c_name  = nan_to_str(getattr(c_row, f"microcause_{k}_name",  None))
            a_name  = nan_to_str(getattr(a_row, f"microcause_{k}_name",  None))
            c_score = getattr(c_row, f"microcause_{k}_score",       None)
            a_score = getattr(a_row, f"microcause_{k}_similarity",  None)

            if c_name != a_name:
                row_ok = False
                name_diffs.append({
                    "comment_id"  : getattr(c_row, "comment_id", i),
                    "issue_number": getattr(c_row, "issue_number", "?"),
                    "k": k,
                    "colab_name": c_name,
                    "api_name"  : a_name,
                })

            if not float_close(c_score, a_score, SCORE_TOL):
                row_ok = False
                try:
                    diff_val = abs(float(c_score or 0) - float(a_score or 0))
                except (ValueError, TypeError):
                    diff_val = -1
                score_diffs.append({
                    "comment_id"  : getattr(c_row, "comment_id", i),
                    "issue_number": getattr(c_row, "issue_number", "?"),
                    "k"          : k,
                    "colab_score": c_score,
                    "api_score"  : a_score,
                    "diff"       : diff_val,
                })

        if row_ok:
            perfect += 1

    total = len(colab_s)
    if not name_diffs and not score_diffs:
        ok(f"PARIDAD PERFECTA — {total} comentarios con microcausas idénticas")
    else:
        ok(f"{perfect} de {total} comentarios perfectamente idénticos")
        if name_diffs:
            fail(f"{len(name_diffs)} discrepancias de NOMBRE:")
            for d in name_diffs[:15]:
                info(f"  comment_id={d['comment_id']} (issue {d['issue_number']}) "
                     f"· microcausa {d['k']}")
                info(f"    Colab: {d['colab_name']}")
                info(f"    API  : {d['api_name']}")
            if len(name_diffs) > 15:
                info(f"  … y {len(name_diffs)-15} más.")
        if score_diffs:
            fail(f"{len(score_diffs)} discrepancias de SCORE:")
            for d in score_diffs[:15]:
                info(f"  comment_id={d['comment_id']} (issue {d['issue_number']}) "
                     f"· microcausa {d['k']}")
                info(f"    Colab={d['colab_score']}  API={d['api_score']}  "
                     f"diff={d['diff']:.6f}")
            if len(score_diffs) > 15:
                info(f"  … y {len(score_diffs)-15} más.")

    return len(name_diffs) == 0 and len(score_diffs) == 0


# =============================================================================
# PASO 5 — SDI (Social Debt Index y Nivel)
# =============================================================================
def audit_paso5() -> bool:
    header("PASO 5 · Social Debt Index — Comparación de métricas por issue")

    colab = load("paso 5/adaptive_social_debt_diagnosis_final.xlsx")
    api   = load("paso 5/dataset_prueba_cliente_auditoria_paso5.xlsx",
                 sheet="Metricas SDI")

    section("Conteo de issues")
    info(f"Colab: {len(colab)} issues  |  API: {len(api)} issues")

    merged = pd.merge(
        colab[["issue_number", "social_debt_index", "social_debt_level"]].rename(
            columns={"social_debt_index": "sdi_colab", "social_debt_level": "lvl_colab"}),
        api[["issue_number", "social_debt_index", "social_debt_level"]].rename(
            columns={"social_debt_index": "sdi_api", "social_debt_level": "lvl_api"}),
        on="issue_number", how="outer"
    )

    only_colab = merged[merged["sdi_api"].isna()]
    only_api   = merged[merged["sdi_colab"].isna()]
    common     = merged.dropna(subset=["sdi_colab", "sdi_api"]).copy()

    if not only_colab.empty:
        warn(f"{len(only_colab)} issues en Colab no están en API: "
             f"{only_colab['issue_number'].tolist()}")
    if not only_api.empty:
        warn(f"{len(only_api)} issues en API no están en Colab: "
             f"{only_api['issue_number'].tolist()}")

    section(f"Tabla comparativa ({len(common)} issues en común) · tolerancia SDI ±0.0001")

    SDI_TOL = 1e-4

    print()
    print(f"  {'issue_number':>12}  {'SDI Colab':>14}  {'SDI API':>14}  "
          f"{'Diferencia':>12}  {'Nivel Colab':>22}  {'Nivel API':>22}  {'OK?':>4}")
    print("  " + "-" * 108)

    sdi_diffs   = []
    level_diffs = []
    perfect     = 0

    for _, row in common.sort_values("sdi_colab", ascending=False).iterrows():
        sdi_c = float(row["sdi_colab"])
        sdi_a = float(row["sdi_api"])
        lvl_c = nan_to_str(row["lvl_colab"])
        lvl_a = nan_to_str(row["lvl_api"])
        diff  = sdi_a - sdi_c

        sdi_ok   = abs(diff) <= SDI_TOL
        level_ok = lvl_c == lvl_a

        if sdi_ok and level_ok:
            perfect += 1
            status = f"{GREEN}✔{RESET}"
        else:
            status = f"{RED}✘{RESET}"

        diff_str = f"{diff:+.6f}"
        print(f"  {int(row['issue_number']):>12}  {sdi_c:>14.6f}  {sdi_a:>14.6f}  "
              f"{diff_str:>12}  {lvl_c:>22}  {lvl_a:>22}  {status}")

        if not sdi_ok:
            sdi_diffs.append(row["issue_number"])
        if not level_ok:
            level_diffs.append(row["issue_number"])

    print()
    if not sdi_diffs and not level_diffs:
        ok(f"PARIDAD PERFECTA — {perfect} issues con SDI y nivel idénticos")
    else:
        ok(f"{perfect} de {len(common)} issues perfectamente idénticos")
        if sdi_diffs:
            fail(f"Issues con SDI fuera de tolerancia: {sdi_diffs}")
        if level_diffs:
            fail(f"Issues con nivel diferente: {level_diffs}")

    return len(sdi_diffs) == 0 and len(level_diffs) == 0


# =============================================================================
# PUNTO DE ENTRADA
# =============================================================================
def main():
    print()
    print(BOLD + "═" * 70 + RESET)
    print(BOLD + "  AUDITORÍA DE PARIDAD — Social Debt API Model Pipeline" + RESET)
    print(BOLD + "═" * 70 + RESET)

    results = {
        "Paso 1 (Limpieza texto)": audit_paso1(),
        "Paso 2 (Detección ruido)": audit_paso2(),
        "Paso 3 (Macrocausa LLM)": audit_paso3(),
        "Paso 4 (Microcausas NLP)": audit_paso4(),
        "Paso 5 (SDI y nivel)":    audit_paso5(),
    }

    header("RESUMEN FINAL")
    all_ok = True
    for label, passed in results.items():
        if passed:
            print(f"  {GREEN}✔  {label}: PARIDAD PERFECTA{RESET}")
        else:
            print(f"  {RED}✘  {label}: CON DISCREPANCIAS{RESET}")
            all_ok = False

    print()
    if all_ok:
        print(f"  {BOLD}{GREEN}🏆  PIPELINE EN PARIDAD TOTAL CON COLAB  🏆{RESET}")
    else:
        print(f"  {BOLD}{YELLOW}  Revisa los pasos marcados en rojo arriba para más detalles.{RESET}")
    print()


if __name__ == "__main__":
    main()
