import asyncio
from app.api.routes import process_single_comment
import time

async def run_test():
    # Comentario de prueba (El mismo que usaba el cliente)
    test_comment = "Thank you for this PR! Code looks good, did you run the perf dash to check it works as intended?"
    
    print(f"Probando la API con el comentario:\n'{test_comment}'\n")
    print("-" * 50)
    
    try:
        # Llamar directamente a la función asíncrona del endpoint
        start_time = time.time()
        result = await process_single_comment(test_comment)
        end_time = time.time()
        exec_time = end_time - start_time
        
        print("RESULTADOS DEL PIPELINE COMPLETO:\n")
        print(f"⏱️ Tiempo de ejecución: {exec_time:.3f} segundos\n")
        print(f"1. Texto Limpio: '{result['cleaned_text']}'")
        print(f"2. Ruido detectado: {result['noise_level']} (Es ruido: {result['is_noise']})")
        print(f"3. Macro-causa (LLM + Reglas): {result['macro_cause_code']}")
        print(f"4. Confianza: {result['confidence']}")
        print(f"5. Regla Aplicada: {result['rule_applied']}")
        
        print("\n6. Micro-causas (Match Semántico) y Detalles Ontológicos:")
        for mc in result['microcauses']:
            print(f"   - {mc['cause_id']}: {mc['cause_name']} (Similitud: {mc['similarity']:.2f})")
            if mc.get('corrective_strategies'):
                print(f"     > Soluciones Correctivas: {', '.join(mc['corrective_strategies'])}")
            if mc.get('preventive_strategies'):
                print(f"     > Estrategias Preventivas: {', '.join(mc['preventive_strategies'])}")
            if mc.get('community_smells'):
                print(f"     > Community Smells Relacionados: {', '.join(mc['community_smells'])}")
            if mc.get('risks'):
                print(f"     > Riesgos Potenciales: {', '.join(mc['risks'])}")
            
        print("-" * 50)
        
        if result['macro_cause_code'] == 'G':
            print("✅ PRUEBA EXITOSA: La macro-causa es G, tal como en el notebook.")
        else:
            print("❌ ATENCIÓN: La macro-causa no es G. Revisa si configuraste correctamente el .env con OPENAI_API_KEY")
            
    except Exception as e:
        print(f"❌ Ocurrió un error al ejecutar la prueba. Detalle:\n{e}")
        print("Asegúrate de haber guardado tu OPENAI_API_KEY en el archivo .env")

if __name__ == "__main__":
    asyncio.run(run_test())
