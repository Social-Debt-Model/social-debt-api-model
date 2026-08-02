import asyncio
import httpx
import time
import psutil
from app.core.config import settings

async def run_reduced_dataset_test():
    print("Selecciona el entorno de ejecución:")
    print("1. Local (http://127.0.0.1:8000)")
    print("2. Remoto / VPS Coolify (http://dxeaoppd6tz7tjuus42a8vwb.169.58.105.173.sslip.io)")
    
    env_opcion = input("Elige una opción (1/2): ").strip()
    if env_opcion == "2":
        api_url = "http://dxeaoppd6tz7tjuus42a8vwb.169.58.105.173.sslip.io"
    else:
        api_url = "http://127.0.0.1:8000"
        
    print("\nSelecciona el dataset para la prueba de carga:")
    print("1. Dataset de 1,000 comentarios")
    print("2. Dataset de 2,593 comentarios")
    print("3. Dataset original completo (~7,780 comentarios)")
    print("4. Cancelar")
    
    opcion = input("Elige una opción (1/2/3/4): ").strip()
    
    if opcion == "1":
        csv_filename = "Modelo_adaptativo_deuda_social_julio/Dataset_original/dataset_test_1000.csv"
    elif opcion == "2":
        csv_filename = "Modelo_adaptativo_deuda_social_julio/Dataset_original/dataset_test_2593.csv"
    elif opcion == "3":
        csv_filename = "Modelo_adaptativo_deuda_social_julio/Dataset_original/dataset_master_clean2.csv"
    elif opcion == "4":
        print("Prueba cancelada.")
        return
    else:
        print("Opción inválida. Saliendo...")
        return
        
    print(f"Iniciando prueba de rendimiento con el archivo: {csv_filename}...\n")
    print("-" * 50)
    
    # Pre-flight check: Validar saldo de OpenAI
    required_requests = { "1": 1000, "2": 2593, "3": 7780 }.get(opcion, 1000)
    
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
        while True:
            try:
                res = await client.get(f"{settings.API_V1_STR}/classify/batch/{job_id}", timeout=10.0)
                job_status = res.json()
                
                status = job_status.get("status")
                progress = job_status.get("progress", "Iniciando...")
                
                # Imprimir el progreso reemplazando la línea (carriage return) para no inundar la consola
                print(f"\rEstado: {status} | Progreso: {progress}                           ", end="", flush=True)
                
                if status in ["completed", "failed"]:
                    print() # Nueva línea al terminar
                    break
                    
            except Exception as e:
                print(f"\nError durante el polling: {e}")
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
        
        import json
        out_file = f"resultado_api_{opcion}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        print(f"\n[INFO] Resultados guardados completamente en {out_file} para que los compares.")
        
        comments_results = result_data.get("comments", [])
        total_comments = len(comments_results)
        
        print("\n" + "=" * 50)
        print(f"RESUMEN DE CLASIFICACIÓN ({total_comments} comentarios procesados)")
        print("=" * 50)
        
        # Mostrar solo los 3 primeros como ejemplo para no inundar la terminal
        print("Mostrando los primeros 3 comentarios como muestra:")
        for i, c in enumerate(comments_results[:3], 1):
            print(f"\n[Muestra {i}]: '{str(c.get('original_text', ''))[:100]}...'")
            print(f"   - Es Ruido: {c.get('is_noise', False)} ({c.get('noise_level', 'none')})")
            print(f"   - Macrocausa: {c.get('macro_cause_code', 'N/A')} (Confianza: {c.get('confidence', 0)})")
        print("\n... (Ocultando los demás comentarios para mantener la consola limpia) ...")
        
        print("\n" + "=" * 50)
        print("MÉTRICAS DE SOCIAL DEBT POR ISSUE (Muestra de 3 issues):")
        print("=" * 50)
        
        issues_metrics = result_data.get("issues_metrics", {})
        
        for i, (issue_id, metrics) in enumerate(list(issues_metrics.items())[:3]):
            print(f"\n[Issue #{issue_id}]")
            print(f"   - Comentarios válidos: {metrics.get('valid_comments', 0)} / {metrics.get('total_comments', 0)}")
            print(f"   - Diversidad Normalizada: {metrics.get('normalized_diversity', 0)}")
            print(f"   - SDI Score (Deuda Social): {metrics.get('sdi_score', 0)}")
            print(f"   - Riesgo Final (Estado): {metrics.get('sdi_status', 'Unknown')}")
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
