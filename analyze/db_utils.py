import bcrypt
import psycopg2
import aiopg
import pickle
import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.locks
import tornado.options
import tornado.web
import tornado.websocket

def clear_db(db, filename):
    with open(filename,'r') as f:
        delsql = f.read()
    with db.cursor() as cur:
        cur.execute(delsql)

def maybe_create_tables(db, filename):
    with open(filename, 'r') as f:
        schema = f.read()
    with db.cursor() as cur:
        cur.execute(schema)

def add_one_warning(db, name, intime, outtime, image, url):
    with db.cursor() as cur:
        # user_email = "su@su.com"
        # user_name = "su"
        # user_hashed_password = await tornado.ioloop.IOLoop.current().run_in_executor(
        #         None, bcrypt.hashpw, tornado.escape.utf8("superuser"),
        #         bcrypt.gensalt())
        # user_hashed_password = tornado.escape.to_unicode(user_hashed_password)
        # print("before INSERT into warnings")
        cur.execute("INSERT INTO warnings (name, intime, outtime, image, url) VALUES (%s, %s, %s, %s, %s)",
                                        (name, intime, outtime, image, url))
        # print("after INSERT into warnings")