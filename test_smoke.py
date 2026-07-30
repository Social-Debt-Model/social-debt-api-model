import asyncio
from app.api.routes import classify_text
from app.domain.schemas import ClassificationRequest

async def main():
    req = ClassificationRequest(
        text="Thank you for this PR! Code looks good, did you run the perf dash to check it works as intended?"
    )
    res = await classify_text(req)
    print(f"Cause: {res.cause.value}")
    print(f"Confidence: {res.confidence}")
    
    # Assert conditions for smoke test
    assert res.cause.value == "G", f"Expected cause G, got {res.cause.value}"
    assert res.confidence == 0.88, f"Expected confidence 0.88, got {res.confidence}"
    print("Smoke test passed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
