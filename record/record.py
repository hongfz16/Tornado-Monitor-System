import os
import sys
import time
import io

import coils
import cv2
import numpy as np
from redis import StrictRedis
import threading
import json
import tornado
from tornado.options import define, options

define("port", default=7000, help="run on the given port", type=int)

redishost = 'redis'

urls = set()

def open_cap(url):
    max_sleep = 5.0
    cur_sleep = 0.1
    while True:
        # cap = cv2.VideoCapture('./trump.mp4')
        cap = cv2.VideoCapture(url)
        if cap.isOpened():
            break
        print('not opened, sleeping {}s'.format(cur_sleep))
        time.sleep(cur_sleep)
        if cur_sleep < max_sleep:
            cur_sleep *= 2
            cur_sleep = min(cur_sleep, max_sleep)
            continue
        cur_sleep = 0.1
    return cap

def start_recording(url = '0'):
    # Retrieve command line arguments.
    width = None if len(sys.argv) <= 1 else int(sys.argv[1])
    height = None if len(sys.argv) <= 2 else int(sys.argv[2])

    # width = 480
    # height = 360

    # Create video capture object, retrying until successful.
    if url.isdigit():
        cap = open_cap(int(url))
    else:
        cap = open_cap(url)

    print("cap is opened!")

    mfps = cap.get(cv2.CAP_PROP_FPS)

    # Create client to the Redis store.
    store = StrictRedis(host=redishost, port=6379, db=0)

    # Set video dimensions, if given.
    if width: cap.set(3, width)
    if height: cap.set(4, height)

    # Monitor the framerate at 1s, 5s, 10s intervals.
    fps = coils.RateTicker((1, 5, 10))

    # Repeatedly capture current image, 
    # encode, serialize and push to Redis database.
    # Then create unique ID, and push to database as well.
    print('Start Recording %s...'%url)
    while url in urls:
        hello, image = cap.read()
        # if image is None:
        #     cap.release()
        #     # cap = cv2.VideoCapture(0)
        #     cap = cv2.VideoCapture('./trimed.mp4')
        #     cap = open_cap()
        #     hello, image = cap.read()
        #     print(None)
        time.sleep(0.05)
        if image is None:
            time.sleep(0.5)
            continue

        _, image = cv2.imencode('.jpg', image)
        value = image.tobytes()
        store.set('image'+'_'+url, value)
        image_id = os.urandom(4)
        store.set('image_id'+'_'+url, image_id)
        # Print the framerate.
        # text = '{:.2f}, {:.2f}, {:.2f} fps'.format(*fps.tick())
        # print(text)
    print('Stop Recording %s...'%url)

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/newCameraHandler", newCameraHandler),
            (r"/deleteCameraHandler", deleteCameraHandler),
        ]
        settings = dict(
            # web_title=u"Intelligent Monitor System",
            # template_path=os.path.join(os.path.dirname(__file__), "templates"),
            # static_path=os.path.join(os.path.dirname(__file__), "static"),
            ui_modules={},
            # xsrf_cookies=True,
            # cookie_secret="__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__",
            # login_url="/auth/login",
            debug=True,
        )
        super(Application, self).__init__(handlers, **settings)

class MultiThreadHandler:
    def __init__(self, func, args=None):
        if args is None:
            self.thread = threading.Thread(target = func)
        else:
            self.thread = threading.Thread(target = func, args = args)
        self.thread.start()

    def finish(self):
        self.thread.join()

class newCameraHandler(tornado.web.RequestHandler):
    def get(self):
        url = self.get_argument('new_camera_feed', None)
        if url is none: return
        urls.add(url)
        MultiThreadHandler(start_recording, (url,))

class deleteCameraHandler(tornado.web.RequestHandler):
    def get(self):
        url = self.get_argument('delete_camera_feed', None)
        if url is none: return
        if url in urls:
            urls.remove(url)

if __name__ == "__main__":
    # urls.add('trump.mp4')
    # urls.add('0')
    # t1 = MultiThreadHandler(start_recording, ('trump.mp4',))
    # t2 = MultiThreadHandler(start_recording, ('0',))
    # time.sleep(5)
    # urls.remove('0')
    # start_recording()
    app = Application()
    app.listen(options.port)
    tornado.ioloop.IOLoop.current().start()