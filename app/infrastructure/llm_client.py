from openai import AsyncOpenAI
from app.core.config import settings

# Initialize AsyncOpenAI client
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

async def predict(system_prompt: str, user_text: str, model: str = "gpt-4o-mini", temperature: float = 0.0) -> str:
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ],
        temperature=temperature
    )
    return response.choices[0].message.content
