import asyncio
import aiohttp

api_url = 'https://paste.ee/api'

async def new_paste(code):
	params = {
		"key": "public",
		"description": "",
		"paste": code,
		"expire": 30000,
		"format": "json"
	}

	async with aiohttp.ClientSession() as session:
		async with session.post(api_url, data=params) as response:
			if response.status == 200:
				result = await response.json()
				return result["paste"]["raw"]
			print(f"[Paste.ee][Error {response.status}] Bad API request")
			return f"[Paste.ee] Bad API request"
	print("[Paste.ee][Error] Request closed")
