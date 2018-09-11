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
from .mauth import BaseHandler

MAX_FPS = 100

class WSConnectionManager():
    websockets = []
    counter = 0

    @classmethod
    def AddWSConnection(cls, socket):
        cls.websockets.append({'id':cls.counter, 'socket':socket})
        print('A new connection added to pool!')
        print('Now we have ' + str(len(cls.websockets)) + ' connections!')
        cls.counter += 1
        return cls.counter - 1

    @classmethod
    def DelWSConnection(cls, id):
        index = -1
        for _index, ws in enumerate(cls.websockets):
            if ws['id']==id:
                index = _index
                break
        if index != -1:
            cls.websockets.pop(index)
            print('A connection poped out of pool!')
            print('Now we have ' + str(len(cls.websockets)) + ' connections!')

class NewWarningHandler(tornado.web.RequestHandler):
    def get(self):
        url = self.get_argument('url', None)
        # print(url)
        if not url:
            return
        for ws in WSConnectionManager.websockets:
            socket = ws['socket']
            try:
                warning_list = pickle.loads(socket.store.get('warning_'+url))
            except:
                print("Socket disconnected!")
                return
            mess = {}
            strmess = []
            for w in warning_list:
                strmess.append('{} {} at {}'.format(w['name'],w['type'],w['time']))
            mess['str'] = strmess
            mess['url'] = url
            try:
                socket.write_message(mess)
            except tornado.websocket.WebSocketClosedError:
                print("Websocket disconnected!")
            except:
                print("other errors!")

class NewWarningWritedbHandler(BaseHandler):
    store = redis.StrictRedis(host=redishost, port=6379, db=0)
    async def get(self):
        print('in NewWarningWritedbHandler')
        url = self.get_argument('url', None)
        if not url:
            return
        db_warnings = pickle.loads(self.store.get('db_warnings_'+url))
        for db_warning in db_warnings:
            await self.execute("INSERT INTO warnings (name, intime, outtime, url, image) VALUES (%s, %s, %s, %s, %s)",
                    db_warning['name'], db_warning['intime'], db_warning['outtime'], db_warning['url'], db_warning['image'])

# Not using it! Polling is inefficient!
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
        self.mid = WSConnectionManager.AddWSConnection(self)

    def on_close(self):
        # self.executor.shutdown(wait=True)
        WSConnectionManager.DelWSConnection(self.mid)
        print("Connection closed by client.")

    # Not using it! It need to be used with the above function!
    @run_on_executor
    def on_message(self, message):
        print("on_message")
        try:
            (self.last_warning_id, warning) = poll_warning_info(self.last_warning_id, self.store)
            # print(self.last_have_face)
        except:
            print("Something happened while polling faces.")
            return
        try:
            mess = {}
            strmess = []
            for w in warning:
                strmess.append('From on message: {} {} at {}'.format(w['name'],w['type'],w['time']))
            mess['str'] = strmess
            self.write_message(mess)
        except tornado.websocket.WebSocketClosedError:
            print("Websocket disconnected!")
        except:
            print("other errors!")
            return
