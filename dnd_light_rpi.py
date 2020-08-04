import time
from datetime import datetime
import zmq
import blinkt


def set_light(rgb):
    blinkt.set_all(rgb[0], rgb[1], rgb[2], 0.1)
    blinkt.show()


def is_worktime(dt: datetime):
    if dt.weekday() in range(0, 5):
        if dt.hour in range(8, 18):
            return True
        else:
            return False
    else:
        return False


brightness = 0.1
color_vals = {'off': (0, 0, 0),
              'red': (255, 0, 0),
              'green': (0, 255, 0),
              'blue': (0, 0, 255)}

set_light(color_vals['green'])

idle_time = 3600 * 2  # 2 hours
last_set_time = datetime.now()

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind("tcp://*:5556")

while True:
    time_delta = datetime.now() - last_set_time
    if time_delta.total_seconds() > idle_time:
        if not is_worktime(datetime.now()):
            print("DND light idle")
            set_light(color_vals['off'])

    try:
        message = socket.recv_string(flags=zmq.NOBLOCK)

        if message in color_vals.keys():
            set_light(color_vals[message])
            print("DND light set to {}".format(message))
            socket.send_string("Success")
            last_set_time = datetime.now()
        else:
            print("{} is not valid".format(message))
            socket.send_string("Failed")
    except zmq.Again as e:
        # No messages received
        pass

    time.sleep(0.1)
