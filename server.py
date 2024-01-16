from pymongo import MongoClient
from flask import Flask, request
from flask_cors import CORS
from flask_bcrypt import Bcrypt
import math
import os
import glob
from PIL import Image
import io
import matplotlib.pyplot as plt
import base64

app = Flask(__name__)
bcrypt = Bcrypt(app)
CORS(app)

MONGODB_URI = os.environ.get("MONGODB_URI")
MONGODB_DB_NAME = os.environ.get("MONGODB_DB_NAME")
MONGODB_COLLECTION_USR = os.environ.get("MONGODB_COLLECTION_USR")
MONGODB_COLLECTION_CKPT = os.environ.get("MONGODB_COLLECTION_CKPT")
MONGODB_COLLECTION_SEQ = os.environ.get("MONGODB_COLLECTION_SEQ")
MONGODB_COLLECTION_IMG = os.environ.get("MONGODB_COLLECTION_IMG")

CKPT_RANGE = 0.05 # in km

# return distance of 2 coordinates in km
def cal_distance(lat1, lon1, lat2, lon2):
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
    print("[Flask server.py] cal_distance result in (km):", distance)
    return distance

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
    datum = db[MONGODB_COLLECTION_USR]
    group = datum.find_one({"groupNo": request.json["groupNo"]})
    client.close()
    if(group):
        if(bcrypt.check_password_hash(group["password"], request.json["password"])):
            return {"res": True}
    return {"res": False}

# handling create user requests from REST API directly
# param: list named as userList containing all user's groupNo, password, type, and memberList as object
# return: true on successful user creation and false on failed creation
@app.route('/createuser', methods=['POST'])
def create_user():
    print("[Flask server.py] POST path /createuser")
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB_NAME]
    datum = db[MONGODB_COLLECTION_USR]
    userList = request.json["userList"].copy()
    for u in userList:
        u["password"] = bcrypt.generate_password_hash(u["password"])
        u["completedTask"] = []
        u["visitedCkpts"] = []
    print(userList)
    res = datum.insert_many(userList)
    client.close()
    if res:
        return {"res": True}
    return {"res": False}

# return the next available group no
# param: N.A.
# return: object of groupNo
@app.route('/groupNo', methods=['GET'])
def next_available_groupNo():
    print("[Flask server.py] GET path /groupNo")
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB_NAME]
    datum = db[MONGODB_COLLECTION_USR]
    count = datum.count_documents({})
    client.close()
    return {"groupNo": count + 1}

# return the memberList to react
# param: object of groupNo
# return: object of memberList
@app.route('/memberlist', methods=['POST'])
def return_member_list():
    print("[Flask server.py] POST path /memberlist")
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB_NAME]
    datum = db[MONGODB_COLLECTION_USR]
    user = datum.find_one({"groupNo": request.json["groupNo"]})
    client.close()
    return {"memberList": user["members"]}

# handling member changing request from react
# param: object of memberList and groupNo
# return: true on successful update and false on failed update
@app.route('/updatemember', methods=['POST'])
def update_member():
    print("[Flask server.py] POST path /updatemember")
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB_NAME]
    datum = db[MONGODB_COLLECTION_USR]
    datum.find_one_and_update({"groupNo": request.json["groupNo"]}, {"$set": {"members": request.json["memberList"]}})
    client.close()
    return {"res": True}

# handling password changing request from react
# param: object of groupNo, oldPassword, and newPassword
# return: true on successful update and false on failed update
@app.route('/changepassword', methods=['POST'])
def change_password():
    print("[Flask server.py] POST path /changepassword")
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB_NAME]
    datum = db[MONGODB_COLLECTION_USR]
    group = datum.find_one({"groupNo": request.json["groupNo"]})
    if (group == None):
        return {"res": False}
    if (bcrypt.check_password_hash(group["password"], request.json["oldPassword"]) == False):
        return {"res": False}
    datum.find_one_and_update({"groupNo": request.json["groupNo"]}, {"$set": {"password": bcrypt.generate_password_hash(request.json["newPassword"])}})
    client.close()
    return {"res": True}

# upload all images in IMG folder to MongoDB [Can only be used on computer locally with /IMG folder existing]
# param: N.A.
# return: true on successful upload and false on failed upload
@app.route('/uploadimage', methods=['GET'])
def upload_image():
    print("[Flask server.py] GET path /uploadimage")
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB_NAME]
    datum = db[MONGODB_COLLECTION_IMG]
    images = []
    for k in glob.glob('IMG/*.png'):
        im = Image.open(k)
        kn, _ = os.path.splitext(os.path.basename(k))
        image_bytes = io.BytesIO()
        im.save(image_bytes, format='PNG')
        prevImageObj = {}
        for image in images:
            if image["ckptNo"] == kn.split("-")[0]:
                prevImageObj = image
        if prevImageObj:
            prevImageObj['data'][kn.split("-")[1]] = image_bytes.getvalue()
        else:
            image = {
                'data':  {kn.split("-")[1]: image_bytes.getvalue()},
                'ckptNo': kn.split("-")[0]
            }
            images.append(image)
    res = datum.insert_many(images)
    client.close()
    if res:
        return {"res": True}
    return {"res": False}

