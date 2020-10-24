import io
import time
import cv2

from rtcom import RealTimeCommunication
from PIL import Image, ImageDraw
import numpy as np
from threading import Thread



import cv2, queue, threading, time

with RealTimeCommunication("rpi") as rtcom:
    cap = VideoCapture(0)
    first_pass = True 
    data = {}
    loop_start_time=0

    while(True):
        data["Cycle Time"] = ((time.perf_counter() - loop_start_time)*1000, "ms")
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 70]
        frame = cap.read()
        loop_start_time=time.perf_counter()
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        ret, jpg_image = cv2.imencode("*.jpg",frame, encode_param)
        rtcom.broadcast_endpoint("camera", bytes(jpg_image), encoding="binary")
        rtcom.broadcast_endpoint("data",data)


        
