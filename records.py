import asyncio

import gspread
gc = gspread.service_account(filename="service_account_credentials.json")

wr_list = {"new": {}, "old": {}}

async def update_wr_list():
	ver_key = "old"
	sheet_key = "1l3D-tmUAgwqNPjR3qa1rKqNkNYImPLC3dhgHUD3gLjo"

	for n in range(2):
		tfmrs = gc.open_by_key(sheet_key)

		for cat in ["P3", "P13", "P17"]:
			left_side = tfmrs.values_batch_get([f"{cat}!B:B", f"{cat}!C:C", f"{cat}!D:D"])
			maps = left_side["valueRanges"][0]["values"]
			players = left_side["valueRanges"][1]["values"]
			times = left_side["valueRanges"][2]["values"]

			# Reverse maps
			right_side = tfmrs.values_batch_get([f"{cat}!J:J", f"{cat}!K:K", f"{cat}!L:L"])
			rmaps = right_side["valueRanges"][2]["values"]
			rplayers = right_side["valueRanges"][1]["values"]
			rtimes = right_side["valueRanges"][0]["values"]

			last_map_key, last_player_key = 1, 2
			while last_map_key < len(maps):
				if last_player_key > len(players):
					break

				if maps[last_map_key] and "@" in maps[last_map_key][0]:
					wr_list[ver_key][maps[last_map_key][0]] = {}

					if players[last_player_key] and times[last_player_key]:
						wr_list[ver_key][maps[last_map_key][0]]["left"] = (
							players[last_player_key][0],
							times[last_player_key][0]
						)

					if right_side is not None:
						if last_map_key <= len(rmaps) and last_player_key <= len(rplayers):
							if rplayers[last_player_key] and rtimes[last_player_key]:
								wr_list[ver_key][maps[last_map_key][0]]["right"] = (
									rplayers[last_player_key][0],
									rtimes[last_player_key][0]
								)

				last_map_key += 8
				last_player_key += 8

		ver_key = "new"
		sheet_key = "1xoPZXT5apgKm1Z5J-YEv-sXTQ6BjB0vnPgrWLxhRpaU"

	print("[Records] World records list has been updated.")

def get_map_record(map_code, version=""):
	target = wr_list["old"] if version else wr_list["new"]
	prefix = "[Old Spreadsheet] " if version else "[New Spreadsheet] "

	map_code = str(map_code)
	if "@" not in map_code:
		map_code = "@" + map_code
	if map_code in target:
		times = [f"{time[0]} - {time[1]}" for time in target[map_code].values()]

		if "left" not in target[map_code].keys():
			map_code = map_code + " (reverse)"

		if times:
			return f"{prefix}{map_code} best time » {'/'.join(times)}"
		return f"{prefix}There is no record"
	return f"{prefix}Map not registered"

def map_list_comparison(_dict):
	return [_map for _map in wr_list["new"] if _map not in _dict]

loop = asyncio.get_event_loop()
loop.create_task(update_wr_list())