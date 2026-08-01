import pandas as pd
import numpy as np
from app.use_cases.semantic.ontology_matcher import classify_specific_causes_topk
from app.use_cases.metrics.social_debt_index import calculate_batch_sdi
from app.infrastructure.ontology_client import enrich_microcause

def run_verification():
    print("Loading original dataset...")
    df = pd.read_excel('Modelo_adaptativo_deuda_social_julio/4. Integracion_semantica/Dataset_salida/Dataset_integration_semantico_original_con_H.xlsx')
    
    issues_data = {}
    print(f"Processing {len(df)} rows for semantic matching...")
    # Group by issue
    for _, row in df.iterrows():
        i_id = row['issue_number']
        code = row.get('final_cause_code', row.get('predicted_code', 'H'))
        if pd.isna(code): code = "H"
        
        text = str(row['comment_body_clean_final'])
        
        if i_id not in issues_data:
            issues_data[i_id] = []
            
        is_noise = (code == "H") # Simplified noise assumption for test
        
        microcauses = []
        if not is_noise:
            # Map code
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
        
        issues_data[i_id].append({
            "code": code,
            "is_noise": is_noise,
            "cleaned_text": text,
            "microcauses": microcauses
        })
        
    print("Calculating batch SDI...")
    sdi_results = calculate_batch_sdi(issues_data)
    
    print("Loading client SDI results...")
    df_issues = pd.read_excel('Modelo_adaptativo_deuda_social_julio/5.Modelos/Dataset_salida/adaptive_social_debt_issue_model.xlsx')
    
    client_issues_dict = {}
    for _, row in df_issues.iterrows():
        client_issues_dict[row['issue_number']] = float(row.get('social_debt_index', 0.0))
        
    sdi_errors = []
    issues_encontrados = 0
    for i_id, metrics in sdi_results.items():
        if i_id in client_issues_dict:
            issues_encontrados += 1
            diff = abs(metrics['social_debt_index'] - client_issues_dict[i_id])
            sdi_errors.append(diff)
            
    if issues_encontrados > 0:
        mae = np.mean(sdi_errors)
        max_err = np.max(sdi_errors)
        print(f"Issues comparados: {issues_encontrados}")
        print(f"Error Absoluto Medio (MAE) del SDI: {mae:.6f} (0 es perfecto)")
        print(f"Max Error: {max_err:.6f}")
        if mae < 0.001:
            print("VERIFICACION EXITOSA: Los valores son IDENTICOS a los del cliente.")
        else:
            print("ADVERTENCIA: Hay diferencias en los cálculos.")
    else:
        print("No issues found to compare.")

if __name__ == "__main__":
    run_verification()
