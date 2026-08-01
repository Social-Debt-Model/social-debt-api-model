import pandas as pd
from app.use_cases.semantic.ontology_matcher import classify_specific_causes_topk
from app.infrastructure.ontology_client import enrich_microcause
from app.use_cases.metrics.social_debt_index import calculate_batch_sdi
from sklearn.preprocessing import MinMaxScaler
from collections import Counter

def run_comparison():
    df = pd.read_excel('Modelo_adaptativo_deuda_social_julio/4. Integracion_semantica/Dataset_salida/Dataset_integration_semantico_original_con_H.xlsx')
    
    # 1. Encontrar los 2 issues con más comentarios
    issue_counts = df['issue_number'].value_counts()
    top_2_issues = issue_counts.head(2).index.tolist()
    
    print(f"Los 2 issues con más comentarios son: {top_2_issues}")
    print(f"Comentarios: Issue {top_2_issues[0]} ({issue_counts[top_2_issues[0]]}), Issue {top_2_issues[1]} ({issue_counts[top_2_issues[1]]})\n")
    
    df_top2 = df[df['issue_number'].isin(top_2_issues)]
    
    # ========================================================
    # EJECUCIÓN A TRAVÉS DE LA LÓGICA DE LA API
    # ========================================================
    print("--- 1. EJECUCIÓN VÍA PIPELINE DE LA API ---")
    issues_data_api = {top_2_issues[0]: [], top_2_issues[1]: []}
    
    for _, row in df_top2.iterrows():
        i_id = row['issue_number']
        code = row.get('final_cause_code', row.get('predicted_code', 'H'))
        if pd.isna(code): code = "H"
        text = str(row['comment_body_clean_final'])
        is_noise = (code == "H")
        
        microcauses = []
        if not is_noise:
            macro_label = code
            if code == "A": macro_label = "Communication and shared understanding breakdowns"
            elif code == "B": macro_label = "Coordination and workflow misalignment"
            elif code == "C": macro_label = "Technical complexity, compatibility, and system constraints"
            elif code == "D": macro_label = "Organizational and procedural workflow constraints"
            elif code == "E": macro_label = "Collaboration and interpersonal tensions"
            elif code == "F": macro_label = "Knowledge, documentation, and standards deficiencies"
            elif code == "G": macro_label = "Resource, tooling, access, and validation dependencies"
            
            # NLP Local Semántico de la API
            top_k_res = classify_specific_causes_topk(macro_label, text)
            for m in top_k_res.get("top_candidates", []):
                enriched = enrich_microcause(m.get("ontology_id"))
                microcauses.append({
                    "cause_name": m.get("specific_cause_name"),
                    "similarity": float(m["final_score"]),
                    "community_smells": enriched.get("community_smells", []),
                    "risks": enriched.get("risks", [])
                })
                
        issues_data_api[i_id].append({
            "code": code,
            "is_noise": is_noise,
            "cleaned_text": text,
            "microcauses": microcauses
        })
        
    sdi_api_results = calculate_batch_sdi(issues_data_api)
    print(f"SDI API Issue {top_2_issues[0]}: {sdi_api_results[str(top_2_issues[0])]['social_debt_index']:.6f}")
    print(f"SDI API Issue {top_2_issues[1]}: {sdi_api_results[str(top_2_issues[1])]['social_debt_index']:.6f}\n")
    
    # ========================================================
    # EJECUCIÓN A TRAVÉS DE LA LÓGICA DEL NOTEBOOK
    # ========================================================
    print("--- 2. EJECUCIÓN VÍA CÓDIGO CRUDO DEL NOTEBOOK DEL CLIENTE ---")
    
    def count_items(x): return len(x) if isinstance(x, list) else 0
    def top_value(x): return x[0][1] if isinstance(x, list) and len(x) > 0 else 0
    
    rows = []
    # Simulamos el DataFrame de salida del cuaderno semántico (Dataset_integration_semantico_topk_enriched_final.xlsx)
    for i_id, comments in issues_data_api.items():
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
    
    # Función exacta del Cuaderno 08
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
        
    df_notebook_agg = df_notebook.groupby("issue_number").apply(aggregate_issue).reset_index()
    
    df_notebook_agg["macro_diversity"] = df_notebook_agg["dominant_macrocauses"].apply(count_items)
    df_notebook_agg["micro_diversity"] = df_notebook_agg["dominant_microcauses"].apply(count_items)
    df_notebook_agg["smell_diversity"] = df_notebook_agg["dominant_community_smells"].apply(count_items)
    df_notebook_agg["risk_diversity"] = df_notebook_agg["dominant_risks"].apply(count_items)
    df_notebook_agg["top_macro_frequency"] = df_notebook_agg["dominant_macrocauses"].apply(top_value)
    df_notebook_agg["top_micro_score"] = df_notebook_agg["dominant_microcauses"].apply(top_value)
    df_notebook_agg["top_smell_frequency"] = df_notebook_agg["dominant_community_smells"].apply(top_value)
    df_notebook_agg["top_risk_frequency"] = df_notebook_agg["dominant_risks"].apply(top_value)
    
    sdi_features = ["comment_count", "macro_diversity", "micro_diversity", "smell_diversity", "risk_diversity", "top_macro_frequency", "top_micro_score", "top_smell_frequency", "top_risk_frequency"]
    scaler = MinMaxScaler()
    normalized_values = scaler.fit_transform(df_notebook_agg[sdi_features])
    df_sdi_norm = pd.DataFrame(normalized_values, columns=[f"{col}_norm" for col in sdi_features])
    
    df_notebook_agg = pd.concat([df_notebook_agg.reset_index(drop=True), df_sdi_norm], axis=1)
    
    sdi_variables = ["comment_count_norm", "macro_diversity_norm", "top_macro_frequency_norm", "top_micro_score_norm", "top_smell_frequency_norm", "top_risk_frequency_norm"]
    df_notebook_agg["social_debt_index"] = df_notebook_agg[sdi_variables].mean(axis=1)
    
    val_1 = df_notebook_agg[df_notebook_agg['issue_number'] == top_2_issues[0]]['social_debt_index'].values[0]
    val_2 = df_notebook_agg[df_notebook_agg['issue_number'] == top_2_issues[1]]['social_debt_index'].values[0]
    
    print(f"SDI NOTEBOOK Issue {top_2_issues[0]}: {val_1:.6f}")
    print(f"SDI NOTEBOOK Issue {top_2_issues[1]}: {val_2:.6f}\n")
    
    print("--- 3. COMPARACIÓN ---")
    diff_1 = abs(sdi_api_results[str(top_2_issues[0])]['social_debt_index'] - val_1)
    diff_2 = abs(sdi_api_results[str(top_2_issues[1])]['social_debt_index'] - val_2)
    print(f"Diferencia Issue {top_2_issues[0]}: {diff_1:.8f}")
    print(f"Diferencia Issue {top_2_issues[1]}: {diff_2:.8f}")
    
    if diff_1 < 0.0001 and diff_2 < 0.0001:
        print("\n¡VERIFICACIÓN EXITOSA! LA API Y EL CUADERNO PRODUCEN RESULTADOS MATEMÁTICAMENTE IDÉNTICOS.")
    
if __name__ == "__main__":
    run_comparison()
