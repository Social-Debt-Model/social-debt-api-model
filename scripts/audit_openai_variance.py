import pandas as pd
import asyncio
import time
from collections import Counter
from sklearn.preprocessing import MinMaxScaler
import json
import sys
import os

# Asegurar que Python pueda encontrar la carpeta "app"
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# API imports
from app.use_cases.preprocessing.cleaning import clean_comment_text
from app.use_cases.preprocessing.noise_filtering import es_hard_noise, es_operational_noise
from app.use_cases.classification.llm_classifier import predict_macro_cause
from app.use_cases.semantic.ontology_matcher import classify_specific_causes_topk
from app.infrastructure.ontology_client import enrich_microcause
from app.use_cases.metrics.social_debt_index import calculate_batch_sdi

async def process_comment_notebook(text):
    cleaned = clean_comment_text(text)
    is_noise = es_hard_noise(cleaned) or es_operational_noise(cleaned)
    if is_noise:
        return {"macro": "H", "microcauses": [], "is_noise": True, "cleaned_text": cleaned}
        
    macro, _ = await predict_macro_cause(cleaned)
    microcauses = []
    
    is_noise = (macro == "H")
    if not is_noise:
        macro_label = macro
        if macro == "A": macro_label = "Communication and shared understanding breakdowns"
        elif macro == "B": macro_label = "Coordination and workflow misalignment"
        elif macro == "C": macro_label = "Technical complexity, compatibility, and system constraints"
        elif macro == "D": macro_label = "Organizational and procedural workflow constraints"
        elif macro == "E": macro_label = "Collaboration and interpersonal tensions"
        elif macro == "F": macro_label = "Knowledge, documentation, and standards deficiencies"
        elif macro == "G": macro_label = "Resource, tooling, access, and validation dependencies"
        
        top_k_res = classify_specific_causes_topk(macro_label, cleaned)
        for m in top_k_res.get("top_candidates", []):
            enriched = enrich_microcause(m.get("ontology_id"))
            microcauses.append({
                "cause_name": m.get("specific_cause_name"),
                "similarity": float(m["final_score"]),
                "community_smells": enriched.get("community_smells", []),
                "risks": enriched.get("risks", [])
            })
    return {"macro": macro, "microcauses": microcauses, "is_noise": is_noise, "cleaned_text": cleaned}

async def process_comment_api(text):
    # Ya verificamos antes que la API usa exactamente las mismas funciones bajo el capó.
    # Correrlo dos veces nos da la varianza pura de OpenAI.
    return await process_comment_notebook(text)

async def bounded_process(sem, text, func):
    async with sem:
        return await func(text)

