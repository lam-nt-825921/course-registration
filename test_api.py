import asyncio
import httpx

async def test():
    async with httpx.AsyncClient() as client:
        res = await client.post("http://localhost:8000/api/auth/login", data={"username": "20020000", "password": "dummy_password"})
        if res.status_code != 200:
            print("Login failed:", res.text)
            return
        token = res.json()["access_token"]
        
        res = await client.get("http://localhost:8000/api/courses/", headers={"Authorization": f"Bearer {token}"})
        print("Status:", res.status_code)
        import json
        c = res.json()[0]
        print("Sample course:", json.dumps(c, indent=2))

asyncio.run(test())
