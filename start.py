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
from tornado.platform.asyncio import AnyThreadEventLoopPolicy
from threading import Thread
from tornado.concurrent import run_on_executor, return_future
from concurrent.futures import ThreadPoolExecutor

import video

from threading import Thread
from tornado.options import define, options
from tornado.platform.asyncio import AnyThreadEventLoopPolicy
from tornado.concurrent import run_on_executor
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

class BaseHandler(tornado.web.RequestHandler):
    def row_to_obj(self, row, cur):
        """Convert a SQL row to an object supporting dict and attribute access."""
        obj = tornado.util.ObjectDict()
        for val, desc in zip(row, cur.description):
            obj[desc.name] = val
        return obj

    async def execute(self, stmt, *args):
        """Execute a SQL statement.
        Must be called with ``await self.execute(...)``
        """
        with (await self.application.db.cursor()) as cur:
            await cur.execute(stmt, args)

    async def query(self, stmt, *args):
        """Query for a list of results.
        Typical usage::
            results = await self.query(...)
        Or::
            for row in await self.query(...)
        """
        with (await self.application.db.cursor()) as cur:
            await cur.execute(stmt, args)
            return [self.row_to_obj(row, cur)
                    for row in await cur.fetchall()]

    async def queryone(self, stmt, *args):
        """Query for exactly one result.
        Raises NoResultError if there are no results, or ValueError if
        there are more than one.
        """
        results = await self.query(stmt, *args)
        if len(results) == 0:
            raise NoResultError()
        elif len(results) > 1:
            raise ValueError("Expected 1 result, got %d" % len(results))
        return results[0]

    async def prepare(self):
        # get_current_user cannot be a coroutine, so set
        # self.current_user in prepare instead.
        user_id = self.get_secure_cookie("monitor_user")
        if user_id:
            # print(user_id)
            self.current_user = await self.queryone("SELECT * FROM users WHERE id = %s",
                                                    int(user_id))

class MultiThreadHandler:
    def __init__(self, func, *args):
        self.thread = Thread(target = func, args=args)
        self.thread.start()

    def finish(self):
        self.thread.join()


# Really slow! Do not use it!
class VideoSocketHandler(tornado.websocket.WebSocketHandler):
    def __init__(self, *args, **kwargs):
        super(VideoSocketHandler, self).__init__(*args, **kwargs)
    async def on_message(self, message):
        img = cam2.get_frame()
        img = base64.b64encode(img)
        await self.write_message(img)

def poll_have_face(last):
    while True:
        tmp = facedetect.have_face()
        if tmp != last:
            return tmp

class WarningSocketHandler(tornado.websocket.WebSocketHandler):
    executor = ThreadPoolExecutor(10)
    def __init__(self, *args, **kwargs):
        super(WarningSocketHandler, self).__init__(*args, **kwargs)
        self.last_have_face = False
    
    # @tornado.web.asynchronous
    # @tornado.gen.coroutine
    @run_on_executor
    def on_message(self, message):
        # i = fake_poll()
        # self.write_message(str(i)+' loops.')
        self.last_have_face = poll_have_face(self.last_have_face)
        if self.last_have_face:
            self.write_message('Face detected!')
        else:
            self.write_message('No face!')

class StreamHandler(tornado.web.RequestHandler):
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
            # Generating images for mjpeg stream and wraps them into http resp
            # if self.get_argument('fd') == "true":
            #     # res = {}
            #     # mt = MultiThreadHandler(cam.get_frame, True, res)
            #     # mt.finish()
            #     # img = res['img']
            #     img = cam.get_frame(True)
            # else:
            #     # res = {}
            #     # mt = MultiThreadHandler(cam.get_frame, False, res)
            #     # mt.finish()
            #     # img = res['img']
            #     img = cam.get_frame(False)
            img = cam.get_frame()
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

class IndexHandler(BaseHandler):
    async def get(self):
        self.render("index.html")

class AuthSignupHandler(BaseHandler):
    def get(self):
        self.render('signup.html', error=None)

    async def post(self):
        user_email = self.get_argument("email")
        try:
            await self.queryone("SELECT * FROM users WHERE email = %s", user_email)
        except NoResultError:
            user_name = self.get_argument("name")
            hashed_password = await tornado.ioloop.IOLoop.current().run_in_executor(
                None, bcrypt.hashpw, tornado.escape.utf8(self.get_argument("password")),
                bcrypt.gensalt())
            user_hashed_password = tornado.escape.to_unicode(hashed_password)
            await self.execute("INSERT INTO users (email, name, hashed_password, level) VALUES (%s, %s, %s, 1)",
                                        user_email, user_name, user_hashed_password)
            user_id = await self.queryone("SELECT id FROM users WHERE email = %s", user_email)
            self.set_secure_cookie("monitor_user", str(user_id.id))
            self.redirect(self.get_argument("next", "/"))
            return
        self.render('signup.html', error="This E-mail has existed!")
        

