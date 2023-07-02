from aiotfm import __version__
from aiotfm.errors import EndpointError, InternalError, MaintenanceError
from zlibsrc import init; init()
import aiomysql, aiohttp
import asyncio
import json

loop = asyncio.get_event_loop()

class Keys:
	def __init__(self, **keys):
		self.auth = keys.pop('auth_key', 0)
		self.connection = keys.pop('connection_key', '')
		self.identification = keys.pop('identification_keys', [])
		self.msg = [k & 0xff for k in keys.pop('msg_keys', [])]
		self.packet = keys.pop('packet_keys', [])
		self.version = keys.pop('version', 0)
		self.server_ip = keys.pop('ip', '37.187.29.8')
		self.server_ports = keys.pop('ports', [11801,12801,13801,1401])
		self.kwargs = keys

async def get_keys(client_id=0):
	data = {}
	payload = {"token": "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"}
	async with aiohttp.ClientSession() as session:                
		async with session.get("http://45.145.167.45:8080/jodis", params=payload) as response:
			data = await response.json()

	if data:
		keys = Keys(**data)

		if len(keys.packet) > 0 and len(keys.identification) > 0 and len(keys.msg) > 0:
			return keys

		raise Exception('Something goes wrong: A key is empty. {}'.format(data))
	else:
		raise Exception("Can't get the keys.")
