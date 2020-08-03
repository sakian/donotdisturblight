import zmq
import time
import blinkt

brightness = 0.1
color_vals = {'off': (0, 0, 0),
        'red': (255, 0, 0),
        'green': (0, 255, 0),
        'blue': (0, 0, 255)}
        
color = color_vals['green']
blinkt.set_all(color[0], color[1], color[2], brightness)
blinkt.show()

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind("tcp://*:5556")

while True:
    message = socket.recv_string()
    
    if message in color_vals.keys():
        color = color_vals[message]
        blinkt.set_all(color[0], color[1], color[2], brightness)
        blinkt.show()
        print("DND light set to {}".format(message))
        socket.send_string("Success")
    else:
        print("{} is not valid".format(message))
        socket.send_string("Failed")

    time.sleep(1)


