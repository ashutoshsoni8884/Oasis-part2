import httpx
import asyncio

async def test_chat():
    url = "http://localhost:8000/api/chat"
    payload = {
        "query": "show me unpaid invoices",
        "bearer_token": "dummy_token"
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")

if __name__ == "__main__":
    asyncio.run(test_chat())
