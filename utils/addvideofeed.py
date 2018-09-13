import cv2
import numpy as np
import time
import aiopg
import bcrypt
import os.path
import io
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
import requests
from tornado.concurrent import run_on_executor
from threading import Thread
from concurrent.futures import ThreadPoolExecutor
from .host import *
from .mauth import BaseHandler
from utils.noresulterror import NoResultError

def TranslateUrl(url):
    if not url.startswith('rtsp'):
        return url
    new_url = url.replace('&','%26')
    # new_url = url.replace('+','%2B')
    # new_url = url.replace(' ','%20')
    # new_url = url.replace('/','%2F')
    # new_url = url.replace('?','%3F')
    # new_url = url.replace('%','%25')
    # new_url = url.replace('#','%23')
    # new_url = url.replace('=','%3D')
    return new_url

class AddVideoFeedHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render('addvideofeed.html', error=None, message=None)

    @tornado.web.authenticated
    def post(self):
        new_url = self.get_argument('url')
        # print(new_url)
        if new_url in self.application.urls:
            self.render('addvideofeed.html', error='This url has been added.', message=None)
            return
        self.application.urls.append(new_url)
        new_url = TranslateUrl(new_url)
        print('http://record_thread:7000/new_camera_feed?url='+new_url)
        requests.get('http://record_thread:7000/new_camera_feed?url='+new_url)
        requests.get('http://analyze_thread:6000/new_camera_feed?url='+new_url)
        self.render('addvideofeed.html', error=None, message='Successfully add new url: '+new_url)

class DeleteVideoFeedHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render('deletevideofeed.html', error=None, message=None)

    @tornado.web.authenticated
    def post(self):
        new_url = self.get_argument('url')
        if new_url not in self.application.urls:
            self.render('deletevideofeed.html', error='This url was not in the list.', message=None)
            return
        self.application.urls.remove(new_url)
        new_url = TranslateUrl(new_url)
        requests.get('http://record_thread:7000/delete_camera_feed?url='+new_url)
        requests.get('http://analyze_thread:6000/delete_camera_feed?url='+new_url)
        self.render('deletevideofeed.html', error=None, message='Successfully remove url: '+new_url)