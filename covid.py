import asyncio
loop = asyncio.get_event_loop()

import aiohttp

countries = {}

async def update_countries_data():
	async with aiohttp.ClientSession() as session:
		async with session.get("http://country.io/names.json") as response:
			if response.status == 200:
				global countries
				countries = await response.json()
				return print("[Covid] Countries JSON updated.")
			return print(f"[Covid][Error {response.status}] Bad API request")
	print("[Covid][Error] Request closed")

async def get_info(country):
	async with aiohttp.ClientSession() as session:
		async with session.get("https://coronavirus-19-api.herokuapp.com/countries/" + countries.get(country.upper(), country)) as response:
			if response.status == 200:
				if "not found" in await response.text():
					return "[Worldometers] Country not found"
				result = await response.json()
				today = f" (+{result['todayCases']} last 24H)" if result['todayCases'] > 0 else ""
				today_d = f" (+{result['todayDeaths']} last 24H)" if result['todayDeaths'] > 0 else ""
				return f"[Worldometers] {result['country']} » Cases: {result['cases']}{today} - {result['active']} currently active / Total deaths: {result['deaths']}{today_d} / Recovered: {result['recovered']}"
			print(f"[Covid][Error {response.status}] Bad API request")
			return ""

loop.create_task(update_countries_data())