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
    pass

class AuthLoginHandler(BaseHandler):
    pass

class AuthLogoutHandler(BaseHandler):
    pass

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