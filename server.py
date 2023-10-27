from pymongo import MongoClient
from flask import Flask, request
from flask_cors import CORS
from flask_bcrypt import Bcrypt
import math
import os

app = Flask(__name__)
bcrypt = Bcrypt(app)
CORS(app)

MONGODB_URI = os.environ.get("MONGODB_URI")
MONGODB_DB_NAME = os.environ.get("MONGODB_DB_NAME")
MONGODB_COLLECTION = os.environ.get("MONGODB_COLLECTION")
print("[Flask server.py] Flask server connected to " + str(MONGODB_URI))

# return true if the distance between 2 points is less than 100m
def validate_distance(lat1, lon1, lat2, lon2):
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

# for testing connection with server
@app.route('/', methods=['GET'])
def test():
    print("[Flask server.py] GET path /")
    return {"res": True}

# handling login requests from react
# param: object of groupNo and password
# return: true on successful login and false for failed login
@app.route('/login', methods=['POST'])
def login():
    print("[Flask server.py] POST path /login")
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB_NAME]
    datum = db[MONGODB_COLLECTION]
    group = datum.find_one({"groupNo": request.json["groupNo"]})
    client.close()
    if(group):
        if(bcrypt.check_password_hash(group["password"], request.json["password"])):
            return {"res": True}
    return {"res": False}

# handling create user requests from REST API directly
# param: list named as userList containing all user's groupNo and password as object
# return: true on successful user creation and false on failed creation
@app.route('/createuser', methods=['POST'])
def create_user():
    print("[Flask server.py] POST path /createuser")
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB_NAME]
    datum = db[MONGODB_COLLECTION]
    userList = request.json["userList"].copy()
    for u in userList:
        u["password"] = bcrypt.generate_password_hash(u["password"])
    print(userList)
    res = datum.insert_many(userList)
    client.close()
    if res:
        return {"res": True}
    return {"res": False}

# handling password changing request from react
# param: object of groupNo, oldPassword, and newPassword
# return: true on successful update and false on failed update
@app.route('/changepassword', methods=['POST'])
def change_password():
    print("[Flask server.py] POST path /changepassword")
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB_NAME]
    datum = db[MONGODB_COLLECTION]
    group = datum.find_one({"groupNo": request.json["groupNo"]})
    if (group == None):
        return {"res": False}
    if (bcrypt.check_password_hash(group["password"], request.json["oldPassword"]) == False):
        return {"res": False}
    datum.find_one_and_update({"groupNo": request.json["groupNo"]}, {"$set": {"password": bcrypt.generate_password_hash(request.json["newPassword"])}})
    client.close()
    return {"res": True}

if __name__ == "__main__":
    app.run(host="192.168.118.143", port=5000, debug=True)