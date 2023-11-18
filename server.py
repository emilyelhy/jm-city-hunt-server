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

app = Flask(__name__)
bcrypt = Bcrypt(app)
CORS(app)

MONGODB_URI = os.environ.get("MONGODB_URI")
MONGODB_DB_NAME = os.environ.get("MONGODB_DB_NAME")
MONGODB_COLLECTION_USR = os.environ.get("MONGODB_COLLECTION_USR")
MONGODB_COLLECTION_CKPT = os.environ.get("MONGODB_COLLECTION_CKPT")
MONGODB_COLLECTION_SEQ = os.environ.get("MONGODB_COLLECTION_SEQ")
MONGODB_COLLECTION_IMG = os.environ.get("MONGODB_COLLECTION_IMG")
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
    datum = db[MONGODB_COLLECTION_USR]
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
    datum = db[MONGODB_COLLECTION_USR]
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
    datum = db[MONGODB_COLLECTION_USR]
    group = datum.find_one({"groupNo": request.json["groupNo"]})
    if (group == None):
        return {"res": False}
    if (bcrypt.check_password_hash(group["password"], request.json["oldPassword"]) == False):
        return {"res": False}
    datum.find_one_and_update({"groupNo": request.json["groupNo"]}, {"$set": {"password": bcrypt.generate_password_hash(request.json["newPassword"])}})
    client.close()
    return {"res": True}

# Upload all images in IMG folder to MongoDB [Can only be used on computer locally with /IMG folder existing]
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
        image = {
            'data': image_bytes.getvalue(),
            'ckptNo': kn
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

# Remove all saved images on MongoDB
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

# Add checkpoint(s) data to MongoDB
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

# Return the current checkpoint data to React
# param: groupNo
# return: ckptNo, location {latitude, longitude}, clue, taskContent, image
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
    sequence = seq_datum.find_one({"seqID": user.seqID})
    # compare sequence and completedTasks to get the current ckptNo
    if len(user.completedTasks) == 0:
        currentCkptNo = sequence.sequence[0]
    # cases when all tasks are completed
    elif len(user.completedTasks) == len(sequence.sequence):
        return {"res": False}
    else:
        currentCkptNo = sequence.sequence[sequence.sequence.index(user.completedTasks[len(user.completedTasks) - 1]) + 1]
    # get ckpt detail from Checkpoint collection with ckptNo
    ckpt = ckpt_datum.find_one({"ckptNo": currentCkptNo})
    # return ckptNo, location, clue, taskContent to React
    client.close()
    return {"ckptNo": currentCkptNo, "location": ckpt.location, "clue": ckpt.clue, "taskContent": ckpt.taskContent}

# Return the required image to React
# param: ckptNo
# return: image
@app.route('/getimage', methods='POST')
def return_image():
    print("[Flask server.py] POST path /getimage")
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB_NAME]
    datum = db[MONGODB_COLLECTION_IMG]
    image = datum.find_one({"ckptNo": request.json["ckptNo"]})
    request.headers["content-type"] = "image/png"
    return {"res": image.data}

if __name__ == "__main__":
    app.run(host="192.168.118.143", port=5000, debug=True)