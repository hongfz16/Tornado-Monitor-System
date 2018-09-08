import time
import aiopg
import bcrypt
import os.path
import psycopg2
import re
import json
import base64
import random
import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.locks
import tornado.web
import tornado.websocket
import unicodedata
import asyncio
from tornado.concurrent import run_on_executor
from threading import Thread
from concurrent.futures import ThreadPoolExecutor
from .videostreamer import UsbCamera

def poll_have_face(last, facedetect):
    count = 100
    while count >= 0:
        count -= 1
        tmp = facedetect.have_face()
        if tmp != last:
            return tmp
    return facedetect.have_face()

class WarningSocketHandler(tornado.websocket.WebSocketHandler):
    executor = ThreadPoolExecutor(10)
    def __init__(self, *args, **kwargs):
        self.facedetect = UsbCamera()
        super(WarningSocketHandler, self).__init__(*args, **kwargs)
        self.last_have_face = -1

    def on_close(self):
        # self.executor.shutdown(wait=True)
        print("Connection closed by client.")

    @run_on_executor
    def on_message(self, message):
        try:
            self.last_have_face = poll_have_face(self.last_have_face, self.facedetect)
        except:
            print("Something happened while polling faces.")
        try:
            self.write_message("找到{}张脸".format(self.last_have_face))
        except tornado.websocket.WebSocketClosedError:
            print("Websocket disconnected!")
