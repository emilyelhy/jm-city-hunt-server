from pymongo import MongoClient
from flask import Flask, request
from flask_cors import CORS
import math
import os

app = Flask(__name__)
CORS(app)

MONGODB_URI = os.environ.get("MONGODB_URI")
MONGODB_DB_NAME = os.environ.get("MONGODB_DB_NAME")
MONGODB_COLLECTION = os.environ.get("MONGODB_COLLECTION")
print("[Flask server.py] Flask server connected to " + MONGODB_URI)

# return true if the distance between 2 points is less than 100m
def validateDistance(lat1, lon1, lat2, lon2):
    # Radius of the Earth in km
    radius = 6371
    # Convert latitude and longitude to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    # Distance in km
    distance = radius * c
    if distance <= 0.1:
        return True
    return False

@app.route('/', methods=['GET'])
def test():
    print("[Flask server.py] GET path /")
    return {"res": "success"}

@app.route('/login', methods=['POST'])
def login():
    print("[Flask server.py] POST path /login")
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB_NAME]
    datum = db[MONGODB_COLLECTION]
    group = datum.find_one({"groupNo": request.json["groupNo"]})
    client.close()
    if(group):
        if(request.json["password"] == group["password"]):
            return {"res": "success"}
    return {"res": "fail"}

if __name__ == "__main__":
    app.run(host="192.168.118.143", port=5000, debug=True)