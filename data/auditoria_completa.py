#!/usr/bin/env python3
"""
=============================================================================
AUDITORÍA COMPLETA DE PARIDAD — Social Debt API Model
=============================================================================
Compara paso a paso los archivos de referencia del Colab contra los archivos
de auditoría generados por la API (con detección dinámica de carpetas y archivos).

Uso:
    python3 auditoria_completa.py
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

# ── Directorio donde se encuentra el script ──────────────────────────────────
BASE = os.path.dirname(os.path.abspath(__file__))

# ── Helpers de impresión ──────────────────────────────────────────────────────
def header(title: str):
    w = 70
    print()
    print(BOLD + CYAN + "=" * w + RESET)
    print(BOLD + CYAN + f"  {title}" + RESET)
    print(BOLD + CYAN + "=" * w + RESET)

def ok(msg: str):    print(f"  {GREEN}[OK]  {msg}{RESET}")
def fail(msg: str):  print(f"  {RED}[FAIL]  {msg}{RESET}")
def warn(msg: str):  print(f"  {YELLOW}[WARN]  {msg}{RESET}")
def info(msg: str):  print(f"     {msg}")
def section(t: str): print(f"\n  {BOLD}── {t} ──{RESET}")

def find_step_files(step_num: int):
    subdirs = [d for d in os.listdir(BASE) if os.path.isdir(os.path.join(BASE, d))]
    step_dir_name = None
    for d in subdirs:
        if str(step_num) in d.lower() and "paso" in d.lower():
            step_dir_name = d
            break
            
    if not step_dir_name:
        step_dir_name = f"paso {step_num}"
        
    full_step_dir = os.path.join(BASE, step_dir_name)
    if not os.path.exists(full_step_dir):
        print(f"\n{RED}ERROR: Directorio para el paso {step_num} no encontrado → {full_step_dir}{RESET}")
        sys.exit(1)
        
    files = [f for f in os.listdir(full_step_dir) if f.endswith(".xlsx") and not f.startswith("~$")]
    
    if len(files) != 2:
        print(f"\n{RED}ERROR: No se puede ejecutar. Se esperaban exactamente 2 archivos Excel en '{step_dir_name}', pero se encontraron {len(files)}. No es claro cuál archivo es cuál.{RESET}")
        sys.exit(1)
        
    api_file, colab_file = None, None
    for f in files:
        lf = f.lower()
        if "auditoria" in lf and str(step_num) in lf:
            api_file = f
            break
            
    if not api_file:
        for f in files:
            if "auditoria" in f.lower():
                api_file = f
                break
                
    for f in files:
        if f != api_file:
            colab_file = f
            break
            
    if not api_file or not colab_file:
        print(f"\n{RED}ERROR: No se pudo distinguir claramente el archivo de auditoría y el de referencia en '{step_dir_name}'.{RESET}")
        sys.exit(1)
        
    return os.path.join(step_dir_name, colab_file), os.path.join(step_dir_name, api_file)

def load(relpath: str, sheet: str = None) -> pd.DataFrame:
    full = os.path.join(BASE, relpath)
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
def audit_paso1():
    header("PASO 1 · Limpieza de Texto — Comparación carácter a carácter")
    c_file, a_file = find_step_files(1)

    colab = load(c_file)
    api   = load(a_file)

    section("Conteo de filas")
    info(f"Colab ({os.path.basename(c_file)}): {len(colab)} filas  |  API ({os.path.basename(a_file)}): {len(api)} filas")

    merged = pd.merge(
        colab[["comment_id", "comment_body_clean_final"]].rename(
            columns={"comment_body_clean_final": "texto_colab"}),
        api[["comment_id", "cleaned_text"]].rename(
            columns={"cleaned_text": "texto_api"}),
        on="comment_id", how="inner"
    )

    section(f"Comparación de texto limpiado ({len(merged)} comentarios en común)")

    diffs = []
    matches = 0
    total = len(merged)

    for _, row in merged.iterrows():
        tc = nan_to_str(row["texto_colab"])
        ta = nan_to_str(row["texto_api"])
        if tc == ta:
            matches += 1
        else:
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
        ok(f"PARIDAD PERFECTA — {total} textos idénticos carácter a carácter")
    else:
        fail(f"{len(diffs)} de {total} textos difieren")
        for d in diffs[:10]:
            info(f"  comment_id={d['comment_id']}  primera diferencia en posición {d['char_pos']}")
            info(f"    Colab: {repr(d['colab'][:80])}")
            info(f"    API  : {repr(d['api'][:80])}")
        if len(diffs) > 10:
            info(f"  … y {len(diffs)-10} más.")

    pct = (matches / total * 100) if total > 0 else 0.0
    return matches, total, pct


# =============================================================================
# PASO 2 — Detección de Ruido
# =============================================================================
def audit_paso2():
    header("PASO 2 · Detección de Ruido")
    c_file, a_file = find_step_files(2)

    colab = load(c_file)
    api   = load(a_file)

    section("Conteo de filas")
    info(f"Colab ({os.path.basename(c_file)}) (solo comentarios LIMPIOS): {len(colab)} filas")
    info(f"API ({os.path.basename(a_file)}) (todos los comentarios):      {len(api)} filas")

    api_clean = api[api["is_noise"] == False]
    info(f"API (is_noise=False):             {len(api_clean)} filas")

    section("Verificación de comment_ids (Colab vs API limpios)")

    colab_ids     = set(colab["comment_id"].astype(str))
    api_clean_ids = set(api_clean["comment_id"].astype(str))
    
    total = len(colab_ids)
    common_ids = colab_ids.intersection(api_clean_ids)
    matches = len(common_ids)
    
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

    pct = (matches / total * 100) if total > 0 else 0.0
    return matches, total, pct


# =============================================================================
# PASO 3 — Clasificación de Macrocausa
# =============================================================================
def audit_paso3():
    header("PASO 3 · Clasificación de Macrocausa — Comparación por comment_id")
    c_file, a_file = find_step_files(3)

    colab = load(c_file)
    api   = load(a_file)

    api_clean = api[api["is_noise"] == False]

    section("Conteo de filas")
    info(f"Colab ({os.path.basename(c_file)}): {len(colab)} filas  |  API ({os.path.basename(a_file)}) (sin ruido): {len(api_clean)} filas")

    merged = pd.merge(
        colab[["comment_id", "final_cause_code"]].rename(
            columns={"final_cause_code": "code_colab"}),
        api_clean[["comment_id", "macro_cause_code"]].rename(
            columns={"macro_cause_code": "code_api"}),
        on="comment_id", how="inner"
    )

    total = len(merged)
    section(f"Comparación de código de macrocausa ({total} comentarios en común)")

    diffs = merged[merged["code_colab"].astype(str) != merged["code_api"].astype(str)]
    matches = total - len(diffs)

    if diffs.empty:
        ok(f"PARIDAD PERFECTA — {total} macrocódigos idénticos")
    else:
        fail(f"{len(diffs)} de {total} comentarios con macrocausa diferente:")
        for _, row in diffs.iterrows():
            info(f"  comment_id={row['comment_id']}  "
                 f"Colab={row['code_colab']}  API={row['code_api']}")

    pct = (matches / total * 100) if total > 0 else 0.0
    return matches, total, pct


# =============================================================================
# PASO 4 — Integración Semántica (Microcausas)
# =============================================================================
def audit_paso4():
    header("PASO 4 · Integración Semántica — Microcausas (nombre, orden y score)")
    c_file, a_file = find_step_files(4)

    colab = load(c_file)
    api   = load(a_file)

    api_clean = api[api["is_noise"] == False].sort_values(
        ["issue_number", "comment_id"]).reset_index(drop=True)
    colab_s = colab.sort_values(
        ["issue_number", "comment_id"]).reset_index(drop=True)

    section("Conteo de filas")
    info(f"Colab ({os.path.basename(c_file)}): {len(colab_s)} filas  |  API ({os.path.basename(a_file)}) (sin ruido): {len(api_clean)} filas")

    section("Comparación microcausas 1, 2 y 3 (nombre + score, tolerancia ±0.0001)")

    SCORE_TOL  = 1e-4
    name_diffs = []
    score_diffs= []
    perfect    = 0
    total = len(colab_s)

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
        if score_diffs:
            fail(f"{len(score_diffs)} discrepancias de SCORE:")
            for d in score_diffs[:15]:
                info(f"  comment_id={d['comment_id']} (issue {d['issue_number']}) "
                     f"· microcausa {d['k']}")
                info(f"    Colab={d['colab_score']}  API={d['api_score']}  "
                     f"diff={d['diff']:.6f}")

    pct = (perfect / total * 100) if total > 0 else 0.0
    return perfect, total, pct


# =============================================================================
# PASO 5 — SDI (Social Debt Index y Nivel) con Tolerancia del 5% (±5 unidades)
# =============================================================================
def audit_paso5():
    header("PASO 5 · Social Debt Index — Comparación de métricas por issue (Tolerancia 5%)")
    c_file, a_file = find_step_files(5)

    colab = load(c_file)
    api   = load(a_file, sheet="Metricas SDI")

    section("Conteo de issues")
    info(f"Colab ({os.path.basename(c_file)}): {len(colab)} issues  |  API ({os.path.basename(a_file)}): {len(api)} issues")

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

    section(f"Tabla comparativa ({len(common)} issues en común) · Tolerancia SDI ±5.0 (5%)")

    SDI_EXACT_TOL = 1e-4
    SDI_SIMILAR_TOL = 5.0

    print()
    print(f"  {'issue_number':>12}  {'SDI Colab':>14}  {'SDI API':>14}  "
          f"{'Diferencia':>12}  {'Nivel Colab':>22}  {'Nivel API':>22}  {'Estado':>10}")
    print("  " + "-" * 114)

    exact_count = 0
    similar_count = 0
    total = len(common)

    for _, row in common.sort_values("sdi_colab", ascending=False).iterrows():
        sdi_c = float(row["sdi_colab"])
        sdi_a = float(row["sdi_api"])
        lvl_c = nan_to_str(row["lvl_colab"])
        lvl_a = nan_to_str(row["lvl_api"])
        diff  = sdi_a - sdi_c

        is_exact = abs(diff) <= SDI_EXACT_TOL and lvl_c == lvl_a
        is_similar = abs(diff) <= SDI_SIMILAR_TOL and lvl_c == lvl_a

        if is_exact:
            exact_count += 1
            status = f"{GREEN}[EXACTO]{RESET}"
        elif is_similar:
            similar_count += 1
            status = f"{YELLOW}[SIMILAR]{RESET}"
        else:
            status = f"{RED}[DISCREP]{RESET}"

        diff_str = f"{diff:+.6f}"
        print(f"  {int(row['issue_number']):>12}  {sdi_c:>14.6f}  {sdi_a:>14.6f}  "
              f"{diff_str:>12}  {lvl_c:>22}  {lvl_a:>22}  {status}")

    matches = similar_count + exact_count
    print()
    info(f"Exactos: {exact_count} | Similares: {similar_count} | Diferentes: {total - matches} | Total aciertos: {matches} de {total}")
    pct = (matches / total * 100) if total > 0 else 0.0
    return matches, total, pct


# =============================================================================
# PUNTO DE ENTRADA
# =============================================================================
def main():
    print()
    print(BOLD + "═" * 70 + RESET)
    print(BOLD + "  AUDITORÍA DE PARIDAD — Social Debt API Model Pipeline" + RESET)
    print(BOLD + "═" * 70 + RESET)

    r1_match, r1_tot, r1_pct = audit_paso1()
    r2_match, r2_tot, r2_pct = audit_paso2()
    r3_match, r3_tot, r3_pct = audit_paso3()
    r4_match, r4_tot, r4_pct = audit_paso4()
    r5_match, r5_tot, r5_pct = audit_paso5()

    header("RESUMEN FINAL")
    
    print(f"  Paso 1 (Limpieza texto):     {r1_pct:.1f}% ({r1_match}/{r1_tot})")
    print(f"  Paso 2 (Detección ruido):    {r2_pct:.1f}% ({r2_match}/{r2_tot})")
    print(f"  Paso 3 (Macrocausa LLM):     {r3_pct:.1f}% ({r3_match}/{r3_tot})")
    print(f"  Paso 4 (Microcausas NLP):    {r4_pct:.1f}% ({r4_match}/{r4_tot})")
    print(f"  Paso 5 (SDI y nivel):        {r5_pct:.1f}% ({r5_match}/{r5_tot})")

    print()
    overall_avg = (r1_pct + r2_pct + r3_pct + r4_pct + r5_pct) / 5.0
    print(f"  {BOLD}Similitud Promedio del Pipeline: {overall_avg:.1f}%{RESET}")
    print()


if __name__ == "__main__":
    main()