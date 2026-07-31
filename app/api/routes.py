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
from app.use_cases.preprocessing.cleaning import clean_comment
from app.use_cases.preprocessing.noise_filtering import get_noise_level
from app.use_cases.classification.llm_classifier import predict_macro_cause
from app.use_cases.classification.priority_rules import apply_priority_rules
from app.use_cases.semantic.semantic_matcher import match_microcauses
from app.use_cases.metrics.social_debt_index import calculate_issue_metrics

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
    cleaned_text = clean_comment(text)
    noise_level = get_noise_level(cleaned_text)
    is_noise = noise_level in ["hard_noise", "operational_noise"]
    
    final_code = "H"
    final_conf = 1.0
    rule_applied = "none"
    microcauses = []
    
    if not is_noise:
        llm_code, llm_conf = await predict_macro_cause(cleaned_text)
        final_code, final_conf, rule_applied = apply_priority_rules(cleaned_text, llm_code, llm_conf)
        if final_code != "H":
            microcauses = match_microcauses(cleaned_text, final_code, top_k=3)
            
    return {
        "original_text": text,
        "cleaned_text": cleaned_text,
        "noise_level": noise_level,
        "is_noise": is_noise,
        "macro_cause_code": final_code,
        "confidence": final_conf,
        "rule_applied": rule_applied,
        "microcauses": microcauses
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
            
            # Procesar en lotes (chunks) concurrentes de 20 comentarios a la vez
            chunk_size = 20
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
                    
            response_data = {"comments": results}
            
            if issue_col:
                sdi_results = {}
                for iss_id, comments in issues_data.items():
                    sdi_metrics = calculate_issue_metrics(comments)
                    sdi_results[str(iss_id)] = sdi_metrics
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
        df = pd.read_csv(io.BytesIO(file_bytes))
    elif file.filename.endswith('.xlsx') or file.filename.endswith('.xls'):
        df = pd.read_excel(io.BytesIO(file_bytes))
    else:
        raise HTTPException(status_code=400, detail="Only CSV or Excel files are supported")
        
    text_col = next((col for col in df.columns if col.lower() in ['comment', 'text', 'body', 'description']), None)
    if not text_col:
        raise HTTPException(status_code=400, detail="Could not find a text column")
        
    issue_col = next((col for col in df.columns if col.lower() in ['issue_number', 'issue', 'ticket', 'issue_id']), None)
    
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
            
    return job_data
