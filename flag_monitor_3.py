import json
import requests
import time
import cv2
import numpy as np
import mss
from queue import Queue
from threading import Thread

API_KEY = "224e9e51-04ba-48f9-971f-9f6862dba1d3"
HEADERS = {
    "Content-Type": "application/json",
    "Govee-API-Key": API_KEY
}

devices = [
    {"name": "Other Strip", "model": "H61A0", "id": "E5:52:D4:AD:FC:73:DA:E1"}
]

pending_tasks = Queue()

def change_color(device, r, g, b):
    device_id = device["id"]
    url = 'https://developer-api.govee.com/v1/devices/control'
    payload = json.dumps({
        "device": device_id,
        "model": device["model"],
        "cmd": {
            "name": "color",
            "value": {
                "r": r,
                "g": g,
                "b": b
            }
        }
    })
    response = requests.put(url, headers=HEADERS, data=payload)
    remaining_calls = int(response.headers.get('API-RateLimit-Remaining'))
    print(int(response.headers.get('API-RateLimit-Remaining')))
    
    if remaining_calls < 1:
        pending_tasks.put((device, r, g, b))
        print(f"Rate limit reached. Queued task for {device['name']}.")
        return

    handle_response(device, response)

def handle_response(device, response):
    try:
        json_response = response.json()
        if json_response.get("code") == 200:
            print(f"Successfully changed color for {device['name']}")
        else:
            print(f"API Error. Response: {json_response}")
    except json.JSONDecodeError:
        print(f"Failed to decode JSON. Response: {response.text}, Status Code: {response.status_code}")

def process_pending_tasks():
    while True:
        if not pending_tasks.empty():
            device, r, g, b = pending_tasks.get()
            change_color(device, r, g, b)
        time.sleep(1)

Thread(target=process_pending_tasks, daemon=True).start()

current_flag = None
safety_car_toggle = False

while True:
    with mss.mss() as sct:
        monitor = {"top": 36, "left": 57, "width": 367, "height": 266}
        sct_img = sct.grab(monitor)

    flag_image = np.array(sct_img)
    hsv = cv2.cvtColor(flag_image, cv2.COLOR_BGR2HSV)

    yellow_lower = np.array([20, 100, 100])
    yellow_upper = np.array([30, 255, 255])
    yellow_mask = cv2.inRange(hsv, yellow_lower, yellow_upper)

    red_lower = np.array([0, 100, 100])
    red_upper = np.array([10, 255, 255])
    red_mask = cv2.inRange(hsv, red_lower, red_upper)

    yellow_count = cv2.countNonZero(yellow_mask)
    red_count = cv2.countNonZero(red_mask)

    new_flag = None

    if yellow_count > 40000:
        new_flag = "Safety Car"
    elif yellow_count > 20000:
        new_flag = "Yellow Flag"
    elif red_count > 20000:
        new_flag = "Red Flag"
    else:
        new_flag = "No Flag"

    if new_flag != current_flag:
        print(f"{new_flag} Detected!")
        current_flag = new_flag
        r, g, b = 255, 255, 255

        if current_flag == "Safety Car":
            r, g, b = 255, 255, 0
        elif current_flag == "Yellow Flag":
            r, g, b = 255, 255, 0
        elif current_flag == "Red Flag":
            r, g, b = 255, 0, 0

        for device in devices:
            change_color(device, r, g, b)

    time.sleep(2)