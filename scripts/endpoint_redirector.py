from flask import Flask
from flask import request
from flask_cors import CORS,cross_origin
import requests
app = Flask(__name__)
CORS(app) # This will enable CORS for all routes

REDIRECT_TO = "https://osu.ppy.sh"
#samREDIRECT_TO = "http://rpg.dut-info.cf"

HTTP_METHODS = ['GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'CONNECT', 'OPTIONS', 'TRACE', 'PATCH']


@app.route('/', defaults={'path': ''}, methods=HTTP_METHODS)
@app.route('/<path:path>', methods=HTTP_METHODS)
@cross_origin()
def catch_all(path):
	# print(request.headers)
	req_exec = eval("requests."+request.method.lower())
	try:
		headers = {
			"User-Agent": request.headers["User-Agent"],
			"Authorization": request.headers["Authorization"]
		}
	except Exception:
		headers = {
			"User-Agent": request.headers["User-Agent"]
		}

	data = request.values
	try:
		data = json.loads(request.data)
	except Exception as e:
		pass

	r = req_exec(REDIRECT_TO + "/" +path, data = data, headers=headers)
	open(str(path).replace("/","_")+".txt","w").write(r.text)
	return r.text


app.run(host="0.0.0.0",debug=False,port=6868)
