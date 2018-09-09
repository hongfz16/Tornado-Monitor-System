import time
import aiopg
import bcrypt
import os.path
import psycopg2
import re
import json
import base64
import random
import pickle
import redis
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
from .host import *

MAX_FPS = 100

def poll_warning_info(last_warning_id, store):
    re_id = None
    while True:
        time.sleep(1./MAX_FPS)
        warning_id = store.get("warning_id")
        if warning_id != last_warning_id:
            re_id = warning_id
            break
    warning_list = pickle.loads(store.get("warning"))
    return (re_id, warning_list)

class WarningSocketHandler(tornado.websocket.WebSocketHandler):
    executor = ThreadPoolExecutor(10)
    def __init__(self, *args, **kwargs):
        super(WarningSocketHandler, self).__init__(*args, **kwargs)
        self.last_warning_id = None
        self.store = redis.StrictRedis(host=redishost, port=6379, db=0)

    def on_close(self):
        # self.executor.shutdown(wait=True)
        print("Connection closed by client.")

    @run_on_executor
    def on_message(self, message):
        # print("on_message")
        try:
            (self.last_warning_id, warning) = poll_warning_info(self.last_warning_id, self.store)
            # print(self.last_have_face)
        except:
            print("Something happened while polling faces.")
            return
        try:
            strmess = ""
            for w in warning:
                strmess += '{} {} at {}. '.format(w['name'],w['type'],w['time'])
            self.write_message(strmess)
        except tornado.websocket.WebSocketClosedError:
            print("Websocket disconnected!")
        except:
            print("other errors!")
            return
