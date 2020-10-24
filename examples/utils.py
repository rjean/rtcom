
#From : https://stackoverflow.com/questions/43665208/how-to-get-the-latest-frame-from-capture-device-camera-in-opencv
import cv2, threading, queue
from time import sleep

def write_header(image, text):
    cv2.putText(image,text, (10,30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 1)

def write_line(image, line_number, text):
    cv2.putText(image,text, (10,60+20*line_number), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 1)

# bufferless VideoCapture
class VideoCapture:
  def __init__(self, name):
    self.cap = cv2.VideoCapture(name)
    self.q = queue.Queue()
    t = threading.Thread(target=self._reader)
    t.daemon = True
    t.start()

  # read frames as soon as they are available, keeping only most recent one
  def _reader(self):
    while True:
      ret, frame = self.cap.read()
      if not ret:
        break
      if not self.q.empty():
        try:
          self.q.get_nowait()   # discard previous (unprocessed) frame
        except queue.Empty:
          pass
      self.q.put(frame)
      sleep(0.010)

  def read(self):
    return self.q.get()
