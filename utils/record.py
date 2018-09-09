import os
import sys
import time
import io

import coils
import cv2
import numpy as np
from redis import StrictRedis

from .host import *

def start_recording():
    # Retrieve command line arguments.
    width = None if len(sys.argv) <= 1 else int(sys.argv[1])
    height = None if len(sys.argv) <= 2 else int(sys.argv[2])

    width = 640
    height = 360

    # Create video capture object, retrying until successful.
    max_sleep = 5.0
    cur_sleep = 0.1
    while True:
        cap = cv2.VideoCapture('./utils/uncledrew.avi')
        # cap = cv2.VideoCapture(0)
        if cap.isOpened():
            break
        print('not opened, sleeping {}s'.format(cur_sleep))
        time.sleep(cur_sleep)
        if cur_sleep < max_sleep:
            cur_sleep *= 2
            cur_sleep = min(cur_sleep, max_sleep)
            continue
        cur_sleep = 0.1

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
    print('Start Recording...')
    while True:
        hello, image = cap.read()
        if image is None:
            time.sleep(0.5)
            continue
        _, image = cv2.imencode('.jpg', image)
        value = image.tobytes()
        store.set('image', value)
        image_id = os.urandom(4)
        store.set('image_id', image_id)
        # Print the framerate.
        # text = '{:.2f}, {:.2f}, {:.2f} fps'.format(*fps.tick())
        # print(text)
    print('Stop Recording...')