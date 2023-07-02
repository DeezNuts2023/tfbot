import base64
import ujson
import zlib

def json_zip(j):
	return base64.b64encode(
		zlib.compress(
			ujson.dumps(j).encode("utf-8")
		)
	)

def json_unzip(j):
	return ujson.loads(
		zlib.decompress(
			base64.b64decode(j)
		)
	)