class AuthLoginHandler(BaseHandler):
    def get(self):
        self.render("login.html", error=None)

    async def post(self):
        try:
            user = await self.queryone("SELECT * FROM users WHERE email = %s",
                                        self.get_argument("email"))
        except NoResultError:
            self.render("login.html", error="Email not found. Please Sign up first.")
            return
        hashed_password = await tornado.ioloop.IOLoop.current().run_in_executor(
            None, bcrypt.hashpw, tornado.escape.utf8(self.get_argument("password")),
            tornado.escape.utf8(user.hashed_password))
        hashed_password = tornado.escape.to_unicode(hashed_password)
        if hashed_password == user.hashed_password:
            self.set_secure_cookie("monitor_user", str(user.id))
            self.redirect(self.get_argument("next", "/"))
        else:
            self.render("login.html", error="Incorrect password.")

class AuthLogoutHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.clear_cookie("monitor_user")
        self.redirect(self.get_argument("next", "/"))

class AuthChangepwdsuccHandler(BaseHandler):
    def get(self):
        self.render("changepwdsucc.html", succ="Successfully changed password!")


class AuthChangepwdHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("changepwd.html", error=None)

    async def post(self):
        try:
            user = await self.queryone("SELECT * FROM users WHERE id = %s",
                                        self.current_user.id)
        except NoResultError:
            self.render("changepwd.html", 
                        error="User Not Found. There must be something wrong.")
            return
        if self.get_argument("newpassword") != self.get_argument("newpasswordagain"):
            self.render("changepwd.html",
                        error="The second password is different from the first one.")
            return
        new_hashed_password = await tornado.ioloop.IOLoop.current().run_in_executor(
            None, bcrypt.hashpw, tornado.escape.utf8(self.get_argument("newpassword")),
            bcrypt.gensalt())
        new_hashed_password = tornado.escape.to_unicode(new_hashed_password)
        hashed_password = await tornado.ioloop.IOLoop.current().run_in_executor(
            None, bcrypt.hashpw, tornado.escape.utf8(self.get_argument("originalpassword")),
            tornado.escape.utf8(user.hashed_password))
        hashed_password = tornado.escape.to_unicode(hashed_password)
        if hashed_password == user.hashed_password:
            await self.execute("UPDATE users SET hashed_password=%s WHERE id=%s;",
                                new_hashed_password,
                                self.current_user.id)
            self.clear_cookie("monitor_user")
            self.redirect("/auth/changepwdsucc")
        else:
            self.render("changepwd.html",
                        error="Original Password incorrect!")

class AuthCreateUserHandler(BaseHandler):
    @tornado.web.authenticated
    async def get(self):
        user_id_str = self.get_secure_cookie("monitor_user")
        if not user_id_str: return None
        user_id = int(user_id_str)
        try:
            level = await self.queryone("SELECT level FROM users WHERE id = %s;", user_id)
        except:
            self.redirect("/")
            return
        if (level.level != 0):
            self.redirect("/")
            return
        self.render("create.html", error=None)

    @tornado.web.authenticated
    async def post(self):
        user_id_str = self.get_secure_cookie("monitor_user")
        if not user_id_str: return None
        user_id = int(user_id_str)
        try:
            level = await self.queryone("SELECT level FROM users WHERE id = %s;", user_id)
        except:
            self.redirect("/")
            return
        if (level.level != 0):
            self.redirect("/")
            return
        user_email = self.get_argument("email")
        try:
            await self.queryone("SELECT * FROM users WHERE email = %s", user_email)
        except NoResultError:
            user_name = self.get_argument("name")
            hashed_password = await tornado.ioloop.IOLoop.current().run_in_executor(
                None, bcrypt.hashpw, tornado.escape.utf8(self.get_argument("password")),
                bcrypt.gensalt())
            user_hashed_password = tornado.escape.to_unicode(hashed_password)
            await self.execute("INSERT INTO users (email, name, hashed_password, level) VALUES (%s, %s, %s, 1)",
                                        user_email, user_name, user_hashed_password)
            user_id = await self.queryone("SELECT id FROM users WHERE email = %s", user_email)
            self.redirect(self.get_argument("next", "/"))
            return
        self.render('create.html', error="This E-mail has existed!")


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
    cam = video.UsbCamera()
    cam2 = video.UsbCamera()
    facedetect = video.UsbCamera()
    asyncio.set_event_loop_policy(tornado.platform.asyncio.AnyThreadEventLoopPolicy())
    tornado.ioloop.IOLoop.current().run_sync(main)