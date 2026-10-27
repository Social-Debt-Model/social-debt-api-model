"""
Prueba Unitaria de Inferencia de Comentario Individual.

Ejecuta el pipeline completo de procesamiento para un comentario de prueba:
limpieza de texto, detección de ruido, clasificación de macrocausa con LLM,
matching semántico con microcausas y enriquecimiento ontológico.

Uso:
    python scripts/debug_single_comment.py
"""

import os
import sys
import time
import asyncio

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from app.api.routes import process_single_comment

async def run_test():
    test_comment = "Thank you for this PR! Code looks good, did you run the perf dash to check it works as intended?"

    print(f"Evaluando pipeline de inferencia con el comentario:\n'{test_comment}'\n")
    print("-" * 60)

    try:
        start_time = time.time()
        result = await process_single_comment(test_comment)
        exec_time = time.time() - start_time

        print("RESULTADOS DEL PIPELINE:\n")
        print(f"- Tiempo de ejecución: {exec_time:.3f} segundos")
        print(f"- Texto limpio: '{result['cleaned_text']}'")
        print(f"- Nivel de ruido: {result['noise_level']} (Es ruido: {result['is_noise']})")
        print(f"- Macrocausa: {result['macro_cause_code']}")
        print(f"- Confianza: {result['confidence']}")
        print(f"- Regla aplicada: {result['rule_applied']}")

        print("\n- Microcausas identificadas y detalles ontológicos:")
        for mc in result.get("microcauses", []):
            print(f"   * [{mc['ontology_id']}] {mc['cause_name']} (Similitud: {mc['similarity']:.2f})")
            if mc.get("corrective_strategies"):
                print(f"     > Estrategias correctivas: {', '.join(mc['corrective_strategies'])}")
            if mc.get("preventive_strategies"):
                print(f"     > Estrategias preventivas: {', '.join(mc['preventive_strategies'])}")
            if mc.get("community_smells"):
                print(f"     > Community Smells asociados: {', '.join(mc['community_smells'])}")
            if mc.get("risks"):
                print(f"     > Riesgos asociados: {', '.join(mc['risks'])}")

        print("-" * 60)

        if result.get("macro_cause_code") == "G":
            print("[OK] Clasificación consistente con la referencia ontológica (Macrocausa G).")
        else:
            print(f"[INFO] Macrocausa asignada: {result.get('macro_cause_code')}. Verificar configuración de entorno si se esperaba G.")

    except Exception as e:
        print(f"[ERROR] Fallo en la ejecución del pipeline: {e}")
        print("Verificar que la variable OPENAI_API_KEY esté correctamente configurada en .env.")

if __name__ == "__main__":
    asyncio.run(run_test())
