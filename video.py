import cv2
import numpy as np

class UsbCamera(object):

    """ Init camera """
    def __init__(self):
        # select first video device in system
        self.cam = cv2.VideoCapture(0)
        # set camera resolution
        self.w = int(self.cam.get(3))
        self.h = int(self.cam.get(4))
        # set crop factor
        self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, self.h)
        self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, self.w)
        # load cascade file
        self.face_cascade = cv2.CascadeClassifier('face.xml')

    def __del__(self):
        self.cam.release()

    def set_resolution(self, new_w, new_h):
        """
        functionality: Change camera resolution
        inputs: new_w, new_h - with and height of picture, must be int
        returns: None ore raise exception
        """
        if isinstance(new_h, int) and isinstance(new_w, int):
            # check if args are int and correct
            if (new_w <= 800) and (new_h <= 600) and \
               (new_w > 0) and (new_h > 0):
                self.h = new_h
                self.w = new_w
            else:
                # bad params
                raise Exception('Bad resolution')
        else:
            # bad params
            raise Exception('Not int value')

    def get_frame(self, fdenable):
        """
        functionality: Gets frame from camera and try to find feces on it
        :return: byte array of jpeg encoded camera frame
        """
        success, image = self.cam.read()
        # cv2.waitKey(5)
        # cv2.imshow('frame',image)
        # image = cv2.resize(image, (640, 360), interpolation=cv2.INTER_CUBIC)
        if success:
            # scale image
            image = cv2.resize(image, (640, 360), interpolation=cv2.INTER_CUBIC)
            if fdenable:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
                for (x,y,w,h) in faces:
                    cv2.rectangle(image, (x,y), (x+w, y+h), (255,0,0), 2)
        else:
            image = np.zeros((self.h, self.w, 3), np.uint8)
            cv2.putText(image, 'No camera', (40, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 1)
        # encoding picture to jpeg
        # cv2.imshow('frame',image)
        ret, jpeg = cv2.imencode('.jpg', image)
        return jpeg.tostring()

# cam = UsbCamera()
# while True:
#     cam.get_frame(False)