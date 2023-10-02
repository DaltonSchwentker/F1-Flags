import json
import requests
import time
import cv2
import numpy as np
import mss
from queue import Queue
from threading import Thread
from screeninfo import get_monitors

API_KEY = "224e9e51-04ba-48f9-971f-9f6862dba1d3"
HEADERS = {
    "Content-Type": "application/json",
    "Govee-API-Key": API_KEY
}

devices = [
    {"name": "Other Strip", "model": "H61A0", "id": "E5:52:D4:AD:FC:73:DA:E1"}
]

pending_tasks = Queue()

def select_roi():
    monitors = get_monitors()
    for i, monitor in enumerate(monitors):
        print(f"{i}: {monitor}")

    monitor_choice = int(input("Enter the number of the monitor you want to use: "))
    chosen_monitor = monitors[monitor_choice]

    with mss.mss() as sct:
        monitor = {
            "top": chosen_monitor.y,
            "left": chosen_monitor.x,
            "width": chosen_monitor.width,
            "height": chosen_monitor.height
        }
        sct_img = sct.grab(monitor)
        img_np = np.array(sct_img)
        img_rgb = cv2.cvtColor(img_np, cv2.COLOR_RGBA2RGB)
        r = cv2.selectROI(img_rgb)
        cv2.destroyAllWindows()

    # Adjust the ROI coordinates to account for the monitor's position
    r_adjusted = (r[0] + chosen_monitor.x, r[1] + chosen_monitor.y, r[2], r[3])
    return r_adjusted

roi = select_roi()  # Call this at the start of your script

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

while True:
    with mss.mss() as sct:
        monitor = {"top": roi[1], "left": roi[0], "width": roi[2], "height": roi[3]}
        sct_img = sct.grab(monitor)

    flag_image = np.array(sct_img)
    hsv = cv2.cvtColor(flag_image, cv2.COLOR_BGR2HSV)

    # Define color ranges
    yellow_lower = np.array([20, 100, 100])
    yellow_upper = np.array([30, 255, 255])
    orange_lower = np.array([10, 100, 100])
    orange_upper = np.array([20, 255, 255])
    green_lower = np.array([35, 100, 100])
    green_upper = np.array([85, 255, 255])
    red_lower = np.array([0, 100, 100])
    red_upper = np.array([10, 255, 255])

    # Create masks
    yellow_mask = cv2.inRange(hsv, yellow_lower, yellow_upper)
    orange_mask = cv2.inRange(hsv, orange_lower, orange_upper)
    green_mask = cv2.inRange(hsv, green_lower, green_upper)
    red_mask = cv2.inRange(hsv, red_lower, red_upper)

    # Count non-zero pixels
    yellow_count = cv2.countNonZero(yellow_mask)
    orange_count = cv2.countNonZero(orange_mask)
    green_count = cv2.countNonZero(green_mask)
    red_count = cv2.countNonZero(red_mask)

    print(f"Yellow pixels: {yellow_count}, Orange pixels: {orange_count}, Green pixels: {green_count}, Red pixels: {red_count}")

    # Display the color masks with pixel count
    cv2.putText(yellow_mask, f'Count: {yellow_count}', (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 2)
    cv2.putText(orange_mask, f'Count: {orange_count}', (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 2)
    cv2.putText(green_mask, f'Count: {green_count}', (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 2)
    cv2.putText(red_mask, f'Count: {red_count}', (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 2)
    
    cv2.imshow('Yellow Mask', yellow_mask)
    cv2.imshow('Orange Mask', orange_mask)
    cv2.imshow('Green Mask', green_mask)
    cv2.imshow('Red Mask', red_mask)
    cv2.waitKey(1)

    new_flag = None

    # Set flags based on color pixel counts
    if orange_count > 600:  # Adjust this threshold as needed
        new_flag = "Safety Car"
    elif yellow_count > 600:  # Adjust this threshold as needed
        new_flag = "Yellow Flag"
    elif red_count > 600:  # Adjust this threshold as needed
        new_flag = "Red Flag"
    elif green_count > 600:  # Adjust this threshold as needed
        new_flag = "Track Clear"
    else:
        new_flag = "No Flag"

    if new_flag != current_flag:
        print(f"{new_flag} Detected!")
        current_flag = new_flag
        r, g, b = 255, 255, 255

        # Set color for each flag condition
        if current_flag == "Safety Car":
            r, g, b = 255, 165, 0  # Orange
        elif current_flag == "Yellow Flag":
            r, g, b = 255, 255, 0  # Yellow
        elif current_flag == "Red Flag":
            r, g, b = 255, 0, 0  # Red
        elif current_flag == "Track Clear":
            r, g, b = 0, 255, 0  # Green

        for device in devices:
            change_color(device, r, g, b)

    time.sleep(2)