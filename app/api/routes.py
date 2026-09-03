from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks
from typing import List, Dict, Any
import pandas as pd
import io
import uuid
import json
import os
import random
import string
import asyncio
import time
from datetime import datetime
import base64

from app.domain.schemas import ClassificationRequest, ClassificationResponse
from pydantic import BaseModel
from app.use_cases.preprocessing.cleaning import clean_comment_text
from app.use_cases.preprocessing.noise_filtering import es_hard_noise, es_operational_noise
from app.use_cases.classification.llm_classifier import predict_macro_cause
from app.use_cases.semantic.ontology_matcher import classify_specific_causes_topk
from app.infrastructure.ontology_client import enrich_microcause
from app.use_cases.metrics.social_debt_index import calculate_batch_sdi
from app.infrastructure.llm_client import client

router = APIRouter()

JOBS_DIR = "app/jobs"
os.makedirs(JOBS_DIR, exist_ok=True)

# Bloqueo global para evitar la ejecución concurrente de múltiples archivos por lotes
batch_lock = asyncio.Lock()

def df_to_b64_excel(df_or_dict):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        if isinstance(df_or_dict, dict):
            for sheet_name, df_sheet in df_or_dict.items():
                df_sheet.to_excel(writer, sheet_name=sheet_name, index=False)
        else:
            df_or_dict.to_excel(writer, index=False)
    return base64.b64encode(output.getvalue()).decode('utf-8')


# Estado global del trabajo activo para calcular estimaciones a los trabajos en cola
active_job_state = {
    "job_id": None,
    "total_comments": 0,
    "processed_comments": 0,
    "avg_time_per_comment": 0.30 # Valor inicial conservador (300ms)
}

def get_job_file_path(job_id: str) -> str:
    return os.path.join(JOBS_DIR, f"{job_id}.json")

def update_job_status(job_id: str, data: dict):
    path = get_job_file_path(job_id)
    # Merging with existing data if exists
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            current_data = json.load(f)
        current_data.update(data)
    else:
        current_data = data
        
    current_data["updated_at"] = datetime.utcnow().isoformat()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(current_data, f, ensure_ascii=False, indent=2)

def get_job_status(job_id: str) -> dict:
    path = get_job_file_path(job_id)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

async def process_single_comment(text: str) -> dict:
    cleaned_text = clean_comment_text(text)
    is_hard = es_hard_noise(cleaned_text)
    is_oper = es_operational_noise(cleaned_text)
    is_noise = is_hard or is_oper
    noise_level = "hard_noise" if is_hard else "operational_noise" if is_oper else "none"
    
    final_code = "H"
    macro_label = "No identificable"
    final_conf = 1.0
    rule_applied = "none"
    microcauses = []
    
    if not is_noise:
        llm_code, llm_conf = await predict_macro_cause(cleaned_text)
        final_code = llm_code
        final_conf = llm_conf
        
        if final_code != "H":
            # Map code back to label for the semantic matcher (it expects labels, wait, I can modify it or pass code)
            # The client notebook mapped A->Communication etc. Let's assume classify_specific_causes_topk accepts it.
            macro_label = final_code
            if final_code == "A": macro_label = "Communication and shared understanding breakdowns"
            elif final_code == "B": macro_label = "Coordination and workflow misalignment"
            elif final_code == "C": macro_label = "Technical complexity, compatibility, and system constraints"
            elif final_code == "D": macro_label = "Organizational and procedural workflow constraints"
            elif final_code == "E": macro_label = "Collaboration and interpersonal tensions"
            elif final_code == "F": macro_label = "Knowledge, documentation, and standards deficiencies"
            elif final_code == "G": macro_label = "Resource, tooling, access, and validation dependencies"
            
            top_k_res = classify_specific_causes_topk(macro_label, cleaned_text)
            
            for m in top_k_res.get("top_candidates", []):
                enriched = enrich_microcause(m.get("ontology_id") or m.get("cause_id", ""))
                microcauses.append({
                    "ontology_id": m.get("ontology_id") or m.get("cause_id", ""),
                    "cause_type": enriched.get("cause_type"),
                    "cause_name": m.get("specific_cause_name", m.get("cause_id", "")),
                    "similarity": float(m["final_score"]),
                    "risks": enriched.get("risks", []),
                    "community_smells": enriched.get("community_smells", []),
                    "preventive_strategies": enriched.get("preventive_strategies", []),
                    "effects": enriched.get("effects", []),
                    "corrective_strategies": enriched.get("corrective_strategies", []),
                    "indicators": enriched.get("indicators", []),
                    "metrics": enriched.get("metrics", [])
                })
            
    return {
        "cleaned_text": cleaned_text,
        "is_noise": is_noise,
        "noise_level": noise_level,
        "macro_cause_code": final_code,
        "macro_cause_clean": macro_label,
        "confidence": final_conf,
        "rule_applied": rule_applied,
        "microcauses": microcauses
    }

