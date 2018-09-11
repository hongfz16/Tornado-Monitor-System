import face_recognition
import cv2
import time
import numpy as np
import redis
import base64
import pickle
import os
import json
import requests
import tornado
import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.locks
import tornado.options
import tornado.web
import tornado.websocket
from tornado.options import define, options
import threading

# postgreshost = '127.0.0.1'
# redishost = '127.0.0.1'
postgreshost  = 'postgres'
redishost = 'redis'

urls = set()
urls_lock = threading.Lock()
MAX_FPS = 100

define("port", default=6000, help="run on the given port", type=int)

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

def getWarnings(detecteds, inCam, inCamTime, current):
    warnings = []
    toAdd = []
    for name in detecteds[0]:
        if name == 'Unknown': continue
        if name in detecteds[1] and \
            not (name in detecteds[-1]) and \
            not (name in detecteds[-2]):
            warning = {}
            warning['name'] = name
            warning['time'] = current
            warning['type'] = 'in'
            warnings.append(warning)
            toAdd.append(name)
            inCam.add(name)
            inCamTime[name] = current

    all = detecteds[0] | detecteds[1]# | detecteds[2] | detecteds[3]
    toDelete = []
    for name in inCam:
        if not (name in all):
            warning = {}
            warning['name'] = name
            warning['time'] = current
            warning['type'] = 'out'
            warnings.append(warning)
            toDelete.append(name)
    for name in toDelete:
        inCam.remove(name)

    if len(warnings) > 0:
        return os.urandom(4), warnings, toAdd, toDelete
    return None, None, None, None

def analyze_cam(known_face_encodings, known_face_names, url):
    store = redis.StrictRedis(host=redishost, port=6379, db=0)
    prev_image_id = None
    analyze_this_frame = True
    detected_history = [set(), set(), set()]
    inCam = set()
    inCamTime = {}
    inCamFace = {}
    while url in urls:
        while url in urls:
            time.sleep(1./MAX_FPS)
            image_id = store.get('image_id'+'_'+url)
            if image_id != prev_image_id:
                break
        if not (url in urls): break
        if analyze_this_frame:
            current = time.strftime('%Y.%m.%d %H:%M:%S',time.localtime(time.time()+28800))
            prev_image_id = image_id
            image = store.get('image'+'_'+url)
            frame = decode_image(image)
            detected = set()

            # gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # faces = face_cascade.detectMultiScale(gray, 1.3, 5)
            # store.set('num_face', len(faces))

            # small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
            # small_frame = cv2.resize(frame, (0, 0), fx=0.75, fy=0.75)
            rgb_small_frame = frame[:, :, ::-1]
            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
            faces = []
            cropedfaces = {}
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
                elif name != 'Unknown':
                    detected.add(name)
                (top, right, bottom, left) = face_location
                cropedface = frame[top:bottom, left:right]
                cropedface = cv2.resize(cropedface, (100, 100), interpolation=cv2.INTER_CUBIC) 
                cropedfaces[name] = cropedface
                faces.append({"name":name, "location":face_location})
            
            detected_history.insert(0, detected)
            warning_id , warnings, iners, outers = getWarnings(detected_history, inCam, inCamTime, current)
            detected_history.pop()
            if not (warning_id is None):
                store.set("warning_id"+'_'+url, warning_id)
                store.set("warning"+'_'+url, pickle.dumps(warnings))
                for name in iners:
                    inCamFace[name] = cropedfaces[name]
                db_warnings = []
                for name in outers:
                    # print(base64.b64encode(frame))
                    db_warning = {}
                    db_warning['name'] = name
                    db_warning['intime'] = inCamTime[name]
                    db_warning['outtime'] = current
                    db_warning['image'] = base64.b64encode(cv2.imencode('.jpg', inCamFace[name])[1])
                    db_warning['url'] = url
                    db_warnings.append(db_warning)
                    # add_one_warning(db, name, inCamTime[name], current,
                    #     base64.b64encode(cv2.imencode('.jpg', inCamFace[name])[1]), url)
                    del inCamTime[name]
                    del inCamFace[name]
                if len(db_warnings) > 0:
                    store.set("db_warnings"+'_'+url, pickle.dumps(db_warnings))
                    requests.get('http://tornado_monitor:8000/new_warning_writedb?url=%s'%url)

                requests.get('http://tornado_monitor:8000/new_warning?url=%s'%url)
                
            

            store.set("faces"+'_'+url, pickle.dumps(faces))
            last_detected = detected
        # analyze_this_frame = not analyze_this_frame

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/new_camera_feed", newCameraHandler),
            (r"/delete_camera_feed", deleteCameraHandler),
        ]
        settings = dict(
            # web_title=u"Intelligent Monitor System",
            # template_path=os.path.join(os.path.dirname(__file__), "templates"),
            # static_path=os.path.join(os.path.dirname(__file__), "static"),
            ui_modules={},
            # xsrf_cookies=True,
            # cookie_secret="__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__",
            # login_url="/auth/login",
            debug=True,
        )
        super(Application, self).__init__(handlers, **settings)

class MultiThreadHandler:
    def __init__(self, func, args=None):
        if args is None:
            self.thread = threading.Thread(target = func)
        else:
            self.thread = threading.Thread(target = func, args = args)
        self.thread.start()

    def finish(self):
        self.thread.join()

class newCameraHandler(tornado.web.RequestHandler):
    def get(self):
        url = self.get_argument('url', None)
        if url is None: return
        urls.add(url)
        MultiThreadHandler(analyze_cam, (known_face_encodings, known_face_names, url,))

class deleteCameraHandler(tornado.web.RequestHandler):
    def get(self):
        url = self.get_argument('url', None)
        if url is None: return
        with urls_lock:
            if url in urls:
                urls.remove(url)

if __name__ == "__main__":
    # tornado.ioloop.IOLoop.current().run_sync(connect_to_db)
    # urls.add('0')
    # t = MultiThreadHandler(connect_to_db, '0')
    # time.sleep(5)
    # urls.remove('0')
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

    app = Application()
    app.listen(options.port)
    tornado.ioloop.IOLoop.current().start()