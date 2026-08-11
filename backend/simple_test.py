print("Hello from simple test")
import asyncio
from job_sources.jobbank import create_jobbank_source

async def test():
    print("Creating JobBank source...")
    source = await create_jobbank_source({"rate_limit": 1.0, "max_pages": 1})
    print("Source created")
    await source.close()
    print("Source closed")

print("Starting test...")
asyncio.run(test())
print("Test completed")