# temp use until front end is updated for image transmission
@app.route('/showimage', methods=['GET'])
def show_image():
    print("[Flask server.py] GET path /showimage")
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB_NAME]
    datum = db[MONGODB_COLLECTION_IMG]
    image = datum.find_one({"ckptNo": "1"})
    client.close()
    pil_img = Image.open(io.BytesIO(image['data']))
    plt.imshow(pil_img)
    plt.show()
    return {"res": True}

# remove all saved images on MongoDB
# param: N.A.
# return: true on successful deletion and false on failed deletion
@app.route('/clearimage', methods=['GET'])
def clear_image():
    print("[Flask server.py] GET path /clearimage")
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB_NAME]
    datum = db[MONGODB_COLLECTION_IMG]
    datum.drop()
    client.close()
    return {"res": True}

# add checkpoint(s) data to MongoDB
# param: list of object "ckptList" of ckptNo, location {latitude, longitude}, clue, taskContent
# return: true on successful addition and false on failed addition
@app.route('/addckpt', methods=['POST'])
def add_ckpt():
    print("[Flask server.py] POST path /addckpt")
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB_NAME]
    datum = db[MONGODB_COLLECTION_CKPT]
    res = datum.insert_many(request.json["ckptList"])
    client.close()
    if res:
        return {"res": True}
    return {"res": False}

# return the current checkpoint data to React
# param: object of groupNo
# return: ckptNo, location {latitude, longitude}, clue, taskContent if current ckpt exists, {} if all tasks are completed
@app.route('/currentckpt', methods=['POST'])
def return_current_checkpoint():
    print("[Flask server.py] POST path /currentckpt")
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB_NAME]
    user_datum = db[MONGODB_COLLECTION_USR]
    seq_datum = db[MONGODB_COLLECTION_SEQ]
    ckpt_datum = db[MONGODB_COLLECTION_CKPT]
    # get corresponding info from user collection with groupNo
    user = user_datum.find_one({"groupNo": request.json["groupNo"]})
    # get sequence from sequence collection with seqID
    sequence = seq_datum.find_one({"seqID": user["seqID"]})
    # compare sequence and visitedCkpts to get the current ckptNo
    if len(user["visitedCkpts"]) == 0:
        currentCkptNo = sequence["sequence"][0]
    # cases when all tasks are completed
    elif len(user["visitedCkpts"]) == len(sequence["sequence"]):
        client.close()
        return {}
    else:
        currentCkptIndex = sequence["sequence"].index(user["visitedCkpts"][len(user["visitedCkpts"]) - 1]) + 1
        currentCkptNo = sequence["sequence"][currentCkptIndex]
    # get ckpt detail from Checkpoint collection with ckptNo
    ckpt = ckpt_datum.find_one({"ckptNo": currentCkptNo})
    # return ckptNo, location, clue, taskContent to React
    client.close()
    return {"ckptNo": currentCkptNo, "location": ckpt["location"], "clue": ckpt["clue"], "taskContent": ckpt["taskContent"]}

# return the required image to React
# param: object of ckptNo
# return: image in byte with base64 encoding
@app.route('/getimage', methods=['POST'])
def return_image():
    print("[Flask server.py] POST path /getimage")
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB_NAME]
    datum = db[MONGODB_COLLECTION_IMG]
    image = datum.find_one({"ckptNo": request.json["ckptNo"]})
    client.close()
    return {"res": base64.b64encode(image["data"]).decode("utf-8")}

# return all images for all ckpts of a certain userType to React
# param: object of userType
# return: object of list of object with name imageList (image in byte with base64 encoding)
@app.route('/getallimage', methods=['POST'])
def return_all_image():
    print("[Flask server.py] POST path /getallimage")
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB_NAME]
    datum = db[MONGODB_COLLECTION_IMG]
    images = list(datum.find({}, {'_id': False}).sort("ckptNo").collation({"locale": "en_US", "numericOrdering": True}))
    imageList = images.copy()
    for idx, im in enumerate(imageList):
        im["data"] = base64.b64encode(images[idx]["data"][request.json["userType"]]).decode("utf-8")
    return {"imageList": imageList}

