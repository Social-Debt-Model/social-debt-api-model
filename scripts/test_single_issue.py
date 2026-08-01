import pandas as pd
from app.use_cases.semantic.ontology_matcher import classify_specific_causes_topk
from app.infrastructure.ontology_client import enrich_microcause
from app.use_cases.metrics.social_debt_index import calculate_batch_sdi

def run_single_issue():
    df = pd.read_excel('Modelo_adaptativo_deuda_social_julio/4. Integracion_semantica/Dataset_salida/Dataset_integration_semantico_original_con_H.xlsx')
    
    # Encontrar un issue con más de 50 comentarios
    issue_counts = df['issue_number'].value_counts()
    target_issue = issue_counts[issue_counts > 50].index[0]
    
    print(f"Probando con el Issue {target_issue} que tiene {issue_counts[target_issue]} comentarios...")
    
    df_issue = df[df['issue_number'] == target_issue]
    
    issues_data = {target_issue: []}
    
    for _, row in df_issue.iterrows():
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
            
            top_k_res = classify_specific_causes_topk(macro_label, text)
            for m in top_k_res.get("top_candidates", []):
                enriched = enrich_microcause(m.get("ontology_id"))
                microcauses.append({
                    "cause_name": m.get("specific_cause_name"),
                    "similarity": float(m["final_score"]),
                    "community_smells": enriched.get("community_smells", []),
                    "risks": enriched.get("risks", [])
                })
                
        issues_data[target_issue].append({
            "code": code,
            "is_noise": is_noise,
            "cleaned_text": text,
            "microcauses": microcauses
        })
        
    sdi_results = calculate_batch_sdi(issues_data)
    
    print("\nRESULTADOS EN LA API PARA ESTE ISSUE (Sin OpenAI):")
    print("-" * 50)
    metrics = sdi_results[str(target_issue)]
    print(f"SDI (Deuda Social): {metrics['social_debt_index']} (Es 0 porque es el único issue en el lote y MinMaxScaler no tiene con qué comparar)")
    print(f"Macrocausas Dominantes: {metrics['dominant_macrocauses']}")
    print(f"Microcausas Dominantes: {metrics['dominant_microcauses'][:3]}")
    print(f"Community Smells Detectados: {metrics['dominant_community_smells']}")
    print(f"Riesgos Detectados: {metrics['dominant_risks']}")

if __name__ == "__main__":
    run_single_issue()
