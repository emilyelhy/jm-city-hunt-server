from flask import Flask, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/', methods=['GET'])
def test():
    print("[Flask server.py] GET path /")
    return {"res": "success"}

@app.route('/login', methods=['POST'])
def login():
    print("[Flask server.py] POST path /login")
    if request.json['groupNo'] == "1" and request.json['password'] == "abc":
        return {"res": "success"}
    else:
        return {"res": "fail"}

if __name__ == "__main__":
    app.run(host="192.168.118.143", port=5000, debug=True)