async def run_e2e():
    print("Cargando dataset de 1000 comentarios...")
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(BASE_DIR, 'data/dataset_test_1000.csv')
    df = pd.read_csv(csv_path)
    
    print(f"Procesando {len(df)} comentarios a través de OpenAI (Esto tomará unos minutos)...")
    
    sem = asyncio.Semaphore(50) # Chunk size de 50
    
    api_data = {}
    notebook_data = {}
    
    tasks_api = []
    tasks_not = []
    
    for _, row in df.iterrows():
        text = str(row['comment_body_raw'])
        tasks_api.append(bounded_process(sem, text, process_comment_api))
        tasks_not.append(bounded_process(sem, text, process_comment_notebook))
        
    print("Enviando peticiones a OpenAI (Notebook logic)...")
    res_not_list = await asyncio.gather(*tasks_not)
    print("Enviando peticiones a OpenAI (API logic)...")
    res_api_list = await asyncio.gather(*tasks_api)
    print("Todas las peticiones completadas.")
    
    # Estructura del reporte
    report = {
        "resumen_general": {},
        "analisis_comentarios": [],
        "analisis_issues": []
    }
    
    total_macros_iguales = 0
    total_valid_comments = 0
    
    for idx, (_, row) in enumerate(df.iterrows()):
        i_id = str(row['issue_number'])
        c_id = str(row.get('comment_id', idx))
        
        if i_id not in api_data:
            api_data[i_id] = []
            notebook_data[i_id] = []
            
        r_api = res_api_list[idx]
        r_not = res_not_list[idx]
        
        api_data[i_id].append({
            "code": r_api["macro"],
            "is_noise": r_api["is_noise"],
            "cleaned_text": r_api["cleaned_text"],
            "microcauses": r_api["microcauses"]
        })
        
        notebook_data[i_id].append({
            "code": r_not["macro"],
            "is_noise": r_not["is_noise"],
            "cleaned_text": r_not["cleaned_text"],
            "microcauses": r_not["microcauses"]
        })
        
        if not r_api["is_noise"] and not r_not["is_noise"]:
            total_valid_comments += 1
            if r_api["macro"] == r_not["macro"]:
                total_macros_iguales += 1
                
        # Guardar en el reporte a nivel comentario
        report["analisis_comentarios"].append({
            "issue_id": i_id,
            "comment_id": c_id,
            "cleaned_text": r_not["cleaned_text"],
            "notebook_macro": r_not["macro"],
            "api_macro": r_api["macro"],
            "macro_coincide": r_not["macro"] == r_api["macro"],
            "notebook_microcauses": [m["cause_name"] for m in r_not["microcauses"]],
            "api_microcauses": [m["cause_name"] for m in r_api["microcauses"]]
        })

    print("\nCalculando métricas SDI (API PIPELINE)...")
    sdi_api_results = calculate_batch_sdi(api_data)
    
    print("Calculando métricas SDI (NOTEBOOK PIPELINE)...")
    def count_items(x): return len(x) if isinstance(x, list) else 0
    def top_frequency(x): return x[0][1] if isinstance(x, list) and len(x) > 0 else 0
    def top_score(x): return x[0][1] if isinstance(x, list) and len(x) > 0 else 0

    rows = []
    for i_id, comments in notebook_data.items():
        for c in comments:
            micro_names = [m["cause_name"] for m in c["microcauses"]]
            micro_scores = [m["similarity"] for m in c["microcauses"]]
            smells, risks = [], []
            for m in c["microcauses"]:
                smells.extend(m.get("community_smells", []))
                risks.extend(m.get("risks", []))
            
            rows.append({
                "issue_number": i_id,
                "final_cause_for_analysis": c["code"],
                "top_microcause_names_list": micro_names,
                "top_microcause_scores_list": micro_scores,
                "community_smells_list": smells,
                "risks_list": risks,
                "comment_body_clean_final": c["cleaned_text"]
            })
            
    df_notebook = pd.DataFrame(rows)
    
    def aggregate_issue(group):
        micro_counter = Counter()
        smell_counter = Counter()
        risk_counter = Counter()
        macro_counter = Counter()
        for _, row in group.iterrows():
            macro_counter[row["final_cause_for_analysis"]] += 1
            for name, score in zip(row["top_microcause_names_list"], row["top_microcause_scores_list"]):
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
            "dominant_risks": risk_counter.most_common(5)
        })
        
    df_notebook_agg = df_notebook.groupby("issue_number").apply(aggregate_issue, include_groups=False).reset_index()
    
    df_notebook_agg["macro_diversity"] = df_notebook_agg["dominant_macrocauses"].apply(count_items)
    df_notebook_agg["micro_diversity"] = df_notebook_agg["dominant_microcauses"].apply(count_items)
    df_notebook_agg["smell_diversity"] = df_notebook_agg["dominant_community_smells"].apply(count_items)
    df_notebook_agg["risk_diversity"] = df_notebook_agg["dominant_risks"].apply(count_items)
    df_notebook_agg["top_macro_frequency"] = df_notebook_agg["dominant_macrocauses"].apply(top_frequency)
    df_notebook_agg["top_micro_score"] = df_notebook_agg["dominant_microcauses"].apply(top_score)
    df_notebook_agg["top_smell_frequency"] = df_notebook_agg["dominant_community_smells"].apply(top_frequency)
    df_notebook_agg["top_risk_frequency"] = df_notebook_agg["dominant_risks"].apply(top_frequency)
    
    sdi_features = ["comment_count", "macro_diversity", "micro_diversity", "smell_diversity", "risk_diversity", "top_macro_frequency", "top_micro_score", "top_smell_frequency", "top_risk_frequency"]
    scaler = MinMaxScaler()
    normalized_values = scaler.fit_transform(df_notebook_agg[sdi_features])
    df_sdi_norm = pd.DataFrame(normalized_values, columns=[f"{col}_norm" for col in sdi_features])
    df_notebook_agg = pd.concat([df_notebook_agg.reset_index(drop=True), df_sdi_norm], axis=1)
    
    sdi_variables = ["comment_count_norm", "macro_diversity_norm", "top_macro_frequency_norm", "top_micro_score_norm", "top_smell_frequency_norm", "top_risk_frequency_norm"]
    df_notebook_agg["social_debt_index"] = df_notebook_agg[sdi_variables].mean(axis=1)

    sdi_notebook_results = {}
    for _, row in df_notebook_agg.iterrows():
        sdi_notebook_results[str(row["issue_number"])] = {
            "social_debt_index": float(row["social_debt_index"])
        }
        for k in sdi_features:
            sdi_notebook_results[str(row["issue_number"])][k] = row[k]
        sdi_notebook_results[str(row["issue_number"])]["dominant_macrocauses"] = row["dominant_macrocauses"]
        sdi_notebook_results[str(row["issue_number"])]["dominant_microcauses"] = row["dominant_microcauses"]

    # Agregar auditoría nivel Issue
    diferencias_sdi = []
    
    for i_id in sdi_notebook_results.keys():
        if i_id not in sdi_api_results:
            continue
        api_res = sdi_api_results[i_id]
        not_res = sdi_notebook_results[i_id]
        
        diff = abs(api_res['social_debt_index'] - not_res['social_debt_index'])
        diferencias_sdi.append(diff)
        
        report["analisis_issues"].append({
            "issue_id": i_id,
            "notebook_sdi": not_res['social_debt_index'],
            "api_sdi": api_res['social_debt_index'],
            "sdi_diferencia_absoluta": diff,
            "notebook_top_macros": not_res['dominant_macrocauses'],
            "api_top_macros": api_res.get('details', {}).get('macro_diversity', []),
            "notebook_top_micros": not_res['dominant_microcauses'],
            "api_top_micros": api_res.get('details', {}).get('micro_diversity', [])
        })
        
    avg_sdi_diff = sum(diferencias_sdi) / len(diferencias_sdi) if diferencias_sdi else 0
    macro_match_rate = (total_macros_iguales / total_valid_comments * 100) if total_valid_comments > 0 else 100
    
    report["resumen_general"] = {
        "total_comentarios_procesados": len(df),
        "total_issues_procesados": len(sdi_notebook_results),
        "tasa_coincidencia_macrocausas_openai": f"{macro_match_rate:.2f}%",
        "desviacion_promedio_sdi": f"{avg_sdi_diff:.6f}",
        "explicacion": "La tasa de coincidencia mide qué tan determinista fue OpenAI al correr el mismo prompt dos veces. La desviación SDI mide cuánto afectó esa varianza al puntaje matemático final."
    }
    
    with open("reporte_varianza_exhaustivo.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        
    print("\n================================================")
    print("=== REPORTE DE VARIANZA EXHAUSTIVO GENERADO  ===")
    print("================================================\n")
    print(f"Comentarios procesados: {len(df)}")
    print(f"Tasa de consistencia OpenAI (Misma Macrocausa 2 veces): {macro_match_rate:.2f}%")
    print(f"Desviación promedio en Índice SDI final: {avg_sdi_diff:.6f}")
    print("\nRevisa el archivo 'reporte_varianza_exhaustivo.json' para ver la comparación comentario por comentario.")
    
if __name__ == "__main__":
    asyncio.run(run_e2e())
