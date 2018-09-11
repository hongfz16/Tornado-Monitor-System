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
import unicodedata
import asyncio

from utils.noresulterror import NoResultError

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
        print('in query')
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
