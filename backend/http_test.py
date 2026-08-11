import asyncio
import aiohttp

async def test():
    print("Testing HTTP connection to JobBank...")
    url = "https://www.jobbank.gc.ca/"
    
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                print(f"HTTP Status: {response.status}")
                if response.status == 200:
                    html = await response.text()
                    print(f"Successfully fetched {len(html)} characters")
                    print(f"First 500 chars: {html[:500]}")
                else:
                    print(f"HTTP Error: {response.status}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

print("Starting HTTP test...")
asyncio.run(test())
print("HTTP test completed")
