import face_recognition
import cv2
import time
import numpy as np
import redis
import pickle
import os
import json
import tornado
from tornado.options import define, options
from db_utils import *

# postgreshost = '127.0.0.1'
# redishost = '127.0.0.1'
postgreshost  = 'postgres'
redishost = 'redis'

MAX_FPS = 100

with open('secret.json','r') as f:
    db_data = json.load(f)
    define("db_host", default=postgreshost, help="database host")
    define("db_port", default=5432, help="database port")
    define("db_database", default=db_data['Database'], help="database name")
    define("db_user", default=db_data['Username'], help="database user")
    define("db_password", default=db_data['Password'], help="database password")

define("port", default=8000, help="run on the given port", type=int)
define("db_delete", default=True, help="Delte all the tables in db")

def decode_image(imbytes):
    jpeg = np.asarray(bytearray(imbytes), dtype="uint8")
    jpeg = cv2.imdecode(jpeg,cv2.IMREAD_COLOR)
    return jpeg

def isIn(name, detected_history):
    for i in range(len(detected_history)):
        if i == len(detected_history)-1:
            if name in detected_history[i]:
                return False
        else:
            if not(name in detected_history[i]):
                return False
    return True

def isOut(name, detected, detected_history):
    if name in detected:
        return False
    for i in range(len(detected_history)):
        if i < len(detected_history)-1:
            if name in detected_history[i]:
                return False
    return True

def getWarnings(detected, detected_history, current):
    warnings = []
    for name in detected:
        if name == "Unknown": continue
        if isIn(name, detected_history):
            warning = {}
            warning['name'] = name
            warning['time'] = current
            warning['type'] = 'in'
            warnings.append(warning)
    for name in detected_history[-1]:
        if name == "Unknown": continue
        if isOut(name, detected, detected_history):
            warning = {}
            warning['name'] = name
            warning['time'] = current
            warning['type'] = 'out'
            warnings.append(warning)

    if len(warnings) > 0:
        return os.urandom(4), warnings
    return None, None

async def analyze_cam(db, known_face_encodings, known_face_names):
    store = redis.StrictRedis(host=redishost, port=6379, db=0)
    prev_image_id = None
    # face_cascade = cv2.CascadeClassifier('face.xml')
    analyze_this_frame = True
    detected_history = [set(), set()]
    # last_detected = set()
    while True:
        while True:
            time.sleep(1./MAX_FPS)
            image_id = store.get('image_id')
            if image_id != prev_image_id:
                break
        if analyze_this_frame:
            current = time.strftime('%Y.%m.%d %H:%M:%S',time.localtime(time.time()+28800))
            prev_image_id = image_id
            image = store.get('image')
            frame = decode_image(image)
            detected = set()

            # gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # faces = face_cascade.detectMultiScale(gray, 1.3, 5)
            # store.set('num_face', len(faces))

            # small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
            rgb_small_frame = frame[:, :, ::-1]
            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
            faces= []
            for face_location, face_encoding in zip(face_locations, face_encodings):
                # See if the face is a match for the known face(s)
                matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
                name = "Unknown"
                # If a match was found in known_face_encodings, just use the first one.
                if True in matches:
                    first_match_index = matches.index(True)
                    name = known_face_names[first_match_index]
                if name in detected:
                    name = "Unknown"
                else:
                    detected.add(name)
                faces.append({"name":name, "location":face_location})

            warning_id , warnings = getWarnings(detected, detected_history, current)
            detected_history.pop()
            detected_history.insert(0, detected)
            if not (warning_id is None):
                store.set("warning_id", warning_id)
                store.set("warning", pickle.dumps(warnings))
                await add_one_warning(db, warnings, image)
            # GetIn = detected - last_detected
            # GetOut = last_detected - detected
            # if len(GetIn | GetOut) > 0:
                
            #     warnings = []
            #     for GetInName in GetIn:
            #         if (GetInName == 'Unknown'):
            #             continue
            #         warning = {}
            #         warning['name'] = GetInName
            #         warning['time'] = current
            #         warning['type'] = 'in'
            #         warnings.append(warning)
            #     for GetOutName in GetOut:
            #         if (GetOutName == 'Unknown'):
            #             continue
            #         warning = {}
            #         warning['name'] = GetOutName
            #         warning['time'] = current
            #         warning['type'] = 'out'
            #         warnings.append(warning)
            #     # print(warnings)
            #     if (len(warnings) > 0):
            #         warning_id = os.urandom(4)
            #         store.set("warning_id", warning_id)
            #         store.set("warning", pickle.dumps(warnings))

            store.set("faces",pickle.dumps(faces))
            last_detected = detected
        # analyze_this_frame = not analyze_this_frame


async def connect_to_db():
    tornado.options.parse_command_line()

    # Create the global connection pool.
    print("Trying to connect to postgres...")
    async with aiopg.create_pool(
            host=options.db_host,
            port=options.db_port,
            user=options.db_user,
            password=options.db_password,
            dbname=options.db_database) as db:
        print("Successfully connected to postgres!")
        if options.db_delete:
            await clear_db(db, './sql/delete.sql')
            await maybe_create_tables(db, './sql/warningschema.sql')

        print("Initializing face recognition module...")
        known_face_encodings = []
        known_face_names = []
        path = './known_faces/'
        dirs = os.listdir(path)
        for filename in dirs:
            if filename == '.DS_Store':
                continue
            name = filename.split('.')[0]
            img = face_recognition.load_image_file(path+filename)
            img_encoding = face_recognition.face_encodings(img)[0]
            known_face_encodings.append(img_encoding)
            known_face_names.append(name)
        print("Finish initializing...")
        print("Start analyzing...")
        await analyze_cam(db, known_face_encodings, known_face_names)
        # if options.db_createsuperuser:
        #     await create_superuser(db)
        # app = Application(db)
        # app.listen(options.port)

        # In this demo the server will simply run until interrupted
        # with Ctrl-C, but if you want to shut down more gracefully,
        # call shutdown_event.set().
        # shutdown_event = tornado.locks.Event()
        # await shutdown_event.wait()

if __name__ == "__main__":
    tornado.ioloop.IOLoop.current().run_sync(connect_to_db)
