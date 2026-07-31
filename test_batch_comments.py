import asyncio
from app.api.routes import process_single_comment
import time

async def run_batch_test():
    comments = [
        "I can't push to the repository, permission denied on the master branch.",
        "Thank you for this PR! Code looks good, did you run the perf dash to check it works as intended?",
        "The server keeps crashing because we don't have enough memory to run the tests.",
        "I don't understand how this component works, the documentation is completely missing.",
        "We are blocked waiting for the architecture team to approve the security review ticket.",
        "There is a severe miscommunication between the frontend and backend teams regarding this endpoint.",
        "Our team lacks the necessary budget to scale the infrastructure properly.",
        "The current process for approving these merges is taking way too long and causing bottlenecks.",
        "I have noticed that several developers are implementing custom auth logic instead of using the standard library.",
        "Can someone please explain why this test is flaky on the CI environment but works locally?"
    ]
    
    print(f"Probando un lote de {len(comments)} comentarios de prueba...\n")
    print("-" * 50)
    
    start_time_total = time.time()
    
    results = []
    for i, text in enumerate(comments, 1):
        print(f"Procesando comentario {i}...")
        start_time_comment = time.time()
        
        try:
            res = await process_single_comment(text)
            end_time_comment = time.time()
            exec_time = end_time_comment - start_time_comment
            
            res['exec_time'] = exec_time
            results.append(res)
            
            print(f"✅ Terminado en {exec_time:.3f} segundos (Macrocausa: {res['macro_cause_code']})")
        except Exception as e:
            print(f"❌ Error: {e}")
            
    end_time_total = time.time()
    total_time = end_time_total - start_time_total
    
    print("-" * 50)
    print("RESUMEN DE RENDIMIENTO (BATCH):")
    print(f"Total comentarios: {len(comments)}")
    print(f"Tiempo total: {total_time:.3f} segundos")
    
    if results:
        avg_time = total_time / len(results)
        print(f"Promedio por comentario: {avg_time:.3f} segundos")
        print(f"Estimación para 1,000 comentarios: {(avg_time * 1000) / 60:.2f} minutos")
        print(f"Estimación para 2,000 comentarios: {(avg_time * 2000) / 60:.2f} minutos")
        print(f"Estimación para 3,000 comentarios: {(avg_time * 3000) / 60:.2f} minutos")

if __name__ == "__main__":
    asyncio.run(run_batch_test())
