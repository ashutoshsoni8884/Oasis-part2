import httpx
import asyncio
import json

async def test_query(query):
    url = "http://localhost:8000/api/chat"
    payload = {
        "query": query,
        "bearer_token": "dummy_token"
    }
    print(f"\n--- Testing Query: {query} ---")
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(url, json=payload)
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Job ID: {data.get('job_id')}")
                print(f"Message: {data.get('message')}")
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Exception: {e}")

async def main():
    queries = [
        "show me credit limit for customer 57632",
        "Show me subscription summary of 56064",
        "Unpaid invoices of ABC Consulting"
    ]
    for q in queries:
        await test_query(q)

if __name__ == "__main__":
    asyncio.run(main())
