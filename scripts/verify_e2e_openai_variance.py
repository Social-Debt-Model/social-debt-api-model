import pandas as pd
import asyncio
import time
from collections import Counter
from sklearn.preprocessing import MinMaxScaler
import json

# API imports
from app.use_cases.classification.llm_classifier import predict_macro_cause
from app.use_cases.semantic.ontology_matcher import classify_specific_causes_topk
from app.infrastructure.ontology_client import enrich_microcause
from app.use_cases.metrics.social_debt_index import calculate_batch_sdi

async def process_comment_notebook(text):
    macro, _ = await predict_macro_cause(text)
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
        
        top_k_res = classify_specific_causes_topk(macro_label, text)
        for m in top_k_res.get("top_candidates", []):
            enriched = enrich_microcause(m.get("ontology_id"))
            microcauses.append({
                "cause_name": m.get("specific_cause_name"),
                "similarity": float(m["final_score"]),
                "community_smells": enriched.get("community_smells", []),
                "risks": enriched.get("risks", [])
            })
    return {"macro": macro, "microcauses": microcauses, "is_noise": is_noise}

async def process_comment_api(text):
    return await process_comment_notebook(text)

async def bounded_process(sem, text, func):
    async with sem:
        return await func(text)

async def run_e2e():
    print("Cargando dataset...")
    df = pd.read_excel('Modelo_adaptativo_deuda_social_julio/4. Integracion_semantica/Dataset_salida/Dataset_integration_semantico_original_con_H.xlsx')
    top_2_issues = [60423, 18056]
    df_top2 = df[df['issue_number'].isin(top_2_issues)]
    
    print(f"Procesando {len(df_top2)} comentarios a través de OpenAI (Esto tomará unos minutos)...")
    
    sem = asyncio.Semaphore(5)
    
    api_data = {60423: [], 18056: []}
    notebook_data = {60423: [], 18056: []}
    
    tasks_api = []
    tasks_not = []
    
    for _, row in df_top2.iterrows():
        text = str(row['comment_body_clean_final'])
        tasks_api.append(bounded_process(sem, text, process_comment_api))
        tasks_not.append(bounded_process(sem, text, process_comment_notebook))
        
    print("Enviando peticiones asíncronas a OpenAI...")
    res_api_list = await asyncio.gather(*tasks_api)
    print("Mitad completada...")
    res_not_list = await asyncio.gather(*tasks_not)
    print("Todas las peticiones completadas.")
    
    for idx, (_, row) in enumerate(df_top2.iterrows()):
        i_id = row['issue_number']
        text = str(row['comment_body_clean_final'])
        
        api_data[i_id].append({
            "code": res_api_list[idx]["macro"],
            "is_noise": res_api_list[idx]["is_noise"],
            "cleaned_text": text,
            "microcauses": res_api_list[idx]["microcauses"]
        })
        
        notebook_data[i_id].append({
            "code": res_not_list[idx]["macro"],
            "is_noise": res_not_list[idx]["is_noise"],
            "cleaned_text": text,
            "microcauses": res_not_list[idx]["microcauses"]
        })

    sdi_api_results = calculate_batch_sdi(api_data)
    
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
        
    print("\n================================================")
    print("=== RESULTADOS COMPARATIVOS E2E (CON OPENAI) ===")
    print("================================================\n")
    
    for i_id in [str(60423), str(18056)]:
        print(f"--- ISSUE {i_id} ---")
        api_res = sdi_api_results[i_id]
        not_res = sdi_notebook_results[i_id]
        
        print(f"1. ÍNDICE DE DEUDA SOCIAL (SDI):")
        print(f"   API:      {api_res['social_debt_index']:.6f}")
        print(f"   Notebook: {not_res['social_debt_index']:.6f}")
        print(f"   Diferencia Absoluta: {abs(api_res['social_debt_index'] - not_res['social_debt_index']):.6f}")
        
        print(f"\n2. MÉTRICAS BASE:")
        print(f"   [API]      Macro Diversity: {api_res['macro_diversity']} | Micro Diversity: {api_res['micro_diversity']} | Smell Diversity: {api_res['smell_diversity']}")
        print(f"   [Notebook] Macro Diversity: {not_res['macro_diversity']} | Micro Diversity: {not_res['micro_diversity']} | Smell Diversity: {not_res['smell_diversity']}")
        
        print(f"\n   [API]      Top Macro Freq: {api_res['top_macro_frequency']} | Top Micro Score: {api_res['top_micro_score']:.2f}")
        print(f"   [Notebook] Top Macro Freq: {not_res['top_macro_frequency']} | Top Micro Score: {not_res['top_micro_score']:.2f}")

        print(f"\n   [API]      Top Smell Freq: {api_res['top_smell_frequency']} | Top Risk Freq: {api_res['top_risk_frequency']}")
        print(f"   [Notebook] Top Smell Freq: {not_res['top_smell_frequency']} | Top Risk Freq: {not_res['top_risk_frequency']}")
        print("------------------------------------------------\n")
        
if __name__ == "__main__":
    asyncio.run(run_e2e())
