import time
import aiopg
import bcrypt
import os.path
import psycopg2
import re
import json
import base64
import random
import unicodedata
import asyncio

import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.locks
import tornado.options
import tornado.web
import tornado.websocket

from concurrent.futures import ThreadPoolExecutor
from threading import Thread

from tornado.concurrent import run_on_executor, return_future
from tornado.options import define, options
from tornado.platform.asyncio import AnyThreadEventLoopPolicy

from utils.noresulterror import NoResultError
from utils.mauth import *
from utils.videostreamer import *
from utils.warningpusher import *
from utils.db_utils import *
from utils.host import *
from utils.historywarning import *
from utils.addvideofeed import *

with open('.env','r') as f:
    db_data = []
    for i in range(0,3):
        line = f.readline()
        tmp = ''
        start = False
        for j in range(len(line)):
            if line[j] == '=':
                start = True
                continue
            if line[j] == '\n':
                break
            if start:
                tmp += line[j]
        db_data.append(tmp)

    define("db_host", default=postgreshost, help="database host")
    define("db_port", default=5432, help="database port")
    define("db_database", default=db_data[2], help="database name")
    define("db_user", default=db_data[0], help="database user")
    define("db_password", default=db_data[1], help="database password")	

define("port", default=8000, help="run on the given port", type=int)
define("db_delete", default=True, help="Delte all the tables in db")
define("db_createsuperuser", default=True, help="Create Superuser")

class IndexHandler(BaseHandler):
    async def get(self):
        self.render("index.html", urls=self.application.urls)

class DetailHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        url = self.get_argument('video')
        self.render("videodetail.html",url=url)


class Application(tornado.web.Application):
    def __init__(self, db):
        self.db = db
        self.urls = []
        handlers = [
            (r"/", IndexHandler),
            (r"/detail", DetailHandler),
            (r"/auth/signup", AuthSignupHandler),
            (r"/auth/login", AuthLoginHandler),
            (r"/auth/logout", AuthLogoutHandler),
            (r"/auth/changepwd", AuthChangepwdHandler),
            (r"/auth/createuser", AuthCreateUserHandler),
            (r"/auth/changepwdsucc", AuthChangepwdsuccHandler),
            (r"/video_feed", StreamHandler),
            (r"/video_websocket", VideoSocketHandler), # Really slow! Do not use!
            (r"/warning_websocket", WarningSocketHandler),
            (r"/historywarnings", HistoryWarningHandler),
            (r"/new_warning", NewWarningHandler),
            (r"/add_video_feed", AddVideoFeedHandler),
            (r"/delete_video_feed", DeleteVideoFeedHandler),
            (r"/new_warning_writedb", NewWarningWritedbHandler)
        ]
        settings = dict(
            web_title=u"Intelligent Monitor System",
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            ui_modules={},
            xsrf_cookies=True,
            cookie_secret="__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__",
            login_url="/auth/login",
            debug=True,
            compress_response=True,
        )
        super(Application, self).__init__(handlers, **settings)

async def main():
    tornado.options.parse_command_line()
    
    # Create the global connection pool.
    print("Trying to connect to postgres...")
    while True:
        try:
            db = await aiopg.create_pool(
                host=options.db_host,
                port=options.db_port,
                user=options.db_user,
                password=options.db_password,
                dbname=options.db_database)
            break
        except:
            time.sleep(5)
            print("Retrying...")
    # async with aiopg.create_pool(
    #         host=options.db_host,
    #         port=options.db_port,
    #         user=options.db_user,
    #         password=options.db_password,
    #         dbname=options.db_database) as db:
    print("Successfully connected to postgres!")
    if options.db_delete:
        await clear_db(db, './sql/delete.sql')
        await maybe_create_tables(db, './sql/schema.sql')
    if options.db_createsuperuser:
        await create_superuser(db)
    app = Application(db)
    app.listen(options.port)

    # In this demo the server will simply run until interrupted
    # with Ctrl-C, but if you want to shut down more gracefully,
    # call shutdown_event.set().
    shutdown_event = tornado.locks.Event()
    await shutdown_event.wait()

if __name__ == "__main__":
    asyncio.set_event_loop_policy(tornado.platform.asyncio.AnyThreadEventLoopPolicy())
    # print("Trying to start recording and analyze thread...")
    # recordThread = MultiThreadHandler(record.start_recording)
    # analyzeThread = MultiThreadHandler(analyze.analyze_cam)
    # print("Successfully start 2 threads...")
    tornado.ioloop.IOLoop.current().run_sync(main)