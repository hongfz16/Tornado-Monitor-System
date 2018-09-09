import cv2
import time
import numpy as np
import redis
import aiopg
import bcrypt
import os.path
import psycopg2
import re
import json
import base64
import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.locks
import tornado.options
import tornado.web
import tornado.websocket

MAX_FPS = 100

class UsbCamera(object):
    def __init__(self):
        self._store = redis.StrictRedis(host='redis', port=6379, db=0)
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
        num = self._store.get('num_face')
        return int(num)

# Really slow! Do not use it!
class VideoSocketHandler(tornado.websocket.WebSocketHandler):
    def __init__(self, *args, **kwargs):
        super(VideoSocketHandler, self).__init__(*args, **kwargs)
    async def on_message(self, message):
        img = cam.get_frame()
        img = base64.b64encode(img)
        await self.write_message(img)

class StreamHandler(tornado.web.RequestHandler):
    def __init__(self, *args, **kwargs):
        super(StreamHandler, self).__init__(*args, **kwargs)
        self.cam = UsbCamera()
    @tornado.gen.coroutine
    def get(self):
        ioloop = tornado.ioloop.IOLoop.current()

        self.set_header('Cache-Control', 'no-store, no-cache, must-revalidate, pre-check=0, post-check=0, max-age=0')
        self.set_header( 'Pragma', 'no-cache')
        self.set_header( 'Content-Type', 'multipart/x-mixed-replace;boundary=--jpgboundary')
        self.set_header('Connection', 'close')

        self.served_image_timestamp = time.time()
        my_boundary = "--jpgboundary"
        while True:
            img = self.cam.get_frame()
            interval = 0.05
            if self.served_image_timestamp + interval < time.time():
                self.write(my_boundary)
                self.write("Content-type: image/jpeg\r\n")
                self.write("Content-length: %s\r\n\r\n" % len(img))
                self.write(img)
                self.served_image_timestamp = time.time()
                yield tornado.gen.Task(self.flush)
            else:
                yield tornado.gen.Task(ioloop.add_timeout, ioloop.time() + interval)
