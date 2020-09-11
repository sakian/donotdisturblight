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

zmq_context = zmq.Context()


def get_light_addresses():
    config = load_json_settings('light_addresses.json', default={'addresses': []})
    config.save()
    return config['addresses']


def notify(icon, msg):
    icon.notify(msg, title=APP_TITLE)
    sleep(3)
    icon.remove_notification()


def send_receive_msg(address, msg):
    try:
        socket = zmq_context.socket(zmq.REQ)
        socket.connect(address)
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
    # Just get from first address
    address = get_light_addresses()[0]
    if not address:
        notify("No light addresses configured")
        return ''

    return send_receive_msg(address, 'READ') == COLOR_AVAILABLE


def send_all_color(color):
    addresses = get_light_addresses()
    if not addresses:
        notify("No light addresses configured")
        return False

    for address in addresses:
        if send_receive_msg(address, color) != "Success":
            notify("Failed to set color ({})".format(address))
            return False
    return True


def set_busy(icon, item):
    if send_all_color(COLOR_BUSY):
        icon.icon = Image.open(ICON_BUSY)


def set_available(icon, item):
    if send_all_color(COLOR_AVAILABLE):
        icon.icon = Image.open(ICON_AVAILABLE)


def toggle(icon, item):
    if is_set_available():
        set_busy(icon, item)
    else:
        set_available(icon, item)


def background_task(icon):
    pass


if __name__ == '__main__':
    # Get current available status and set icon image
    if is_set_available():
        print('avail')
        image = Image.open(ICON_AVAILABLE)
    else:
        print('busy')
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
