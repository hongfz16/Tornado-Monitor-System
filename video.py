import cv2
import time
import numpy as np
import redis

MAX_FPS = 100

class UsbCamera(object):
    def __init__(self):
        self._store = redis.StrictRedis(host='localhost', port=6379, db=0)
        self._prev_image_id = None
    def get_frame(self, fdenable):
        while True:
            time.sleep(1./MAX_FPS)
            image_id = self._store.get('image_id')
            if image_id != self._prev_image_id:
                break
        self._prev_image_id = image_id
        image = self._store.get('image')
        return image
    def decode_image(self, imbytes):
        jpeg = np.asarray(bytearray(imbytes), dtype="uint8")
        jpeg = cv2.imdecode(jpeg,cv2.IMREAD_COLOR)
        return jpeg

# cam = UsbCamera()
# while True:
#     cam.get_frame(False)