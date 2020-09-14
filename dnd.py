from pystray import Icon, Menu, MenuItem
from PIL import Image
from time import sleep
from easysettings import load_json_settings
import zmq
import os
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import dateutil.parser
import re


APP_TITLE = "Do Not Disturb Light"
ICON_BUSY = 'dndon.ico'
ICON_AVAILABLE = 'dndoff.ico'
ICON_UNKNOWN = 'dndunknown.ico'
COLOR_BUSY = 'red'
COLOR_AVAILABLE = 'green'

stop_app = False
zmq_context = None
zmq_sockets = None
gcal_service = None


def get_light_addresses():
    config = load_json_settings('light_addresses.json', default={'addresses': []})
    config.save()
    return config['addresses']


def init_connections(icon):
    # Setup ZMQ context
    global zmq_context
    zmq_context = zmq.Context()

    # Setup connections to lights
    addresses = get_light_addresses()
    if not addresses:
        notify(icon, "No light addresses configured")
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


def set_color(icon, color):
    if zmq_sockets:
        for socket in zmq_sockets:
            if send_receive_msg(socket, color) != "Success":
                notify(icon, "Failed to set color ({})".format(socket))
                return False
    return True


def init_gcal_creds(icon):
    # Handle google credentials
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if os.path.exists('credentials.json'):
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json',
                    ['https://www.googleapis.com/auth/calendar.readonly']
                )
                creds = flow.run_local_server(port=0)

        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    # Set service
    global gcal_service
    gcal_service = build('calendar', 'v3', credentials=creds)


def check_if_on_call(icon):
    if gcal_service:
        # Get next 10 events
        now = datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        event_list = gcal_service.events().list(
            calendarId='primary',
            timeMin=now,
            maxResults=10,
            singleEvents=True,
            orderBy='startTime'
        ).execute().get('items', [])

        # Filter to get running events
        filter_events = []
        for event in event_list:
            start_str = event['start'].get('dateTime', event['start'].get('date'))
            start = dateutil.parser.parse(start_str).replace(tzinfo=None)
            start_offset = start - datetime.timedelta(0, 5*60)  # Add 5 min buffer to beginning of event
            if start_offset < datetime.now():
                filter_events.append(event)
        event_list = filter_events

        # Filter to get only events I accepted
        event_list = [event for event in event_list if event['status'] == 'confirmed' or event['status'] == 'tentative']

        # Filter to get only events that include a link the the description (assume it's a meeting link)
        filter_events = []
        for event in event_list:
            description = event.get('description', '')
            urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', description)
            if urls:
                filter_events.append(event)
        event_list = filter_events

        # If there are any events not filtered out, we're on a call
        if event_list:
            summary = event.get('summary', 'Unnamed Meeting')
            return True, summary

    # Not on call or couldn't get events
    return False, ""


def set_busy(icon, item=""):
    if set_color(icon, COLOR_BUSY):
        icon.icon = Image.open(ICON_BUSY)


def set_available(icon, item=""):
    if set_color(icon, COLOR_AVAILABLE):
        icon.icon = Image.open(ICON_AVAILABLE)


def toggle(icon, item=""):
    if is_set_available():
        set_busy(icon, item)
    else:
        set_available(icon, item)


def exit_app(icon, item=""):
    global stop_app
    stop_app = True
    icon.stop()


def background_task(icon):
    # Setup connections to lights
    init_connections(icon)

    # Get current available status and set icon image
    if is_set_available():
        icon.icon = Image.open(ICON_AVAILABLE)
    else:
        icon.icon = Image.open(ICON_BUSY)

    # Setup Google calendar access
    init_gcal_creds(icon)

    # Check if on call
    on_call = False
    while True:
        if stop_app:
            break

        prev_on_call = on_call
        on_call, summary = check_if_on_call(icon)

        # Check if just joined a call
        if on_call and not prev_on_call:
            set_busy(icon)
            notify(icon, "Starting Call ({})".format(summary))

        # Check if just left a call
        if not on_call and prev_on_call:
            set_available(icon)
            notify(icon, "Finished Call")

        # Wait 1 min (but allow app to be killed)
        count = 0
        while count < 60:
            sleep(1)
            count += 1
            print(count)
            if stop_app:
                break


def notify(icon, msg):
    icon.notify(msg, title=APP_TITLE)
    sleep(3)
    icon.remove_notification()


if __name__ == '__main__':
    # Setup Menu
    toggle_menu_item = MenuItem('Toggle', toggle, default=True)
    set_available_menu_item = MenuItem('Available', set_available)
    set_busy_menu_item = MenuItem('Busy', set_busy)
    exit_menu_item = MenuItem('Exit', exit_app)
    menu = Menu(
        toggle_menu_item,
        set_available_menu_item,
        set_busy_menu_item,
        exit_menu_item
    )

    # Start Tray App
    image = Image.open(ICON_UNKNOWN)
    tray = Icon(APP_TITLE, image, menu=menu)
    tray.visible = True
    tray.run(setup=background_task)
