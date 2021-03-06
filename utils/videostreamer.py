import cv2
import time
import numpy as np
import redis
import aiopg
import bcrypt
import os.path
import psycopg2
import pickle
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

from .host import *

MAX_FPS = 100

class UsbCamera(object):
    def __init__(self, url):
        self._store = redis.StrictRedis(host=redishost, port=6379, db=0)
        self._prev_image_id = None
        self._url = url
    def get_frame(self, need_draw):
        while True:
            time.sleep(1./MAX_FPS)
            image_id = self._store.get('image_id_'+self._url)
            if image_id != self._prev_image_id:
                break
        self._prev_image_id = image_id
        image = self._store.get('image_'+self._url)
        frame = self.decode_image(image)
        if need_draw:
            facesp = self._store.get("faces_"+self._url)
            faces = pickle.loads(facesp)
            for face in faces:
                # name = face['name']
                (top, right, bottom, left) = face['location']
                name = face['name']
                # for (top, right, bottom, left), name in zip(face['location'], face['name']):
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
                cv2.rectangle(frame, (left, bottom), (right, bottom+15), (0, 0, 255), cv2.FILLED)
                font = cv2.FONT_HERSHEY_DUPLEX
                cv2.putText(frame, name, (left + 6, bottom + 10), font, 0.5, (255, 255, 255), 1)
        image = cv2.imencode('.jpg',frame)[1].tobytes()
        return image
    def decode_image(self, imbytes):
        jpeg = np.asarray(bytearray(imbytes), dtype="uint8")
        jpeg = cv2.imdecode(jpeg,cv2.IMREAD_COLOR)
        return jpeg

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
        url = self.get_argument('video', None)
        # print(url)
        self.cam = UsbCamera(url)

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
            img = self.cam.get_frame(True)
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
