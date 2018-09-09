import face_recognition
import cv2
import time
import numpy as np
import redis
import pickle
import os

redishost = 'redis'

MAX_FPS = 100

def decode_image(imbytes):
    jpeg = np.asarray(bytearray(imbytes), dtype="uint8")
    jpeg = cv2.imdecode(jpeg,cv2.IMREAD_COLOR)
    return jpeg

def analyze_cam():
    store = redis.StrictRedis(host=redishost, port=6379, db=0)
    prev_image_id = None
    # face_cascade = cv2.CascadeClassifier('face.xml')
    analyze_this_frame = True
    last_detected = set()
    while True:
        while True:
            time.sleep(1./MAX_FPS)
            image_id = store.get('image_id')
            if image_id != prev_image_id:
                break
        if analyze_this_frame:
            current = time.strftime('%Y.%m.%d %H:%M:%S',time.localtime(time.time()+28800))
            prev_image_id = image_id
            image = store.get('image')
            frame = decode_image(image)
            detected = set()

            # gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # faces = face_cascade.detectMultiScale(gray, 1.3, 5)
            # store.set('num_face', len(faces))

            # small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
            rgb_small_frame = frame[:, :, ::-1]
            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
            faces= []
            for face_location, face_encoding in zip(face_locations, face_encodings):
                # See if the face is a match for the known face(s)
                matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
                name = "Unknown"
                # If a match was found in known_face_encodings, just use the first one.
                if True in matches:
                    first_match_index = matches.index(True)
                    name = known_face_names[first_match_index]
                if name in detected:
                    name = "Unknown"
                else:
                    detected.add(name)
                faces.append({"name":name, "location":face_location})

            GetIn = detected - last_detected
            GetOut = last_detected - detected
            if len(GetIn | GetOut) > 0:
                warning_id = os.urandom(4)
                warnings = []
                for GetInName in GetIn:
                    if (GetInName == 'Unknown'):
                        continue
                    warning = {}
                    warning['name'] = GetInName
                    warning['time'] = current
                    warning['type'] = 'in'
                    warnings.append(warning)
                for GetOutName in GetOut:
                    if (GetOutName == 'Unknown'):
                        continue
                    warning = {}
                    warning['name'] = GetOutName
                    warning['time'] = current
                    warning['type'] = 'out'
                    warnings.append(warning)
                # print(warnings)
                store.set("warning_id", warning_id)
                store.set("warning", pickle.dumps(warnings))

            store.set("faces",pickle.dumps(faces))
            last_detected = detected
        analyze_this_frame = not analyze_this_frame


if __name__ == "__main__":
    print("Initializing face recognition module...")
    known_face_encodings = []
    known_face_names = []
    path = './known_faces/'
    dirs = os.listdir(path)
    for filename in dirs:
        name = filename.split('.')[0]
        img = face_recognition.load_image_file(path+filename)
        img_encoding = face_recognition.face_encodings(img)[0]
        known_face_encodings.append(img_encoding)
        known_face_names.append(name)
    print("Finish initializing...")
    print("Start analyzing...")
    analyze_cam()