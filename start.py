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
import tornado.options
import tornado.web
import tornado.websocket
import unicodedata
import asyncio
from utils import analyze
from tornado.concurrent import run_on_executor, return_future
from utils.mauth import *
from utils.videostreamer import *
from utils.warningpusher import *
from utils import record
from threading import Thread
from tornado.options import define, options
from tornado.platform.asyncio import AnyThreadEventLoopPolicy
from concurrent.futures import ThreadPoolExecutor

with open('secret.json','r') as f:
    db_data = json.load(f)
    define("db_host", default="127.0.0.1", help="database host")
    define("db_port", default=5432, help="database port")
    define("db_database", default=db_data['Database'], help="database name")
    define("db_user", default=db_data['Username'], help="database user")
    define("db_password", default=db_data['Password'], help="database password")	

define("port", default=8000, help="run on the given port", type=int)
define("db_delete", default=False, help="Delte all the tables in db")

class NoResultError(Exception):
    pass

async def clear_db(db):
    with open('delete.sql','r') as f:
        delsql = f.read()
    with (await db.cursor()) as cur:
        await cur.execute(delsql)

async def maybe_create_tables(db):
    try:
        with (await db.cursor()) as cur:
            await cur.execute("SELECT COUNT(*) FROM users LIMIT 1")
            await cur.fetchone()
    except psycopg2.ProgrammingError:
        with open('schema.sql') as f:
            schema = f.read()
        with (await db.cursor()) as cur:
            await cur.execute(schema)

async def create_superuser(db):
    with await(db.cursor()) as cur:
        user_email = "su@su.com"
        user_name = "su"
        user_hashed_password = await tornado.ioloop.IOLoop.current().run_in_executor(
                None, bcrypt.hashpw, tornado.escape.utf8("superuser"),
                bcrypt.gensalt())
        user_hashed_password = tornado.escape.to_unicode(user_hashed_password)
        await cur.execute("INSERT INTO users (email, name, hashed_password, level) VALUES (%s, %s, %s, 0)",
                                        (user_email, user_name, user_hashed_password))

class IndexHandler(BaseHandler):
    async def get(self):
        self.render("index.html")

class Application(tornado.web.Application):
    def __init__(self, db):
        self.db = db
        handlers = [
            (r"/", IndexHandler),
            (r"/auth/signup", AuthSignupHandler),
            (r"/auth/login", AuthLoginHandler),
            (r"/auth/logout", AuthLogoutHandler),
            (r"/auth/changepwd", AuthChangepwdHandler),
            (r"/auth/createuser", AuthCreateUserHandler),
            (r"/auth/changepwdsucc", AuthChangepwdsuccHandler),
            (r"/video_feed", StreamHandler),
            (r"/video_websocket", VideoSocketHandler), # Really slow! Do not use!
            (r"/warning_websocket", WarningSocketHandler),
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
        )
        super(Application, self).__init__(handlers, **settings)

class MultiThreadHandler:
    def __init__(self, func, *args):
        self.thread = Thread(target = func, args=args)
        self.thread.start()

    def finish(self):
        self.thread.join()

async def main():
    tornado.options.parse_command_line()
    # Create the global connection pool.
    async with aiopg.create_pool(
            host=options.db_host,
            port=options.db_port,
            user=options.db_user,
            password=options.db_password,
            dbname=options.db_database) as db:
        if options.db_delete:
            await clear_db(db)
        # await create_superuser(db)
        await maybe_create_tables(db)
        app = Application(db)
        app.listen(options.port)

        # In this demo the server will simply run until interrupted
        # with Ctrl-C, but if you want to shut down more gracefully,
        # call shutdown_event.set().
        shutdown_event = tornado.locks.Event()
        await shutdown_event.wait()

if __name__ == "__main__":
    asyncio.set_event_loop_policy(tornado.platform.asyncio.AnyThreadEventLoopPolicy())
    recordThread = MultiThreadHandler(record.start_recording)
    recordThread = MultiThreadHandler(analyze.analyze_cam)
    # cam = video.UsbCamera()
    tornado.ioloop.IOLoop.current().run_sync(main)