async def background_batch_process(job_id: str, df: pd.DataFrame, text_col: str, issue_col: str):
    global active_job_state
    
    # Usar el bloqueo global para asegurar que solo 1 archivo se procese a la vez
    async with batch_lock:
        try:
            initial_status = get_job_status(job_id)
            if initial_status and initial_status.get("status") == "cancelled":
                return
                
            results = []
            issues_data = {}
            total = len(df)
            processed = 0
            
            # Registrar como el trabajo activo actual
            active_job_state["job_id"] = job_id
            active_job_state["total_comments"] = total
            active_job_state["processed_comments"] = 0
            start_time = time.time()
            
            update_job_status(job_id, {
                "status": "processing",
                "progress": f"0 de {total} comentarios procesados (0%)",
                "total": total,
                "processed": 0
            })
            
            # Procesar en lotes (chunks) conservadores de 10 para respetar el Tier 1 (Rate Limits)
            chunk_size = 50
            rows = list(df.iterrows())
            
            for i in range(0, total, chunk_size):
                # Check cancellation at each chunk
                current_status = get_job_status(job_id)
                if current_status and current_status.get("status") == "cancelled":
                    active_job_state["job_id"] = None
                    return
                    
                chunk = rows[i:i + chunk_size]
                tasks = []
                
                for idx, row in chunk:
                    text = str(row[text_col])
                    if pd.isna(row[text_col]) or not text.strip():
                        # Para simplificar el gather, enviamos una tarea dummy que retorna un dict vacío o manejamos después
                        async def dummy_task(r):
                            return r, None
                        tasks.append(dummy_task(row))
                    else:
                        async def process_task(r, t):
                            res = await process_single_comment(t)
                            return r, res
                        tasks.append(process_task(row, text))
                
                chunk_results = await asyncio.gather(*tasks)
                
                for row, res in chunk_results:
                    if res is None:
                        processed += 1
                        continue
                        
                    iss_raw = row.get(issue_col) if issue_col else None
                    iss_val = None if pd.isna(iss_raw) else (int(iss_raw) if isinstance(iss_raw, (float, int)) and float(iss_raw).is_integer() else str(iss_raw))
                    
                    id_raw = row.get("comment_id", row.get("id"))
                    id_val = None if pd.isna(id_raw) else (int(id_raw) if isinstance(id_raw, (float, int)) and float(id_raw).is_integer() else str(id_raw))

                    row_dict = {
                        "issue_number": iss_val,
                        "comment_id": id_val
                    }
                    row_dict.update(res)
                    results.append(row_dict)
                    
                    if iss_val is not None:
                        if iss_val not in issues_data:
                            issues_data[iss_val] = []
                        issues_data[iss_val].append({
                            "code": res["macro_cause_code"],
                            "is_noise": res["is_noise"],
                            "cleaned_text": res.get("cleaned_text", ""),
                            "microcauses": res.get("microcauses", [])
                        })
                    processed += 1
                    
                percent = int((processed / total) * 100)
                
                # Actualizar estado global para que los que están en cola calculen el tiempo
                active_job_state["processed_comments"] = processed
                elapsed = time.time() - start_time
                if processed > 0:
                    active_job_state["avg_time_per_comment"] = elapsed / processed
                    
                update_job_status(job_id, {
                    "progress": f"{processed} de {total} comentarios procesados ({percent}%)",
                    "processed": processed
                })
                
                # NOTA: El limitador de tokens dinámico ya gestiona el ritmo 
                # directamente en la capa de red (llm_client.py) antes de llamar a OpenAI.
                    
            response_data = {"comments": results}
            
            # Construir DataFrames para exportación
            df_step1 = pd.DataFrame(results)
            df_step2 = df_step1[df_step1["is_noise"] == False].copy() if not df_step1.empty else pd.DataFrame()
            
            sdi_results = {}
            if issue_col:
                # Group by issue using the batch SDI calculator
                sdi_results = calculate_batch_sdi(issues_data)
                response_data["issues_metrics"] = sdi_results
                
            df_step3 = pd.DataFrame(sdi_results).T.reset_index().rename(columns={"index": "issue_number"}) if sdi_results else pd.DataFrame()
            
            # Construir Excel Final
            df_ontology = pd.DataFrame()
            try:
                with open("data/frontend_ontology_dictionary.json", "r", encoding="utf-8") as f:
                    ont_data = json.load(f)
                    flat_ont = []
                    for k, v in ont_data.items():
                        if isinstance(v, dict):
                            v["id"] = k
                            flat_ont.append(v)
                    df_ontology = pd.DataFrame(flat_ont)
            except Exception:
                pass
                
            exports = {
                "step1_b64": df_to_b64_excel(df_step1),
                "step2_b64": df_to_b64_excel(df_step2),
                "step3_b64": df_to_b64_excel(df_step3),
                "final_excel_b64": df_to_b64_excel({"Comentarios": df_step1, "Ontologia": df_ontology})
            }
            response_data["exports"] = exports
                
            update_job_status(job_id, {
                "status": "completed",
                "progress": f"{total} de {total} comentarios procesados (100%)",
                "result": response_data
            })
            
            active_job_state["job_id"] = None
            
        except Exception as e:
            active_job_state["job_id"] = None
            update_job_status(job_id, {
                "status": "failed",
                "error_message": str(e)
            })

