import os
import asyncio
import httpx

api_key = "YOUR_GEMINI_API_KEY_HERE"
# A tiny 1x1 black jpeg base64
base64_image = "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA="

async def test_gemini():
    parts = [
        {"text": "What is this?"},
        {
            "inline_data": {
                "mime_type": "image/jpeg",
                "data": base64_image
            }
        }
    ]
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
            json={"contents": [{"parts": parts}]}
        )
        print("Status:", r.status_code)
        print("Response:", r.text)

asyncio.run(test_gemini())
