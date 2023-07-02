from aiotfm.enums import Community, ChatCommunity
from aiotfm import Client, Packet

from covid import get_info
from googletrans import Translator
from pasteee import new_paste
from utils import config, client_admins, client_id, public_commands, private_commands, \
	born_period, disconnect_mod_game, disconnect_mod_room, calc_pos, fix_pos, \
	update_maps_storage, maps

from struct import pack, unpack

import asyncio
import ujson
import records
import sys
import time

loop = asyncio.get_event_loop()
translator = Translator()

class Bot(Client):
	def __init__(self, community=Community[config.pop("community", "en")], auto_restart=True):
		super().__init__(community, auto_restart)

		self.stalked_players = {}

		self.mov_task = None

		self.display_chat = False
		self.map_protection = True
		self.is_bootcamp_room = False
		self.is_recording = False
		self.is_records_room = False
		self.is_playing = False
		self.can_accept_inv = True
		self.can_play = True
		self.can_press_callback = False
		self.can_die = True

		self.first_stalked_player = ""
		self.stalked_from_list = ""
		self.elim_target = ""

		self.last_record_time = 666

		self.born_period = born_period
		self.disconnect_mod_room = disconnect_mod_room
		self.disconnect_mod_game = disconnect_mod_game

	def cancel_mov_task(self):
		if self.mov_task is not None:
			if not self.mov_task.cancelled():
				self.mov_task.cancel()
			self.mov_task = None

	async def save_movement(self, player, obj, movement_type):
		if self.stalked_players[player]["last_movement_time"] == 0:
			self.stalked_players[player]["last_movement_time"] = time.time()
		_time = time.time() - self.stalked_players[player]["last_movement_time"]
		self.stalked_players[player]["last_movement_time"] = time.time()
		self.stalked_players[player]["map_movements"].append([obj, movement_type, _time])

	async def del_map(self, author, code):
		code = "@" + code if "@" not in code else code
		if code not in maps:
			return

		loop.create_task(update_maps_storage(code, author = author, delete = True))

	async def _cheese(self):
		if self._room.map.xml:
			cheese_pos = self._room.map.cheese_pos
			for key in cheese_pos:
				return await self.bulle.send(Packet.new(5, 19).write32(self._room.round_code).write16(key["X"]).write16(key["Y"]).write24(15))

	async def _win(self):
		if self._room.map.xml:
			hole_pos = self._room.map.hole_pos
			for key in hole_pos:
				hole_color = key["CT"] if "CT" in key else 0
				return await self.bulle.send(Packet.new(5, 18).write8(hole_color).write32(self._room.round_code).write32(self._room.map.code).write16(15).write16(key["X"]).write16(key["Y"]))

	async def _mort(self):
		await self.bulle.send(Packet.new(4, 5).write32(self._room.round_code).write8(0))

	async def play_map(self, sequence=None):
		if not self.is_playing:
			return
		if not self.is_bootcamp_room:
			await asyncio.sleep(self.born_period)

		cheese_pos, hole_pos = self._room.map.cheese_pos, self._room.map.hole_pos
		round_code = self._room.round_code

		move = 0
		_sequence = ujson.loads(sequence)
		for i in _sequence:
			time_sleep = i[2] if len(i) >= 3 else 1
			
			if not isinstance(i[0], dict):
				_bytes = i[0][2:].encode().decode('unicode-escape').encode()

			step = i[1]
			if step == 'walk':
				movingRight, movingLeft = i[0]['movingRight'], i[0]['movingLeft']
				x, vx = i[0]['x'], i[0]['vx']

				if self._room.map.is_reversed:
					x = calc_pos(800 - fix_pos(unpack(">l", pack(">L", x))[0]))

					if movingRight or movingLeft:
						movingLeft, movingRight = not movingLeft, not movingRight
					vx = -unpack(">h", pack(">H", vx))[0] if movingRight else -vx
				packet = Packet.new(4, 4).write32(round_code).writeBool(movingRight).writeBool(movingLeft).write32(x).write32(i[0]['y']).write16(vx).write16(i[0]['vy']).writeBool(i[0]['jumping']).write8(i[0]['frame']).write8(i[0]['onPortal'])
			elif i[1] in ['crouch', 'duck']:
				packet = Packet.new(4, 9).write8(_bytes[2])
			elif step == 'emote':
				packet = Packet.new(8, 1).write8(_bytes[2]).write32(0)
				if len(_bytes) > 8:
					_len = _bytes[8]
					flag = unpack(f'!{_len}s', _bytes[9:9+_len])[0]
					packet.writeString(flag)

			if move > 0:
				await asyncio.sleep(time_sleep)
			if step == "cheese":
				await self._cheese()
			elif step in ["hole", "win"]:
				await self._win()
			else:
				await self.bulle.send(packet)
			move += 1

		self.is_playing = False

	async def on_login_ready(self, online_players, *a):
		print(f"Players online: {online_players}")

		config["encrypted"] = False
		time.sleep(2)#letting to verify
		await self.login(**config)

	async def on_ready(self):
		print("Connected to the community platform")
	
	async def on_room_message(self, _message):
		author = str(_message.author)
		message = _message.content
		args = message.split()

		print(f"[Room][{author}] {message}")

		if author in client_admins:
			level = client_admins[author]
			if level == 0:
				if args[0] == "!del":
					code = str(self._room.map.code)
					if len(args) > 1:
						code = args[1]
					return await self.del_map(author, code)
	
	async def on_whisper(self, _message):
		author = str(_message.author)
		commu = ChatCommunity(_message.community).name
		message = _message.content
		args = message.split()

		print(f"[Whisper][{commu}][{author}] {message}")

		# Whispers commands
		if author in client_admins:
			level = client_admins[author]
			# Level 0 Admins only
			if level == 0:
				if args[0] == "!ban":
					if len(args) > 1:
						await self.sendCommand('ban ' + args[1])
						return await _message.reply("Voted to ban "+args[1])
					return await _message.reply("Who to ban? :/")
				elif args[0] == "!target":
					if len(args) > 1:
						self.elim_target = args[1]
					return
				elif args[0] == "!callback":
					self.can_press_callback = not self.can_press_callback
					return
				elif args[0] == "!room":
					if len(args) > 1:
						room = ' '.join(args[1:])
						return await self.joinRoom(room)
					return await _message.reply(self._room.name)
				elif args[0] == "!pwroom":
					if len(args) == 1:
						return
					return await self.joinRoom(" ".join(args[2:]), args[1])
				elif args[0] == "!canplay":
					self.can_play, self.is_playing = not self.can_play, False
					return self.cancel_mov_task()
					return await self._mort()
				elif args[0] == "!candie":
					self.can_die = not self.can_die
					return
				elif args[0] == "!cheese":
					return await self._cheese()
				elif args[0] == "!win":
					return await self._win()
				elif args[0] == "!del":
					code = str(self._room.map.code)
					if len(args) > 1:
						code = args[1]
					return await self.del_map(author, code)
				elif args[0] == "!inv":
					self.can_accept_inv = not self.can_accept_inv
					return

			# Level 0+ Admins
			if level >= 0:
				if args[0] == "!lua":
					if len(args) > 1:
						if "pastebin" not in args[1]:
							return await _message.reply("[Error] Code must be hosted on Pastebin")
						await self.run_code(args[1])
					return
				elif args[0] in ["!come", "!follow", "!seg"]:
					target = author
					if len(args) > 1:
						target = args[1]

					tribe = await self.getTribe(disconnected=False)
					if tribe is not None:
						member = tribe.get_member(target)
						if member is not None and member.room is not None:
							return await self.joinRoom(member.room)
					if self.friends is not None:
						friend = self.friends.get_friend(target)
						if friend is not None and friend.room is not None:
							return await self.joinRoom(friend.room)
					return await _message.reply("Player not found")
				elif args[0] == "!commu":
					commu = 1
					if len(args) > 1:
						try:
							commu = Community(int(args[1]))
						except:
							commu = Community[args[1]]
					self.community = commu
					return loop.create_task(self.restart())
				elif args[0] == "!say":
					return await self.sendRoomMessage(" ".join(args[1:]))
				elif args[0] in ["!th", "!house"]:
					return await self.enterTribe()
				elif args[0] == "!lua":
					if len(args) == 1:
						return
					return await self.run_code(args[1])
				elif args[0] == "!pm":
					if len(args) == 1:
						return
					return await self.whisper(args[1], " ".join(args[2:]))
				elif args[0] == "!tm":
					if len(args) == 1:
						return
					return await self.sendTribeMessage(" ".join(args[1:]))
				elif args[0] == "!mort":
					return await self._mort()

	async def on_tribe_message(self, author, message):
		print(f"[Tribe][{author}] {message}")
			
	async def on_joined_room(self, room):
		self.is_bootcamp_room, self.is_records_room = "bootcamp" in room.name.lower(), "#records" in room.name.lower()
		self.is_recording = False
		self.first_stalked_player = ""
		self.stalked_players.clear()

		print("Joined to room: " + room.name)

	async def on_tribe_inv(self, author, tribe):
		print(author + ' invited to ' + tribe + ' tribe house')
		if self.can_accept_inv:
			await self.enterInvTribeHouse(author)

	async def on_text_area(self, _id, text, callback_list):
		if callback_list:
			for callback in callback_list:
				packet = Packet.new(29, 21).write32(_id)

				_callback = callback.lower()
				if 'particip' in _callback or 'ent' in _callback or 'join' in _callback:
					return await self.bulle.send(packet.writeString(callback))
				if self.elim_target:
					if self.elim_target.lower() in _callback or self.elim_target.lower() in text.lower():
						return await self.bulle.send(packet.writeString(callback))
				if self.can_press_callback:
					await self.bulle.send(packet.writeString(callback))

	async def on_player_send_emoticon(self, player, emoticon):
		if self.is_playing or self.is_recording or player.username not in self.stalked_players:
			return

		packet = Packet.new(8, 5).write8(int(emoticon)).write32(0)
		if self.first_stalked_player == player.username:
			await self.bulle.send(packet)

	async def on_player_movement(self, player):
		if self.is_playing or player.username not in self.stalked_players:
			return
		if self.is_recording:
			#await self.bulle.send(Packet.new(8, 5).write8(5).write32(0))
			prop = {
				'movingLeft': player.moving_left,
				'movingRight': player.moving_right,
				'x': player.x,
				'y': player.y,
				'vx': player.vx,
				'vy': player.vy,
				'jumping': player.jumping,
				'frame': player.frame,
				'onPortal': player.on_portal
			}
			return await self.save_movement(player.username, prop, "walk")

		packet = Packet.new(4, 4).write32(self._room.round_code)
		packet.writeBool(player.moving_right).writeBool(player.moving_left)
		packet.write32(player.x).write32(player.y)
		packet.write16(player.vx).write16(player.vy)
		packet.writeBool(player.jumping)
		packet.write8(player.frame).write8(player.on_portal)
		if self.first_stalked_player == player.username:
			await self.bulle.send(packet)

			s_player = self._room.get_player(username=self.username)
			if s_player.hasCheese:
				return
			if player.hasCheese: 
				await self._cheese()

	async def on_player_duck(self, player):
		if self.is_playing or player.username not in self.stalked_players:
			return

		packet = Packet.new(4, 9).writeBool(player.ducking)
		if self.is_recording:
			return await self.save_movement(player.username, str(bytes(packet)), "crouch")
		if self.first_stalked_player == player.username:
			await self.bulle.send(packet)

	async def on_emote(self, player, emote, flag):
		if self.is_playing or player.username not in self.stalked_players:
			return

		packet = Packet.new(8, 1).write8(emote).write32(0)
		if flag:
			packet.writeString(flag)

		if self.is_recording:
			return await self.save_movement(player.username, str(bytes(packet)), "emote")
		if self.first_stalked_player == player.username:
			await self.bulle.send(packet)

	async def on_player_cheese_state_change(self, player):
		if self.is_playing or player.username not in self.stalked_players:
			return
		if self._room.map.xml:
			cheese_pos = self._room.map.cheese_pos
			for key in cheese_pos:
				packet = Packet.new(5, 19).write32(self._room.round_code).write16(key["X"]).write16(key["Y"]).write24(15)
				if not self.is_recording:
					if self.first_stalked_player == player.username:
						await self.bulle.send(packet)
					return
				return await self.save_movement(player.username, str(bytes(packet)), "cheese")
		if self.first_stalked_player == player.username:
			await self.bulle.send(Packet.new(5, 19).write32(self._room.round_code).write16(fix_pos(player.x)).write16(fix_pos(player.y)).write24(15))
		
	async def on_player_won(self, player, order, player_time):
		if self.username == player.username:
			self.last_record_time = player_time
		if self.is_playing:
			return
		if player.username not in self.stalked_players:
			return
		if self._room.map.xml:
			hole_pos = self._room.map.hole_pos
			for key in hole_pos:
				hole_color = key["CT"] if "CT" in key else 0
				packet = Packet.new(5, 18).write8(hole_color).write32(self._room.round_code).write32(self._room.map.code).write16(15).write16(key["X"]).write16(key["Y"])
				if not self.is_recording:
					if self.first_stalked_player == player.username:
						await self.bulle.send(packet)
					return

				if self.is_bootcamp_room:
					if self._room.map.is_reversed:
						self.stalked_players[player.username]["map_movements"] *= 0
						return await self.sendRoomMessage("!me Run ignored. Map is reversed")
					if self.last_record_time < player_time:
						self.stalked_players[player.username]["map_movements"] *= 0
						return
					self.last_record_time = player_time

				await self.save_movement(player.username, str(bytes(packet)), "hole")

				loop.create_task(update_maps_storage("@" + str(self._room.map.code),
					(ujson.dumps(self.stalked_players[player.username]["map_movements"], ensure_ascii=False),
					self._room.map.xml)
				))

				self.stalked_players[player.username]["map_movements"] *= 0
				break
		else:
			if self.first_stalked_player == player.username:
				await self.bulle.send(Packet.new(5, 18).write8(0).write32(self._room.round_code).write32(self._room.map.code).write16(15).write16(fix_pos(player.x)).write16(fix_pos(player.y)))

	async def on_player_died(self, player):
		if self.is_playing or player.username not in self.stalked_players:
			return
		if self.is_recording:
			self.stalked_players[player.username]["map_movements"] *= 0
			return
		if not self.can_die:
			return
		if self.first_stalked_player == player.username:
			await self._mort()

	async def on_player_left(self, player):
		await self.dispatch("player_died", player)

	async def on_friend_room_change(self, friend, room):
		if self.stalked_from_list.lower() == friend.lower():
			await self.joinRoom(room)

	async def on_player_join(self, player):
		if "#0010" in str(player):
			if self.disconnect_mod_room:
				sys.exit("Mod online in room")

	async def on_player_update(self, _, player):
		if self.username != player.username or not self.can_play or self.is_playing:
			return
		self.cancel_mov_task()
		if self.is_bootcamp_room and not self.is_records_room:
			map_code = "@" + str(self._room.map.code)
			if map_code in maps:
				self.is_playing = True
				self.mov_task = asyncio.ensure_future(self.play_map(sequence=maps[map_code][0]))

	async def on_staff_list(self, staff_list):
		if f"[{self.community.name}]" in staff_list:
			sys.exit("Mod online in community")

	async def on_map_change(self, new_map):
		self.cancel_mov_task()

		self.last_record_time = 666
		self.is_playing = False

		for player in self.stalked_players:
			self.stalked_players[player]["map_movements"] *= 0
			self.stalked_players[player]["last_movement_time"] = 0

		if self.disconnect_mod_game:
			await self.sendCommand("mod")

		map_code = "@" + str(new_map.code)
		if new_map.xml:
			if self.can_play:
				if map_code in maps:
					sequence = maps[map_code][0]
					if maps[map_code][1] == new_map.xml:
						self.is_playing = True
						self.mov_task = asyncio.ensure_future(self.play_map(sequence=sequence))
		else:
			print(f"{map_code} XML not identified")

