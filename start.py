import aiopg
import bcrypt
import os.path
import psycopg2
import re
import json
import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.locks
import tornado.options
import tornado.web
import unicodedata

from tornado.options import define, options

with open('secret.json','r') as f:
    db_data = json.load(f)
    define("db_host", default="127.0.0.1", help="database host")
    define("db_port", default=5432, help="database port")
    define("db_database", default=db_data['Database'], help="database name")
    define("db_user", default=db_data['Username'], help="database user")
    define("db_password", default=db_data['Password'], help="database password")	

define("port", default=8000, help="run on the given port", type=int)
define("db_delete", default=True, help="Delte all the tables in db")

async def clear_db(db):
    with open('delete.sql','r') as f:
        delsql = f.read()
    with (await db.cursor()) as cur:
        await cur.execute(delsql)

async def maybe_create_tables(db):
    try:
        with (await db.cursor()) as cur:
            await cur.execute("SELECT COUNT(*) FROM entries LIMIT 1")
            await cur.fetchone()
    except psycopg2.ProgrammingError:
        with open('schema.sql') as f:
            schema = f.read()
        with (await db.cursor()) as cur:
            await cur.execute(schema)

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
                tornado.escape.utf8(author.hashed_password))
            user_hashed_password = tornado.escape.to_unicode(hashed_password)
            await self.execute("INSERT INTO users (email, name, hashed_password, level) VALUES (%s, %s, %s, 1)",
                                        user_email, user_name, user_hashed_password)
            user_id = await self.queryone("SELECT id FROM users WHERE email = %s", user_email)
            self.set_secure_cookie("monitor_user", str(user_id))
            self.redirect(self.get_argument("next", "/"))
            return
        self.render('signup.html', error="This E-mail has existed!")
        

class AuthLoginHandler(BaseHandler):
    pass

class AuthLogoutHandler(BaseHandler):
    pass

class AuthChangepwdHandler(BaseHandler):
    pass

class AuthCreateUserHandler(BaseHandler):
    # pass
    @tornado.web.authenticated
    await def get(self):
        user_id_str = self.get_secure_cookie("monitor_user")
        if not user_id_str: return None
        user_id = int(user_id_str)
        try:
            level = await self.queryone("SELECT level FROM users WHERE id = %i", user_id)
        except:
            self.redirect("/")
            return
        if (level != 0):
            self.redirect("/")
            return
        self.render("create.html", error=None)

    @tornado.web.authenticated
    await def post(self):
        user_id_str = self.get_secure_cookie("monitor_user")
        if not user_id_str: return None
        user_id = int(user_id_str)
        try:
            level = await self.queryone("SELECT level FROM users WHERE id = %i", user_id)
        except:
            self.redirect("/")
            return
        if (level != 0):
            self.redirect("/")
            return


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
        await maybe_create_tables(db)
        app = Application(db)
        app.listen(options.port)

        # In this demo the server will simply run until interrupted
        # with Ctrl-C, but if you want to shut down more gracefully,
        # call shutdown_event.set().
        shutdown_event = tornado.locks.Event()
        await shutdown_event.wait()

if __name__ == "__main__":
    tornado.ioloop.IOLoop.current().run_sync(main)