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

from app.domain.schemas import ClassificationRequest, ClassificationResponse
from app.use_cases.preprocessing.cleaning import clean_comment_text
from app.use_cases.preprocessing.noise_filtering import es_hard_noise, es_operational_noise
from app.use_cases.classification.llm_classifier import predict_macro_cause
from app.use_cases.semantic.ontology_matcher import classify_specific_causes_topk
from app.infrastructure.ontology_client import enrich_microcause
from app.use_cases.metrics.social_debt_index import calculate_batch_sdi

router = APIRouter()

JOBS_DIR = "app/jobs"
os.makedirs(JOBS_DIR, exist_ok=True)

# Bloqueo global para evitar la ejecución concurrente de múltiples archivos por lotes
batch_lock = asyncio.Lock()

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
                    "cause_name": m.get("specific_cause_name", m.get("cause_id", "")),
                    "similarity": float(m["final_score"]),
                    "community_smells": enriched.get("community_smells", []),
                    "risks": enriched.get("risks", []),
                    "ontology_id": m.get("ontology_id") or m.get("cause_id", "")
                })
            
    return {
        "original_text": text,
        "cleaned_text": cleaned_text,
        "noise_level": noise_level,
        "is_noise": is_noise,
        "macro_cause_code": final_code,
        "confidence": final_conf,
        "rule_applied": rule_applied,
        "microcauses": microcauses,
        "code": final_code
    }

async def background_batch_process(job_id: str, df: pd.DataFrame, text_col: str, issue_col: str):
    global active_job_state
    
    # Usar el bloqueo global para asegurar que solo 1 archivo se procese a la vez
    async with batch_lock:
        try:
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
            chunk_size = 10
            rows = list(df.iterrows())
            
            for i in range(0, total, chunk_size):
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
                        
                    row_dict = row.to_dict()
                    row_dict.update(res)
                    results.append(row_dict)
                    
                    if issue_col:
                        iss_id = row[issue_col]
                        if iss_id not in issues_data:
                            issues_data[iss_id] = []
                        issues_data[iss_id].append({
                            "code": res["macro_cause_code"],
                            "is_noise": res["is_noise"]
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
            
            if issue_col:
                # Group by issue using the batch SDI calculator
                sdi_results = calculate_batch_sdi(issues_data)
                response_data["issues_metrics"] = sdi_results
                
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
