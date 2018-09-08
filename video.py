import cv2
import time
import numpy as np
import redis

MAX_FPS = 100

class UsbCamera(object):
    def __init__(self):
        self._store = redis.StrictRedis(host='localhost', port=6379, db=0)
        self._prev_image_id = None
        self._face_cascade = cv2.CascadeClassifier('face.xml')
    def get_frame(self):
        while True:
            time.sleep(1./MAX_FPS)
            image_id = self._store.get('image_id')
            if image_id != self._prev_image_id:
                break
        self._prev_image_id = image_id
        image = self._store.get('image')

        frame = self.decode_image(image)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self._face_cascade.detectMultiScale(gray, 1.3, 5)

        for (x,y,w,h) in faces:
            cv2.rectangle(frame, (x,y), (x+w, y+h), (255,0,0), 2)
        image = cv2.imencode('.jpg',frame)[1].tobytes()
        
        return image
    def decode_image(self, imbytes):
        jpeg = np.asarray(bytearray(imbytes), dtype="uint8")
        jpeg = cv2.imdecode(jpeg,cv2.IMREAD_COLOR)
        return jpeg
    def have_face(self):
        frame = self.decode_image(self.get_frame())
        frame = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self._face_cascade.detectMultiScale(gray, 1.3, 5)
        return len(faces)

# cam = UsbCamera()
# while True:
#     cam.get_frame(False)