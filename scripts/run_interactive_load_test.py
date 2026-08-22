import asyncio
import httpx
import time
import sys
import os
import psutil
import random

# Asegurar que Python pueda encontrar la carpeta "app" desde la carpeta scripts
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
import json

async def run_reduced_dataset_test():
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dict_path = os.path.join(BASE_DIR, "data/frontend_ontology_dictionary.json")
    print(f"[DEBUG] Attempting to load dictionary from: {dict_path}")
    try:
        with open(dict_path, "r", encoding="utf-8") as f:
            ontology_dict = json.load(f)
            macro_causes_dict = ontology_dict.get("macro_causes", {})
            print(f"[DEBUG] Loaded dictionary with {len(macro_causes_dict)} macro causes.")
    except Exception as e:
        print(f"[ERROR] No se pudo cargar el diccionario de ontología: {e}")
        macro_causes_dict = {}

    print("Selecciona el entorno de ejecución:")
    print("1. Local (http://127.0.0.1:8000)")
    print("2. Remoto / VPS Coolify (http://dxeaoppd6tz7tjuus42a8vwb.169.58.105.173.sslip.io)")
    
    env_opcion = input("Elige una opción (1/2): ").strip()
    if env_opcion == "2":
        api_url = "http://dxeaoppd6tz7tjuus42a8vwb.169.58.105.173.sslip.io"
    else:
        api_url = "http://127.0.0.1:8000"
        
    print("\nSelecciona el dataset para la prueba de carga:")
    print("1. Minimuestra de 100 comentarios (3 Issues)")
    print("2. Dataset de 1,000 comentarios")
    print("3. Dataset de 2,593 comentarios")
    print("4. Dataset original completo (~7,780 comentarios)")
    print("5. Cancelar")
    
    opcion = input("Elige una opción (1/2/3/4/5): ").strip()
    
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if opcion == "1":
        csv_filename = os.path.join(BASE_DIR, "data/dataset_test_100.csv")
    elif opcion == "2":
        csv_filename = os.path.join(BASE_DIR, "data/dataset_test_1000.csv")
    elif opcion == "3":
        csv_filename = os.path.join(BASE_DIR, "data/dataset_test_2593.csv")
    elif opcion == "4":
        csv_filename = os.path.join(BASE_DIR, "Modelo_adaptativo_deuda_social_julio/Dataset_original/dataset_master_clean2.csv")
    elif opcion == "5":
        print("Prueba cancelada.")
        return
    else:
        print("Opción inválida. Saliendo...")
        return
        
    print(f"Iniciando prueba de rendimiento con el archivo: {csv_filename}...\n")
    print("-" * 50)
    
    # Pre-flight check: Validar saldo de OpenAI
    required_requests = { "1": 100, "2": 1000, "3": 2593, "4": 7780 }.get(opcion, 100)
    
    async with httpx.AsyncClient(base_url=api_url, timeout=60.0, headers={"X-API-Key": settings.API_SECRET_KEY}) as client:
        print("Comprobando límites de OpenAI en el servidor...")
        try:
            limit_res = await client.get(f"{settings.API_V1_STR}/system/openai-limits")
            if limit_res.status_code == 200:
                limit_data = limit_res.json()
                if limit_data.get("status") == "success" or limit_data.get("status") == "rate_limit_exceeded":
                    remaining = int(limit_data.get("limits", {}).get("remaining_requests", 0))
                    print(f"Límite disponible actual: {remaining} peticiones (requests)")
                    if remaining < required_requests:
                        reset_time = limit_data.get("limits", {}).get("reset_requests", "desconocido")
                        print("\n" + "!" * 50)
                        print(f"¡ADVERTENCIA! No tienes suficientes peticiones para este dataset.")
                        print(f"Necesitas: {required_requests}")
                        print(f"Disponibles: {remaining}")
                        print(f"Tiempo para reinicio: {reset_time}")
                        print("!" * 50)
                        print("\nEl proceso ha sido cancelado para evitar errores 429 a la mitad de la carga.")
                        return
                    else:
                        print("¡Tienes peticiones suficientes! Procediendo con la prueba...\n")
                else:
                    print("No se pudo parsear los límites, continuando de todos modos...")
            else:
                print(f"Advertencia: El endpoint de límites devolvió {limit_res.status_code}")
        except Exception as e:
            print(f"Advertencia: Falló la comprobación de límites ({e}). Continuando...")
            
        start_time_total = time.time()
        
        try:
            with open(csv_filename, "rb") as f:
                files = {"file": (csv_filename, f, "text/csv")}
                response = await client.post(f"{settings.API_V1_STR}/classify/batch", files=files)
                
            if response.status_code != 200:
                print(f"Error al enviar CSV: {response.text}")
                return
                
            data = response.json()
            job_id = data["job_id"]
            print(f"Archivo subido exitosamente. Job ID: {job_id}")
            print("El procesamiento por lotes ha comenzado en segundo plano...")
            
        except Exception as e:
            print(f"Error de conexión: {e}. Asegúrate de que el servidor FastAPI esté corriendo.")
            return
        
        # Tarea de fondo para monitorear CPU y RAM máxima
        max_cpu = 0.0
        max_ram_mb = 0.0
        max_system_ram_percent = 0.0
        
        async def monitor_resources():
            nonlocal max_cpu, max_ram_mb, max_system_ram_percent
            psutil.cpu_percent(interval=None)
            while True:
                cpu = psutil.cpu_percent(interval=None)
                ram_mb = psutil.Process().memory_info().rss / (1024 * 1024)
                sys_ram = psutil.virtual_memory().percent
                
                if cpu > max_cpu: max_cpu = cpu
                if ram_mb > max_ram_mb: max_ram_mb = ram_mb
                if sys_ram > max_system_ram_percent: max_system_ram_percent = sys_ram
                
                await asyncio.sleep(1.0)
                
        monitor_task = asyncio.create_task(monitor_resources())
        
        # Polling: Consultar el estado hasta que termine
        print("Consultando estado de progreso (Polling)...")
        consecutive_errors = 0
        while True:
            try:
                res = await client.get(f"{settings.API_V1_STR}/classify/batch/{job_id}", timeout=10.0)
                res.raise_for_status()
                job_status = res.json()
                
                status = job_status.get("status")
                progress = job_status.get("progress", "Iniciando...")
                
                # Imprimir el progreso reemplazando la línea (carriage return) para no inundar la consola
                print(f"\rEstado: {status} | Progreso: {progress}                           ", end="", flush=True)
                
                if status in ["completed", "failed"]:
                    print() # Nueva línea al terminar
                    break
                    
                consecutive_errors = 0 # Resetear contador si hubo éxito
                
            except Exception as e:
                consecutive_errors += 1
                error_msg = str(e) if str(e) else type(e).__name__
                print(f"\n[Advertencia] Error temporal de red durante el polling ({consecutive_errors}/5): {error_msg}")
                if consecutive_errors >= 5:
                    print("Demasiados errores de red consecutivos. Abortando polling.")
                    break
                
            await asyncio.sleep(2) # Esperar 2 segundos antes de volver a preguntar
            
        monitor_task.cancel()
            
        end_time_total = time.time()
        total_time = end_time_total - start_time_total
        
        if job_status.get("status") != "completed":
            print(f"\nEl proceso terminó con estado: {job_status.get('status')}")
            if "error_message" in job_status:
                print(f"Error: {job_status['error_message']}")
            return
            
        result_data = job_status.get("result", {})
        out_file = f"resultado_api_{opcion}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        print(f"\n[INFO] Resultados guardados completamente en {out_file} para que los compares.")
        
        comments_results = result_data.get("comments", [])
        total_comments = len(comments_results)
        
        print("\n" + "=" * 50)
        print(f"RESUMEN DE CLASIFICACIÓN ({total_comments} comentarios procesados)")
        print("=" * 50)
        
        # Mostrar 3 aleatorios como ejemplo para no inundar la terminal
        print("Mostrando 3 comentarios aleatorios como muestra:")
        
        sample_comments = random.sample(comments_results, min(3, len(comments_results))) if comments_results else []
        for i, c in enumerate(sample_comments, 1):
            print(f"\n[Muestra {i}]: '{str(c.get('cleaned_text', ''))[:100]}...'")
            print(f"   - Es Ruido: {c.get('is_noise', False)} ({c.get('noise_level', 'none')})")
            macro_code = str(c.get('macro_cause_code', 'N/A')).strip()
            macro_name = macro_causes_dict.get(macro_code, 'Desconocida')
            print(f"   - Macrocausa: {macro_code} - {macro_name} (Confianza: {c.get('confidence', 0)})")
            
            mc_list = c.get('microcauses', [])
            if mc_list:
                print("   - Microcausas detectadas:")
                for mc in mc_list:
                    print(f"     > [{mc.get('ontology_id', '')}] {mc.get('cause_name', '')} (Similitud: {mc.get('similarity', 0):.2f})")
            else:
                print("   - Microcausas detectadas: Ninguna")
        print("\n... (Ocultando los demás comentarios para mantener la consola limpia) ...")
        
        print("\n" + "=" * 50)
        print("MÉTRICAS DE SOCIAL DEBT POR ISSUE (Muestra de 3 issues):")
        print("=" * 50)
        
        issues_metrics = result_data.get("issues_metrics", {})
        
        sample_issues = random.sample(list(issues_metrics.items()), min(3, len(issues_metrics))) if issues_metrics else []
        for i, (issue_id, metrics) in enumerate(sample_issues):
            print(f"\n[Issue #{issue_id}]")
            print(f"   - Total de comentarios evaluados: {metrics.get('comment_count', 0)}")
            print(f"   - Diversidad de Macrocausas: {metrics.get('macro_diversity', 0)}")
            print(f"   - Diversidad de Microcausas: {metrics.get('micro_diversity', 0)}")
            print(f"   - SDI Score (Índice de Deuda Social): {metrics.get('social_debt_index', 0):.4f}")
            print(f"   - Riesgo Final (Nivel de Deuda): {metrics.get('social_debt_level', 'Unknown')}")
        print("\n... (Ocultando los demás issues) ...")
            
        print("\n" + "=" * 50)
        print("RESUMEN DE RENDIMIENTO (END-TO-END + BACKGROUND JOB + TOKEN LIMITER):")
        print("=" * 50)
        
        avg_time = total_time / total_comments if total_comments > 0 else 0
        
        print(f"Comentarios procesados exitosamente: {total_comments}")
        print(f"Tiempo total (Subida + Procesamiento API + SDI): {total_time:.3f} segundos")
        print(f"Promedio real por comentario: {avg_time:.3f} segundos")
        print("-" * 50)
        print("PROYECCIONES ESCALADAS BASADAS EN ESTA PRUEBA:")
        print(f"Estimación para 4,000 comentarios: {(avg_time * 4000) / 60:.2f} minutos")
        print(f"Estimación para 5,000 comentarios: {(avg_time * 5000) / 60:.2f} minutos")
        print(f"Estimación para 6,000 comentarios: {(avg_time * 6000) / 60:.2f} minutos")
        print(f"Estimación para 7,000 comentarios: {(avg_time * 7000) / 60:.2f} minutos")
        print(f"Estimación para 8,000 comentarios: {(avg_time * 8000) / 60:.2f} minutos")
        print("-" * 50)
        print(f"Consumo Máximo Detectado:")
        print(f" > CPU Máx: {max_cpu}%")
        print(f" > RAM Proceso (Test): {max_ram_mb:.1f} MB")
        print(f" > RAM Total Servidor: {max_system_ram_percent}%")
        print("=" * 50 + "\n")

if __name__ == "__main__":
    asyncio.run(run_reduced_dataset_test())