# determine whether the user is in the range of the checkpoint
# param: object of latitude, longitude, ckptNo and groupNo
# return: true and set visitedCkpts if the location is in range of the checkpoint, else false
@app.route('/validatelocation', methods=['POST'])
def validate_location():
    print("[Flask server.py] POST path /validatelocation")
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB_NAME]
    ckpt_datum = db[MONGODB_COLLECTION_CKPT]
    user_datum = db[MONGODB_COLLECTION_USR]
    current_ckpt = ckpt_datum.find_one({"ckptNo": request.json["ckptNo"]})
    user = user_datum.find_one({"groupNo": request.json["groupNo"]})
    if cal_distance(request.json["latitude"], request.json["longitude"], current_ckpt["location"][user["type"]]["latitude"], current_ckpt["location"][user["type"]]["longitude"]) > CKPT_RANGE:
        client.close()
        return {"res": False}
    temp_visitedCkpts = user["visitedCkpts"].copy()
    temp_visitedCkpts.append(request.json["ckptNo"])
    user_datum.find_one_and_update({"groupNo": request.json["groupNo"]}, {"$set": {"visitedCkpts": temp_visitedCkpts}})
    client.close()
    return {"res": True}

# return all ckpts in list in ascending order of ckptNo
# param: N.A.
# return: object of list of objects with name "ckptList"
@app.route('/allckpt', methods=['GET'])
def return_all_ckpt():
    print("[Flask server.py] GET path /allckpt")
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB_NAME]
    datum = db[MONGODB_COLLECTION_CKPT]
    ckptList = list(datum.find({}, {'_id': False}).sort("ckptNo").collation({"locale": "en_US", "numericOrdering": True}))
    client.close()
    return {"ckptList": ckptList}

# return all ckpts in safe mode (without location info) in list (ascending order of ckptNo)
# param: N.A.
# return: object of list of objects with name "ckptList"
@app.route('/allckptsafe', methods=['GET'])
def return_all_ckpt_safe():
    print("[Flask server.py] GET path /allckptsafe")
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB_NAME]
    datum = db[MONGODB_COLLECTION_CKPT]
    ckptList = list(datum.find({}, {'_id': False, 'location': False}).sort("ckptNo").collation({"locale": "en_US", "numericOrdering": True}))
    client.close()
    return {"ckptList": ckptList}

# return visitedCkpts and completedTasks of a certain group to React
# param: object of groupNo
# return: objects with 2 lists visitedCkpts & completedTasks
@app.route('/progress', methods=['POST'])
def progress():
    print("[Flask server.py] POST path /progress")
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB_NAME]
    datum = db[MONGODB_COLLECTION_USR]
    user = datum.find_one({"groupNo": request.json["groupNo"]})
    client.close()
    return {"completedTask": user["completedTask"], "visitedCkpts": user["visitedCkpts"]}

# return type of a certain group to React
# param: object of groupNo
# return: object of type
@app.route('/usertype', methods=['POST'])
def get_user_type():
    print("[Flask server.py] POST path /usertype")
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB_NAME]
    datum = db[MONGODB_COLLECTION_USR]
    user = datum.find_one({"groupNo": request.json["groupNo"]})
    client.close()
    return {"type": user["type"]}

# update coordinates of a certain ckpt
# param: object of ckptNo, type, latitude, and longitude
# return: true on successful update and false on failed update
@app.route('/calibrate', methods=['POST'])
def calibrate_ckpt():
    print("[Flask server.py] POST path /calibrate")
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB_NAME]
    datum = db[MONGODB_COLLECTION_CKPT]
    if request.json["type"] == "Y":
        datum.find_one_and_update({"ckptNo": request.json["ckptNo"]}, {"$set": {"location.Y": {"latitude": request.json["latitude"], "longitude": request.json["longitude"]}}})
    elif request.json["type"] == "F":
        datum.find_one_and_update({"ckptNo": request.json["ckptNo"]}, {"$set": {"location.F": {"latitude": request.json["latitude"], "longitude": request.json["longitude"]}}})
    elif request.json["type"] == "E":
        datum.find_one_and_update({"ckptNo": request.json["ckptNo"]}, {"$set": {"location.E": {"latitude": request.json["latitude"], "longitude": request.json["longitude"]}}})
    client.close()
    return {"res": True}

# return distance between current position and a specified ckpt to React
# param: object of ckptNo, latitude, and longitude
# return: object of distance
@app.route('/distance', methods=['POST'])
def return_distance():
    print("[Flask server.py] POST path /distance")
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB_NAME]
    datum = db[MONGODB_COLLECTION_CKPT]
    ckpt = datum.find_one({"ckptNo": request.json["ckptNo"]})
    client.close()
    distanceY = cal_distance(request.json["latitude"], request.json["longitude"], ckpt["location"]["Y"]["latitude"], ckpt["location"]["Y"]["longitude"])
    distanceF = cal_distance(request.json["latitude"], request.json["longitude"], ckpt["location"]["F"]["latitude"], ckpt["location"]["F"]["longitude"])
    distanceE = cal_distance(request.json["latitude"], request.json["longitude"], ckpt["location"]["E"]["latitude"], ckpt["location"]["E"]["longitude"])
    return {"distanceY": distanceY, "distanceF": distanceF, "distanceE": distanceE}

if __name__ == "__main__":
    app.run(host="192.168.118.193", port=5000, debug=True)