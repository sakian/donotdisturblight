from system_tray import SysTrayIcon
from plyer import notification
from easysettings import load_json_settings
import zmq

#server_addresses = ["tcp://192.168.1.194:5556", "tcp://192.168.1.194:5556"]
hover_text = "Do Not Disturb Light"
busy_icon = 'dndon.ico'
available_icon = 'dndoff.ico'
unknown_icon = 'dndunknown.ico'
zmq_context = zmq.Context()


def get_light_addresses():
    config = load_json_settings('light_addresses.json', default={'addresses': []})
    config.save()
    return config['addresses']


def notify(msg):
    notification.notify(
        title='Do Not Disturb Light',
        message=msg,
        app_name='Do Not Disturb Light',
        app_icon=busy_icon,
        timeout=3
    )


def send_color(color, address):
    try:
        socket = zmq_context.socket(zmq.REQ)
        socket.connect(address)
        socket.send_string(color)
        return socket.recv_string() == "Success"
    except:
        return False


def send_all_color(color):
    addresses = get_light_addresses()
    if not addresses:
        notify("No light addresses configured")
        return False

    for address in addresses:
        if not send_color(color, address):
            notify("Failed to set color ({})".format(address))
            return False
    return True


def set_busy(SysTrayIcon):
    if send_all_color('red'):
        SysTrayIcon.icon = busy_icon
        SysTrayIcon.refresh_icon()


def set_available(SysTrayIcon):
    if send_all_color('green'):
        SysTrayIcon.icon = available_icon
        SysTrayIcon.refresh_icon()


def toggle(SysTrayIcon):
    if SysTrayIcon.icon == busy_icon:
        set_available(SysTrayIcon)
    else:
        set_busy(SysTrayIcon)


if __name__ == '__main__':
    menu_options = (('Toggle', None, toggle),
                    ('Available', available_icon, set_available),
                    ('Busy', busy_icon, set_busy))
    SysTrayIcon(unknown_icon, hover_text, menu_options)
