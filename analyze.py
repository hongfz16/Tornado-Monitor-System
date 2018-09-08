import cv2
import time
import numpy as np
import redis

MAX_FPS = 100

def decode_image(imbytes):
    jpeg = np.asarray(bytearray(imbytes), dtype="uint8")
    jpeg = cv2.imdecode(jpeg,cv2.IMREAD_COLOR)
    return jpeg

def analyze_cam():
    store = redis.StrictRedis(host='localhost', port=6379, db=0)
    prev_image_id = None
    face_cascade = cv2.CascadeClassifier('face.xml')
    while True:
        while True:
            time.sleep(1./MAX_FPS)
            image_id = store.get('image_id')
            if image_id != prev_image_id:
                break
        prev_image_id = image_id
        image = store.get('image')
        frame = decode_image(image)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        store.set('num_face', len(faces))