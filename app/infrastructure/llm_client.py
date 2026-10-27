from openai import AsyncOpenAI
from app.core.config import settings
import time
import asyncio
import tiktoken

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

class TokenRateLimiter:
    def __init__(self, tpm_limit: int = 180000):
        self.capacity = tpm_limit
        self.tokens = self.capacity
        self.fill_rate = tpm_limit / 60.0
        self.last_update = time.time()
        try:
            self.encoding = tiktoken.get_encoding("o200k_base")
        except Exception:
            self.encoding = tiktoken.get_encoding("cl100k_base")

    def estimate_tokens(self, system_prompt: str, user_text: str) -> int:
        if not user_text: user_text = ""
        if not system_prompt: system_prompt = ""
        total_text = system_prompt + user_text
        return len(self.encoding.encode(total_text)) + 50

    async def acquire(self, token_count: int):
        while True:
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(self.capacity, self.tokens + elapsed * self.fill_rate)
            self.last_update = now

            if self.tokens >= token_count:
                self.tokens -= token_count
                break
            else:
                deficit = token_count - self.tokens
                wait_time = deficit / self.fill_rate
                await asyncio.sleep(wait_time)

global_limiter = TokenRateLimiter(tpm_limit=180000)

async def predict(system_prompt: str, user_text: str, model: str = "gpt-4o-mini", temperature: float = 0.0) -> str:
    tokens_needed = global_limiter.estimate_tokens(system_prompt, user_text)
    await global_limiter.acquire(tokens_needed)
    
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ],
        temperature=temperature
    )
    return response.choices[0].message.content
