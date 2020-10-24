from rtcom import RealTimeCommunication
import cv2
import numpy as np
from time import sleep
from utils import VideoCapture, write_header, write_line

with RealTimeCommunication("pc") as rtcom:
    rtcom.subscribe("rpi","camera") #Request unicast for this specific endpoint.
    #(Too much packet drop on multicast for some reason.)
    print("Press escape to quit.")
    while True:
        try:
            image_data = rtcom["rpi"]["camera"]
            if image_data is not None:
                jpg_data = np.asarray(image_data)
                img = cv2.imdecode(jpg_data, cv2.IMREAD_UNCHANGED)
                write_header(img, "Video Feed")
                data = rtcom["rpi"]["data"]
                for i, name in enumerate(data):
                    write_line(img, i, f"{name} : {data[name][0]:0.1f} {data[name][1]}")                
                cv2.imshow("preview", img) 

            key = cv2.waitKey(20)
            if key==-1: 
                key=None
            else:
                key=chr(key)

            if key==27: #Escape key
                break
        except KeyError:
            pass

