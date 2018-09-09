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
    # print("get into poll_have face")
    count = 100
    while count >= 0:
        count -= 1
        tmp = facedetect.have_face()
        if tmp != last:
            # print("return from poll_have face1")
            return tmp
    # print("return from poll_have face2")
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
        # print("on_message")
        try:
            self.last_have_face = poll_have_face(self.last_have_face, self.facedetect)
            # print(self.last_have_face)
        except:
            print("Something happened while polling faces.")
            return

        try:
            self.write_message("找到{}张脸".format(self.last_have_face))
        except tornado.websocket.WebSocketClosedError:
            print("Websocket disconnected!")
        except:
            print("other errors!")
            return
