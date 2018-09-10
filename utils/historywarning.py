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

perpage = 5

class HistoryWarningHandler(BaseHandler):
    @tornado.web.authenticated
    async def get(self):
        # user_id_str = self.get_secure_cookie("monitor_user")
        # if not user_id_str: return None
        # user_id = int(user_id_str)
        # try:
        #     level = await self.queryone("SELECT level FROM users WHERE id = %s;", user_id)
        # except:
        #     self.redirect("/")
        #     return
        pagestr = self.get_argument('page', 'bad')
        if not pagestr.isdigit():
            self.set_status(404)
            return
        page = int(pagestr)
        if page < 1:
            self.set_status(404)
            return
        context = []
        res = await self.queryone("SELECT count(*) FROM warnings;")
        if  (page-1) * perpage >= res['count']:
            self.set_status(404)
            return
        for i in range(perpage):
            # print(res)
            # print(type(res))
            # print(res['count'])
            if (page-1)*perpage+1+i > res['count']:
                break
            ans = {}
            result = await self.queryone("SELECT * FROM warnings WHERE id = %s;", (page-1)*perpage+1+i)

            ans['name'] = result['name']
            ans['intime'] = result['intime']
            ans['outtime'] = result['outtime']
            ans['image'] = result['image']
            # print(type(ans['image']))
            # ans['currentpage'] = page

            context.append(ans)

        # print(context)
        self.render("historywarnings.html", context=context, currentpage=page , nextpage=(page*perpage<res.count))
