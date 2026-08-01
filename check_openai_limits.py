import os
import asyncio
import httpx
from dotenv import load_dotenv

async def check_limits():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: No se encontró OPENAI_API_KEY en el archivo .env")
        return

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "Hola"}],
        "max_tokens": 5
    }

    print("Consultando a OpenAI para leer los límites de tu cuenta...\n")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=data)
        
        if response.status_code != 200:
            print(f"Error de OpenAI: {response.status_code} - {response.text}")
            return
            
        print("="*50)
        print("LÍMITES DETECTADOS EN TU CUENTA (Modelo: gpt-4o-mini)")
        print("="*50)
        
        # Extraer cabeceras de Rate Limit
        h = response.headers
        rpm_limit = h.get('x-ratelimit-limit-requests', 'Desconocido')
        tpm_limit = h.get('x-ratelimit-limit-tokens', 'Desconocido')
        
        print(f"- Límite de Peticiones por Minuto (RPM): {rpm_limit}")
        print(f"- Límite de Tokens por Minuto (TPM):     {tpm_limit}")
        print("-" * 50)
        
        try:
            tpm = int(tpm_limit)
            if tpm <= 200000:
                print(">> DIAGNÓSTICO: Tu cuenta está en TIER 1 (Gratuita/Básica).")
                print(">> Esta es la razón exacta por la que el sistema debe frenar a ~40 minutos.")
            elif tpm >= 2000000:
                print(">> DIAGNÓSTICO: Tu cuenta está en TIER 2 o superior.")
                print(">> Puedes subir el 'tpm_limit' en routes.py a 2,000,000 para ir rapidísimo.")
            else:
                print(f">> DIAGNÓSTICO: Tu límite es de {tpm} TPM. Puedes ajustar el 'tpm_limit' en routes.py a {int(tpm * 0.9)}.")
        except:
            print("No se pudo calcular el Tier automáticamente.")
            
        print("="*50 + "\n")

if __name__ == "__main__":
    asyncio.run(check_limits())
