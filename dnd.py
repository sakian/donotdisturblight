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
START_OFFSET = 2  # Minutes

stop_app = False
zmq_context = None
zmq_socket_defs = None
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
        global zmq_socket_defs
        zmq_sockets = []
        for address in addresses:
            socket = zmq_context.socket(zmq.REQ)
            socket.connect(address)
            zmq_sockets.append((socket, address))


def reconnect(socket, address):
    socket.disconnect(address)
    socket.connect(address)


def send_receive_msg(socket_def, msg):
    try:
        socket, address = socket_def
        socket.send_string(msg)

        tries = 0
        while True:
            try:
                return socket.recv_string(flags=zmq.NOBLOCK)
            except zmq.Again as e:
                # No messages received
                tries += 1

                # Try reconnect every 5 retries
                _, mod = divmod(tries, 5)
                if mod == 0:
                    reconnect(socket, address)

                # Eventually give up
                if tries > 100:
                    return ''
                else:
                    sleep(0.1)
    except:
        return ''


def is_set_available():
    # Just get status from first light (assume others match)
    if zmq_socket_defs:
        socket_def = zmq_socket_defs[0]
        return send_receive_msg(socket_def, 'READ') == COLOR_AVAILABLE
    else:
        return False


def set_color(icon, color):
    if zmq_socket_defs:
        for socket_def in zmq_socket_defs:
            if send_receive_msg(socket_def, color) != "Success":
                notify(icon, "Failed to set color ({})".format(socket_def[1]))
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


def get_busy_events(icon):
    if gcal_service:
        # Get next 10 events
        now = datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        now = "2020-10-05T00:00:00Z"
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
            start_offset = start - timedelta(0, START_OFFSET*60)  # Add buffer to beginning of event
            if start_offset < datetime.now():
                filter_events.append(event)
        event_list = filter_events

        # Filter to get only events I accepted
        event_list = [event for event in event_list if event['status'] == 'confirmed' or event['status'] == 'tentative']

        # Filter to get only events that include a link the the description (assume it's a meeting link) or direct conference link
        filter_events = []
        for event in event_list:
            # find links in description
            description = event.get('description', '')
            urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', description)

            # Check if conference info exists
            conference_info = event.get('conferenceData', '')

            if urls or conference_info:
                filter_events.append(event)
        event_list = filter_events

        # Return list of events
        events = []
        for event in event_list:
            events.append(event.get('summary', 'Unnamed Meeting'))
        return events

    # Not on call or couldn't get events
    return []


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
    event_list = []
    while True:
        if stop_app:
            break

        # Check if just started event
        prev_event_list = event_list
        event_list = get_busy_events(icon)
        if event_list != prev_event_list:
            # Call finished
            if not event_list and not is_set_available():
                set_available(icon)
                notify(icon, "Finished Call (reset to busy if call is still active)")

            # New call beginning
            if event_list:
                set_busy(icon)
                notify(icon, "Call starts in {} minutes (setting to busy early if not already set)".format(START_OFFSET, event_list[0]))

        # Wait 1 min (but allow app to be killed)
        count = 0
        while count < 60:
            sleep(1)
            count += 1
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
