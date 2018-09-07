#!/usr/bin/env python3

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

define("port", default=8888, help="run on the given port", type=int)
define("db_host", default="127.0.0.1", help="blog database host")
define("db_port", default=5432, help="blog database port")
define("db_database", default="tornado_blog", help="blog database name")
define("db_user", default="tornado", help="blog database user")
define("db_password", default="ttasw1234", help="blog database password")