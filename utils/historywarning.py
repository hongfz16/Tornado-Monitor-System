import cv2
import numpy as np
import time
import aiopg
import bcrypt
import os.path
import io
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
from utils.noresulterror import NoResultError

perpage = 5

class HistoryWarningHandler(BaseHandler):
    @tornado.web.authenticated
    async def get(self):
        deleteid = self.get_argument('delete', None)
        if deleteid is None:
            pagestr = self.get_argument('page', 'bad')
            if not pagestr.isdigit():
                self.set_status(404)
                return
            page = int(pagestr)
            if page < 1:
                page = 1
            context = []
            try:
                res = await self.query("SELECT * FROM warnings ORDER BY id DESC;")
            except NoResultError:
                res = []
            count = len(res)
            if  (page-1) * perpage >= count:
                page = 1
            for i in range(perpage):
                index = (page-1)*perpage+1+i
                if index > count: break
                index -= 1
                ans = {}
                # result = await self.queryone("SELECT * FROM warnings WHERE id = %s;", (page-1)*perpage+1+i)
                ans['id'] = res[index]['id']
                ans['name'] = res[index]['name']
                ans['intime'] = res[index]['intime']
                ans['outtime'] = res[index]['outtime']
                ans['url'] = res[index]['url']
                ans['image'] = res[index]['image'].tobytes()

                context.append(ans)

            # print(context)
            self.render("historywarnings.html", context=context, currentpage=page , nextpage=(page*perpage<count))
        else:
            if not deleteid.isdigit():
                self.set_status(404)
                return
            id = int(deleteid)
            await self.execute("DELETE FROM warnings WHERE id = %s;", id)
            self.redirect("/historywarnings?page=1")
