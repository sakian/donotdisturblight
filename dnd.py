from pystray import Icon, Menu, MenuItem
from PIL import Image
from time import sleep
from easysettings import load_json_settings
import zmq


APP_TITLE = "Do Not Disturb Light"
ICON_BUSY = 'dndon.ico'
ICON_AVAILABLE = 'dndoff.ico'
ICON_UNKNOWN = 'dndunknown.ico'
COLOR_BUSY = 'red'
COLOR_AVAILABLE = 'green'

zmq_context = None
zmq_sockets = None


def get_light_addresses():
    config = load_json_settings('light_addresses.json', default={'addresses': []})
    config.save()
    return config['addresses']


def init_connections():
    # Setup ZMQ context
    global zmq_context
    zmq_context = zmq.Context()

    # Setup connections to lights
    addresses = get_light_addresses()
    if not addresses:
        notify("No light addresses configured")
    else:
        global zmq_sockets
        zmq_sockets = []
        for address in addresses:
            socket = zmq_context.socket(zmq.REQ)
            socket.connect(address)
            zmq_sockets.append(socket)


def send_receive_msg(socket, msg):
    try:
        socket.send_string(msg)

        tries = 0
        while True:
            try:
                return socket.recv_string(flags=zmq.NOBLOCK)
            except zmq.Again as e:
                # No messages received
                tries += 1
                if tries > 100:
                    return ''
                else:
                    sleep(0.1)
    except:
        return ''


def is_set_available():
    # Just get status from first light (assume others match)
    if zmq_sockets:
        socket = zmq_sockets[0]
        return send_receive_msg(socket, 'READ') == COLOR_AVAILABLE
    else:
        return False


def set_color(color):
    if zmq_sockets:
        for socket in zmq_sockets:
            if send_receive_msg(socket, color) != "Success":
                notify("Failed to set color ({})".format(socket))
                return False
    return True


def set_busy(icon, item):
    if set_color(COLOR_BUSY):
        icon.icon = Image.open(ICON_BUSY)


def set_available(icon, item):
    if set_color(COLOR_AVAILABLE):
        icon.icon = Image.open(ICON_AVAILABLE)


def toggle(icon, item):
    if is_set_available():
        set_busy(icon, item)
    else:
        set_available(icon, item)


def background_task(icon):
    pass


def notify(icon, msg):
    icon.notify(msg, title=APP_TITLE)
    sleep(3)
    icon.remove_notification()


if __name__ == '__main__':
    # Setup connections to lights
    init_connections()

    # Get current available status and set icon image
    if is_set_available():
        image = Image.open(ICON_AVAILABLE)
    else:
        image = Image.open(ICON_BUSY)

    # Setup Menu
    toggle_menu_item = MenuItem('Toggle', toggle, default=True)
    set_available_menu_item = MenuItem('Available', set_available)
    set_busy_menu_item = MenuItem('Busy', set_busy)
    menu = Menu(
        toggle_menu_item,
        set_available_menu_item,
        set_busy_menu_item
    )

    # Start Tray App
    tray = Icon(APP_TITLE, image, menu=menu)
    # tray.run(setup=background_task)
    tray.run()
