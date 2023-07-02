from aiofile import AIOFile
from base64 import b64encode
from cryptjson import json_zip, json_unzip

import aiomysql
import asyncio
import os
import sys
import ujson

with open("config.txt") as f:
	config = ujson.load(f)
	client_id_dec = config.pop("premium_id", "")
	client_id = b64encode(client_id_dec.encode()).decode()
	client_admins = config.pop("admins", {})
	disconnect_mod_room = config.pop("disconnect_mod_room", False)
	disconnect_mod_game = config.pop("disconnect_mod_game", False)
	public_commands = config.pop("public_commands", False)
	private_commands = config.pop("private_commands", False)
	born_period = config.pop("born_period", 2.95)

maps = {}

from math import floor
def fix_pos(num):
	return floor(num * 8 / 26.66)
	
def calc_pos(num):
	return floor(num * 100 / 30)

async def get_maps_from_storage():
	pool = await aiomysql.create_pool(host="remotemysql.com", user="OiLrYYIcWc", password="Rcah6mNTTE", db="OiLrYYIcWc", loop=loop)
	async with pool.acquire() as conn:
		async with conn.cursor() as cur:
			await cur.execute("SELECT json FROM maps WHERE id=%s", (client_id_dec, ))
			selected = await cur.fetchone()
			if not selected:
				if os.path.isfile("maps.json"):
					async with AIOFile("maps.json", "rb") as f:
						data = json_unzip(await f.read())
						for code, info in data.items():
							maps[code] = info
						await cur.execute("INSERT INTO maps (id, json) VALUES (%s, %s)", (client_id_dec, json_zip(maps)))
			else:
				for code, info in json_unzip(selected[0]).items():
					maps[code] = info
		await conn.commit()
	pool.close()
	await pool.wait_closed()

	print(f"[Maps Database] Storage has been updated. Total length: {len(maps)}")

async def update_maps_storage(code = "", info = (), author="", delete=False):
	await get_maps_from_storage()

	if code:
		if delete:
			del maps[code]

			print(f"[Maps Database] {code} map has been deleted by {author}")
		else:
			maps[code] = info

	pool = await aiomysql.create_pool(host="remotemysql.com", user="OiLrYYIcWc", password="Rcah6mNTTE", db="OiLrYYIcWc", loop=loop)
	async with pool.acquire() as conn:
		async with conn.cursor() as cur:
			data = json_zip(maps)
			await cur.execute("UPDATE maps SET json=%s WHERE id=%s", (data, client_id_dec))
		await conn.commit()
	pool.close()
	await pool.wait_closed()

loop = asyncio.get_event_loop()
loop.create_task(get_maps_from_storage())