@router.post("/classify/text", response_model=dict)
async def classify_text(request: ClassificationRequest):
    """
    Clasifica un único comentario de texto de forma síncrona.
    """
    result = await process_single_comment(request.text)
    return result

@router.post("/classify/batch")
async def classify_batch(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Sube un archivo CSV o Excel. Retorna un job_id casi instantáneamente.
    """
    file_bytes = await file.read()
    if file.filename.endswith('.csv'):
        try:
            df = pd.read_csv(io.BytesIO(file_bytes))
            if len(df.columns) == 1:
                df = pd.read_csv(io.BytesIO(file_bytes), sep=';')
        except Exception:
            df = pd.read_csv(io.BytesIO(file_bytes), sep=';')
    elif file.filename.endswith('.xlsx') or file.filename.endswith('.xls'):
        df = pd.read_excel(io.BytesIO(file_bytes))
    else:
        raise HTTPException(status_code=400, detail="Only CSV or Excel files are supported")
        
    # Buscar la columna de texto (coincidencia parcial, evitando ids y metadatos)
    text_keywords = ['body', 'text', 'content', 'description', 'comment']
    text_col = None
    for col in df.columns:
        c = col.lower()
        if any(bad in c for bad in ['id', 'author', 'date', 'created', 'url', 'time']):
            continue
        if any(kw in c for kw in text_keywords):
            text_col = col
            break
            
    if not text_col:
        raise HTTPException(status_code=400, detail="Could not find a text column")
        
    # Verificar límites de OpenAI antes de aceptar el archivo
    limits_response = await check_openai_limits()
    if limits_response.get("status") == "rate_limit_exceeded":
        raise HTTPException(status_code=429, detail="Cuota de OpenAI agotada o límite excedido. Intenta más tarde.")
        
    limits = limits_response.get("limits", {})
    rem_req_str = limits.get("remaining_requests", "0")
    try:
        rem_req = int(rem_req_str)
    except:
        rem_req = 0
        
    if len(df) > rem_req:
        raise HTTPException(
            status_code=400, 
            detail=f"El archivo tiene {len(df)} comentarios, pero tu cuota actual de OpenAI solo permite {rem_req} peticiones más en este momento."
        )
        
    # Buscar la columna del issue (coincidencia parcial)
    issue_keywords = ['issue_number', 'issue', 'ticket', 'issue_id']
    issue_col = next((col for col in df.columns if any(kw in col.lower() for kw in issue_keywords)), None)
    
    # Generar un ID corto, humano y amigable (ej: "A8K9M2")
    job_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    
    update_job_status(job_id, {
        "job_id": job_id,
        "status": "pending",
        "progress": "Iniciando...",
        "filename": file.filename
    })
    
    background_tasks.add_task(background_batch_process, job_id, df, text_col, issue_col)
    
    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Tu archivo se está procesando. Consulta el estado con el job_id en el endpoint GET /classify/batch/{job_id}."
    }

@router.get("/classify/batch/{job_id}")
async def get_batch_status(job_id: str):
    """
    Consulta el estado y progreso de un procesamiento por lotes usando el job_id.
    """
    job_data = get_job_status(job_id)
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
        
    # Si este trabajo está en cola, calcular cuánto le falta al trabajo activo actual
    if job_data.get("status") == "pending" and active_job_state["job_id"] is not None:
        remaining_comments = active_job_state["total_comments"] - active_job_state["processed_comments"]
        if remaining_comments > 0:
            est_seconds = remaining_comments * active_job_state["avg_time_per_comment"]
            est_minutes = est_seconds / 60
            if est_minutes > 1:
                wait_time_str = f"~{est_minutes:.1f} minutos"
            else:
                wait_time_str = f"~{est_seconds:.0f} segundos"
            
            job_data["progress"] = f"En cola de espera... (Tiempo estimado para iniciar: {wait_time_str})"
            
    # Añadir estimación de tiempo restante si el trabajo está en procesamiento
    elif job_data.get("status") == "processing" and job_data.get("job_id", job_id) == active_job_state["job_id"]:
        remaining_comments = active_job_state["total_comments"] - active_job_state["processed_comments"]
        if remaining_comments > 0:
            est_seconds = remaining_comments * active_job_state["avg_time_per_comment"]
            job_data["estimated_remaining_seconds"] = round(est_seconds, 2)
            if est_seconds > 60:
                job_data["estimated_remaining_time_formatted"] = f"~{est_seconds/60:.1f} minutos"
            else:
                job_data["estimated_remaining_time_formatted"] = f"~{est_seconds:.0f} segundos"
            
    return job_data

@router.get("/system/openai-limits")
async def check_openai_limits():
    """
    Realiza un ping a OpenAI para leer los headers de respuesta y 
    determinar la cuota exacta (Requests y Tokens) disponibles en tiempo real.
    """
    try:
        # Hacemos una petición mínima de 1 token para que devuelva los headers
        response = await client.chat.completions.with_raw_response.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1
        )
        headers = response.headers
        
        return {
            "status": "success",
            "model": "gpt-4o-mini",
            "limits": {
                "remaining_requests": headers.get("x-ratelimit-remaining-requests"),
                "limit_requests": headers.get("x-ratelimit-limit-requests"),
                "reset_requests": headers.get("x-ratelimit-reset-requests"),
                "remaining_tokens": headers.get("x-ratelimit-remaining-tokens"),
                "limit_tokens": headers.get("x-ratelimit-limit-tokens"),
                "reset_tokens": headers.get("x-ratelimit-reset-tokens"),
            },
            "message": "Limits fetched successfully."
        }
    except Exception as e:
        # Si ya llegamos al límite, OpenAI arrojará un error 429, pero igual podemos leer los headers del error
        if hasattr(e, 'response') and e.response is not None:
            headers = e.response.headers
            return {
                "status": "rate_limit_exceeded",
                "model": "gpt-4o-mini",
                "limits": {
                    "remaining_requests": headers.get("x-ratelimit-remaining-requests"),
                    "limit_requests": headers.get("x-ratelimit-limit-requests"),
                    "reset_requests": headers.get("x-ratelimit-reset-requests"),
                    "remaining_tokens": headers.get("x-ratelimit-remaining-tokens"),
                    "limit_tokens": headers.get("x-ratelimit-limit-tokens"),
                    "reset_tokens": headers.get("x-ratelimit-reset-tokens"),
                },
                "error_message": str(e)
            }
        
        raise HTTPException(status_code=500, detail=f"Failed to fetch OpenAI limits: {str(e)}")

class CancelRequest(BaseModel):
    job_id: str

@router.post("/classify/batch/cancel")
async def cancel_batch(req: CancelRequest):
    """
    Cancela un trabajo por lotes en progreso o en cola.
    """
    status_data = get_job_status(req.job_id)
    if not status_data:
        raise HTTPException(status_code=404, detail="Job not found")
        
    current = status_data.get("status")
    if current in ["completed", "failed", "cancelled"]:
        return {"message": f"Job is already {current}"}
        
    update_job_status(req.job_id, {"status": "cancelled"})
    
    # Si este era el trabajo activo, limpiamos el estado global
    if active_job_state["job_id"] == req.job_id:
        active_job_state["job_id"] = None
        
    return {"message": "Job cancelled successfully"}
