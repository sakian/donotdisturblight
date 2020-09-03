import psutil
import re

while True:
    zoom_vms = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_times']):
        if re.search("zoom", proc.info['name'], re.IGNORECASE):
            zoom_vms.append(proc.info['cpu_times'].user)

    print(sum(zoom_vms))
