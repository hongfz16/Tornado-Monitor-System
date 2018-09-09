import bcrypt
import psycopg2
import aiopg
import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.locks
import tornado.options
import tornado.web
import tornado.websocket

async def clear_db(db, filename):
    with open(filename,'r') as f:
        delsql = f.read()
    with (await db.cursor()) as cur:
        await cur.execute(delsql)

async def maybe_create_tables(db, filename):
    with open(filename, 'r') as f:
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