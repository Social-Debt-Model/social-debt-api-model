"""
Verificador de Límites y Cuota de API OpenAI.

Realiza una consulta mínima al endpoint de inferencia de OpenAI para inspeccionar
las cabeceras HTTP de límites de tasa (RPM y TPM) asignadas a la API key configurada.

Uso:
    python scripts/check_openai_limits.py
"""

import os
import asyncio
import httpx
from dotenv import load_dotenv

async def check_limits():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[ERROR] Variable OPENAI_API_KEY no encontrada en el entorno (.env).")
        return

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 5
    }

    print("Consultando cabeceras de cuota y límites en OpenAI...\n")

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=data)

        if response.status_code != 200:
            print(f"[ERROR] Respuesta no exitosa de OpenAI ({response.status_code}): {response.text}")
            return

        print("=" * 60)
        print("LÍMITES DETECTADOS EN LA CUENTA (Modelo: gpt-4o-mini)")
        print("=" * 60)

        headers_resp = response.headers
        rpm_limit = headers_resp.get("x-ratelimit-limit-requests", "No disponible")
        tpm_limit = headers_resp.get("x-ratelimit-limit-tokens", "No disponible")

        print(f"- Límite de Peticiones por Minuto (RPM): {rpm_limit}")
        print(f"- Límite de Tokens por Minuto (TPM):     {tpm_limit}")
        print("-" * 60)

        try:
            tpm = int(tpm_limit)
            if tpm <= 200000:
                print(">> DIAGNÓSTICO: Cuenta en Tier 1 o nivel estándar (<= 200k TPM).")
            elif tpm >= 2000000:
                print(">> DIAGNÓSTICO: Cuenta en Tier de alta concurrencia (>= 2M TPM).")
            else:
                print(f">> DIAGNÓSTICO: Capacidad asignada: {tpm:,} TPM.")
        except (ValueError, TypeError):
            print("No fue posible inferir el Tier automáticamente a partir del valor retornado.")

        print("=" * 60 + "\n")

if __name__ == "__main__":
    asyncio.run(check_limits())
