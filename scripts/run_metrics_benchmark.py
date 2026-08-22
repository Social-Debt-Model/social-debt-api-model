import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import pandas as pd
import httpx
import time
import psutil
from app.core.config import settings

async def run_issue_metrics_test():
    # 1. Crear un DataFrame (simulando un CSV) con 10 comentarios, agrupados en 2 Issues distintos
    data = [
        {"issue_number": 101, "comment": "I can't push to the repository, permission denied on the master branch."},
        {"issue_number": 101, "comment": "The server keeps crashing because we don't have enough memory to run the tests."},
        {"issue_number": 101, "comment": "I don't understand how this component works, the documentation is completely missing."},
        {"issue_number": 101, "comment": "We are blocked waiting for the architecture team to approve the security review ticket."},
        {"issue_number": 101, "comment": "There is a severe miscommunication between the frontend and backend teams regarding this endpoint."},
        {"issue_number": 101, "comment": "Our team lacks the necessary budget to scale the infrastructure properly."},
        {"issue_number": 101, "comment": "The current process for approving these merges is taking way too long and causing bottlenecks."},
        {"issue_number": 101, "comment": "Thank you for this PR! Code looks good, did you run the perf dash to check it works as intended?"},
        {"issue_number": 101, "comment": "I have noticed that several developers are implementing custom auth logic instead of using the standard library."},
        {"issue_number": 101, "comment": "Can someone please explain why this test is flaky on the CI environment but works locally?"}
    ]
    df = pd.DataFrame(data)
    
    # Guardar a un CSV temporal
    csv_filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_issues.csv")
    df.to_csv(csv_filename, index=False)
    
    print("Iniciando prueba de agrupamiento por Issues (Background Jobs)...\n")
    print("-" * 50)
    
    # 2. Enviar el archivo a la API (End-to-End Test)
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", headers={"X-API-Key": settings.API_SECRET_KEY}) as client:
        start_time_total = time.time()
        
        with open(csv_filename, "rb") as f:
            files = {"file": (csv_filename, f, "text/csv")}
            response = await client.post(f"{settings.API_V1_STR}/classify/batch", files=files)
            
        if response.status_code != 200:
            print(f"Error al enviar CSV: {response.text}")
            return
            
        data = response.json()
        job_id = data["job_id"]
        print(f"Archivo subido exitosamente. Job ID: {job_id}")
        
        
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
                
                await asyncio.sleep(0.5)
                
        monitor_task = asyncio.create_task(monitor_resources())
        
        # 3. Polling: Consultar el estado cada segundo hasta que termine
        while True:
            res = await client.get(f"{settings.API_V1_STR}/classify/batch/{job_id}")
            job_status = res.json()
            
            status = job_status.get("status")
            progress = job_status.get("progress", "Iniciando...")
            print(f"Estado: {status} | Progreso: {progress}")
            
            if status in ["completed", "failed"]:
                break
                
            await asyncio.sleep(1) # Esperar 1 segundo antes de volver a preguntar
            
        monitor_task.cancel()
            
        end_time_total = time.time()
        total_time = end_time_total - start_time_total
        
        print("\n" + "=" * 50)
        print("RESULTADOS INDIVIDUALES POR COMENTARIO:")
        print("=" * 50)
        
        result_data = job_status.get("result", {})
        comments_results = result_data.get("comments", [])
        for i, c in enumerate(comments_results, 1):
            print(f"\n[Comentario {i}]: '{c['original_text']}'")
            print(f"   - Limpio: '{c['cleaned_text']}'")
            print(f"   - Es Ruido: {c['is_noise']} ({c['noise_level']})")
            print(f"   - Macrocausa: {c['macro_cause_code']} (Confianza: {c['confidence']})")
            
            if c.get('microcauses'):
                print("   - Microcausas Detectadas:")
                for mc in c['microcauses']:
                    print(f"     > {mc['cause_id']}: {mc['cause_name']} (Similitud: {mc['similarity']:.2f})")
                    if mc.get('corrective_strategies'):
                        print(f"       + Soluciones: {', '.join(mc['corrective_strategies'])}")
                    if mc.get('community_smells'):
                        print(f"       + Smells: {', '.join(mc['community_smells'])}")
        
        print("\n" + "=" * 50)
        print("RESULTADOS GLOBALES DEL HILO (ISSUE #101):")
        print("=" * 50)
        
        issues_metrics = result_data.get("issues_metrics", {})
        
        for issue_id, metrics in issues_metrics.items():
            print(f"   - Comentarios válidos: {metrics['valid_comments']} / {metrics['total_comments']}")
            print(f"   - Diversidad (Shannon): {metrics['macro_diversity']}")
            print(f"   - Diversidad Normalizada: {metrics['normalized_diversity']}")
            print(f"   - Ratio de Ruido: {metrics['noise_ratio']}")
            print(f"   - SDI Score (Deuda Social): {metrics['sdi_score']}")
            print(f"   - Riesgo Final (Estado): {metrics['sdi_status']}")
            
        print("\n" + "=" * 50)
        print("RESUMEN DE RENDIMIENTO (END-TO-END + BACKGROUND JOB):")
        avg_time = total_time / 10
        print(f"Tiempo total (Subida + Polling + SDI): {total_time:.3f} segundos")
        print(f"Promedio por comentario: {avg_time:.3f} segundos")
        print(f"Estimación para 1,000 comentarios: {(avg_time * 1000) / 60:.2f} minutos")
        print(f"Estimación para 2,000 comentarios: {(avg_time * 2000) / 60:.2f} minutos")
        print(f"Estimación para 3,000 comentarios: {(avg_time * 3000) / 60:.2f} minutos")
        print(f"Estimación para 4,000 comentarios: {(avg_time * 4000) / 60:.2f} minutos")
        print(f"Consumo Máximo Detectado: CPU {max_cpu}% | RAM del proceso de prueba: {max_ram_mb:.1f} MB | RAM de TODO el servidor: {max_system_ram_percent}%")
        print("=" * 50 + "\n")

if __name__ == "__main__":
    asyncio.run(run_issue_metrics_test())
