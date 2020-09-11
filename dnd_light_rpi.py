import time
from datetime import datetime
import zmq
import blinkt


IDLE_TIME = 3600  # 1 hour
COLOR_VALS = {'off': (0, 0, 0),
              'red': (255, 0, 0),
              'green': (0, 255, 0),
              'blue': (0, 0, 255)}

current_color = 'off'


def set_light(color):
    global current_color

    if color in COLOR_VALS.keys():
        rgb = COLOR_VALS[color]
        blinkt.set_all(rgb[0], rgb[1], rgb[2], 0.1)
        blinkt.show()
        current_color = color
        return True
    else:
        return False


def is_worktime(dt: datetime):
    if dt.weekday() in range(0, 5):
        if dt.hour in range(8, 18):
            return True
        else:
            return False
    else:
        return False


def main():
    if is_worktime(datetime.now()):
        set_light('green')
    else:
        set_light('off')

    last_set_time = datetime.now()
    work_time = is_worktime(datetime.now())

    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:5556")

    while True:
        prev_work_time = work_time
        work_time = is_worktime(datetime.now())
        time_delta = datetime.now() - last_set_time
        idle = time_delta.total_seconds() > IDLE_TIME

        # Turn light on when work starts
        if work_time and not prev_work_time and idle:
            print("Workday started, turning on")
            set_light('green')

        # Turn light off in off hours
        if not work_time and idle:
            print("Off hours and idle, turning off")
            set_light('off')

        try:
            message = socket.recv_string(flags=zmq.NOBLOCK)
            if message == "READ":
                print("DND light is currently set to {}".format(current_color))
                socket.send_string(current_color)
            else:
                if set_light(message):
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


if __name__ == '__main__':
    main()