client = Bot()

@client.command
async def add(ctx, player):
	await client.friends.add(player)

@client.command
async def friend(ctx, player):
	await client.friends.add(player)

@client.command
async def commu(ctx, commu):
	if str(ctx.author) in client_admins:
		commu = str(commu)

		try:
			try:
				client.community = Community(int(commu))
			except ValueError:
				client.community = Community[commu]
		except KeyError:
			client.community = Community.br

		loop.create_task(client.restart())

@client.command
async def covid(ctx, country, *a):
	if not private_commands:
		return
	if not public_commands:
		if str(ctx.author) not in client_admins:
			return

	if ctx.platform == "room":
		if not client.is_records_room:
			if str(ctx.author) not in client_admins:
				return
	if ctx.author == country:
		country = "world"
	info = await get_info(country)
	if info:
		await ctx.reply(info)

@client.command
async def lsmap(ctx, *a):
	prefix = ""
	if ctx.platform == "room":
		if client.is_records_room:
			prefix = "!me "

	if str(ctx.author) in client_admins:
		await ctx.reply(f"{prefix}{len(maps)} total maps")

@client.command
async def rec(ctx, code, version=""):
	if not private_commands:
		return
	if not public_commands:
		if str(ctx.author) not in client_admins:
			return

	if ctx.platform == "room":
		if not client.is_records_room:
			if str(ctx.author) not in client_admins:
				return
	prefix = ""
	if client.is_records_room:
		prefix = "!me " if ctx.platform == "room" else ""
				
	code = client._room.map.code if ctx.author == code else code
	await ctx.reply(prefix + records.get_map_record(code, version))

