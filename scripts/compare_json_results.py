import json
import pandas as pd
import numpy as np

def run_comparison():
    print("Cargando el JSON de resultados de la API...")
    try:
        with open("resultado_api_3.json", "r", encoding="utf-8") as f:
            api_data = json.load(f)
    except Exception as e:
        print(f"Error al cargar el JSON: {e}")
        return

    api_comments = api_data.get("comments", [])
    api_issues = api_data.get("issues_metrics", {})
    
    print("Cargando los Excels originales del cliente...")
    try:
        df_comments = pd.read_excel('Modelo_adaptativo_deuda_social_julio/4. Integracion_semantica/Dataset_salida/Dataset_integration_semantico_original_con_H.xlsx')
        df_issues = pd.read_excel('Modelo_adaptativo_deuda_social_julio/5.Modelos/Dataset_salida/adaptive_social_debt_issue_model.xlsx')
    except Exception as e:
        print(f"Error al cargar los Excel: {e}")
        return

    # COMPARACIÓN DE COMENTARIOS
    print("\n--- COMPARACIÓN DE COMENTARIOS (Macrocausas) ---")
    
    # Crear diccionario del cliente: comment_id -> macro_cause
    client_comments_dict = {}
    for _, row in df_comments.iterrows():
        c_id = str(row['comment_id']).strip()
        # Asumimos que final_cause_code o predicted_code tiene la macrocausa final
        code = row.get('final_cause_code', row.get('predicted_code', 'H'))
        if pd.isna(code): code = "H"
        client_comments_dict[c_id] = str(code).strip()
        
    coincidencias = 0
    total_evaluados = 0
    diferencias = []
    
    for c in api_comments:
        c_id = str(c.get("comment_id", "")).strip()
        api_code = str(c.get("macro_cause_code", "H")).strip()
        
        if c_id in client_comments_dict:
            client_code = client_comments_dict[c_id]
            total_evaluados += 1
            if api_code == client_code:
                coincidencias += 1
            else:
                if len(diferencias) < 5:
                    diferencias.append(f"Comment {c_id}: API='{api_code}' vs Cliente='{client_code}'")

    if total_evaluados > 0:
        precision = (coincidencias / total_evaluados) * 100
        print(f"Comentarios encontrados y comparados: {total_evaluados}")
        print(f"Coincidencias exactas de Macrocausa: {coincidencias}")
        print(f"PRECISIÓN DE CLASIFICACIÓN: {precision:.2f}%")
        if diferencias:
            print("Ejemplos de diferencias:")
            for d in diferencias: print("  -", d)
    else:
        print("No se encontraron coincidencias de comment_id.")

    # COMPARACIÓN DE ISSUES (SDI)
    print("\n--- COMPARACIÓN DE MÉTRICAS SDI POR ISSUE ---")
    
    # Crear diccionario del cliente: issue_number -> sdi_score
    client_issues_dict = {}
    for _, row in df_issues.iterrows():
        i_id = str(row['issue_number']).strip()
        sdi = row.get('social_debt_index', 0.0)
        client_issues_dict[i_id] = float(sdi) if not pd.isna(sdi) else 0.0
        
    sdi_errors = []
    issues_encontrados = 0
    
    for i_id, api_metrics in api_issues.items():
        if i_id in client_issues_dict:
            issues_encontrados += 1
            client_sdi = client_issues_dict[i_id]
            api_sdi = float(api_metrics.get("sdi_score", 0.0))
            
            # Error absoluto medio (MAE)
            error = abs(api_sdi - client_sdi)
            sdi_errors.append(error)

    if issues_encontrados > 0:
        mae = np.mean(sdi_errors)
        print(f"Issues comparados: {issues_encontrados}")
        print(f"Error Absoluto Medio (MAE) del SDI: {mae:.4f} (Idealmente cercano a 0)")
        if mae < 0.05:
            print(">> Excelente: Las métricas SDI de la API coinciden casi perfectamente con el notebook del cliente.")
        else:
            print(">> Advertencia: Hay algunas desviaciones en el cálculo matemático del SDI.")
    else:
        print("No se encontraron coincidencias de issue_number.")
        
    print("\nComparación finalizada.")

if __name__ == "__main__":
    run_comparison()
