from system_tray import SysTrayIcon
from plyer import notification
from time import sleep
from easysettings import load_json_settings
import zmq

import psutil
import re
import threading


hover_text = "Do Not Disturb Light"
busy_icon = 'dndon.ico'
available_icon = 'dndoff.ico'
unknown_icon = 'dndunknown.ico'
monitor_period = 10
zoom_limit = 440
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

        tries = 0
        while True:
            try:
                resp = socket.recv_string(flags=zmq.NOBLOCK)
                return resp == "Success"
            except zmq.Again as e:
                # No messages received
                tries += 1
                if tries > 100:
                    return False
                else:
                    sleep(0.1)
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


def monitor_zoom():
    cpu_sum = 0
    cpu_sum_prev = 0

    while True:
        # Get Zoom CPU time
        zoom_cpu = []
        for proc in psutil.process_iter(['name', 'cpu_times']):
            if re.search("zoom", proc.info['name'], re.IGNORECASE):
                zoom_cpu.append(proc.info['cpu_times'].user)
        cpu_sum_prev = cpu_sum
        cpu_sum = sum(zoom_cpu)

        # Check if we should set busy
        if cpu_sum >= zoom_limit > cpu_sum_prev:
            set_busy()

        # Check if we should set available
        if cpu_sum < zoom_limit <= cpu_sum_prev:
            set_available()

        print(sum(zoom_cpu))
        sleep(monitor_period)


if __name__ == '__main__':
    threading.Thread(target=monitor_zoom).start()

    menu_options = (('Toggle', None, toggle),
                    ('Available', available_icon, set_available),
                    ('Busy', busy_icon, set_busy))
    SysTrayIcon(unknown_icon, hover_text, menu_options)