@client.command
async def setfrom(ctx, code):
	if str(ctx.author) in client_admins:
		code = "@" + code if "@" not in code else code
		if code not in maps:
			return

		current_map = "@" + str(client._room.map.code)
		loop.create_task(update_maps_storage(current_map,
			(maps[code][0], client._room.map.xml)
		))

@client.command
async def translate(ctx, src, dest, *a):
	if not private_commands:
		return
	if not public_commands:
		if str(ctx.author) not in client_admins:
			return

	if ctx.platform == "room":
		if not client.is_records_room:
			if str(ctx.author) not in client_admins:
				return
	prefix = ""
	if client.is_records_room:
		prefix = "!me " if ctx.platform == "room" else ""

	result = translator.translate(" ".join([*a]), src=src, dest=dest)
	await ctx.reply(prefix + result.text)

@client.command
async def xml(ctx, code):
	if not private_commands:
		return
	if not public_commands:
		if str(ctx.author) not in client_admins:
			return

	if ctx.platform == "room":
		if not client.is_records_room:
			if str(ctx.author) not in client_admins:
				return

	prefix = ""
	if client.is_records_room:
		prefix = "!me " if ctx.platform == "room" else ""
		if ctx.author != code:
			try:
				await client.sendRoomMessage("!np " + code)
				await client.wait_for("on_map_change", timeout=3)
			except asyncio.TimeoutError:
				return

	if client._room.map.xml:
		map_code = "@" + str(client._room.map.code)
		url = await new_paste(client._room.map.xml)
		return await ctx.reply(f"{prefix}{map_code} XML: {url}")
	await ctx.reply("[Error] XML not identified")
	
@client.command
async def rmap(ctx, *a):
	if str(ctx.author) in client_admins:
		if client.is_records_room:
			await client.sendRoomMessage(f"!np {client._room.map.code}")

@client.command
async def start(ctx, *a):
	if str(ctx.author) in client_admins:
		if client.is_records_room:
			client.is_playing, client.is_recording = False, True

@client.command
async def stop(ctx, *a):
	if str(ctx.author) in client_admins:
		client.is_recording = False
		client.first_stalked_player = ""
		client.stalked_players.clear()
		client.cancel_mov_task()

@client.command
async def stalk(ctx, *a):
	if str(ctx.author) in client_admins:
		for target in [*a]:
			target = str(target)
			if not client.first_stalked_player:
				client.first_stalked_player = target
			client.stalked_players[target] = {
				"map_movements": [],
				"last_movement_time": 0
			}
		stalked_players = ", ".join(client.stalked_players)
		print(f"[{str(ctx.author)}] Bot stalking {stalked_players}")

@client.command
async def stalkfriend(ctx, player):
	if str(ctx.author) in client_admins:
		client.stalked_from_list = str(player)
		
if __name__ == "__main__":
	loop.create_task(client.start(client_id))
	loop.run_forever()
