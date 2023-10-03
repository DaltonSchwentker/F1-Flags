import json
import requests
import time
import cv2
import numpy as np
import mss
from queue import Queue
from threading import Thread
from screeninfo import get_monitors
from enum import Enum
import configparser

# Load configuration
config = configparser.ConfigParser()
config.read('config.ini')
API_KEY = config['DEFAULT']['API_KEY']

# Define devices
devices = [{"name": "Other Strip", "model": "H61A0", "id": "E5:52:D4:AD:FC:73:DA:E1"}]

pending_tasks = Queue()

class Flag(Enum):
    SAFETY_CAR = "Safety Car"
    YELLOW_FLAG = "Yellow Flag"
    RED_FLAG = "Red Flag"
    TRACK_CLEAR = "Track Clear"
    NO_FLAG = "No Flag"

class GoveeAPI:
    BASE_URL = 'https://developer-api.govee.com/v1/devices/control'
    HEADERS = {"Content-Type": "application/json"}

    def __init__(self, api_key):
        self.headers = {**self.HEADERS, "Govee-API-Key": api_key}

    def change_color(self, device, r, g, b):
        payload = json.dumps({
            "device": device["id"],
            "model": device["model"],
            "cmd": {"name": "color", "value": {"r": r, "g": g, "b": b}}
        })
        response = requests.put(self.BASE_URL, headers=self.headers, data=payload)
        self.handle_response(device, response)

    def handle_response(self, device, response):
        try:
            json_response = response.json()
            if json_response.get("code") == 200:
                print(f"Successfully changed color for {device['name']}")
            else:
                print(f"API Error. Response: {json_response}")
        except json.JSONDecodeError:
            print(f"Failed to decode JSON. Response: {response.text}, Status Code: {response.status_code}")

govee_api = GoveeAPI(API_KEY)

def process_pending_tasks():
    while True:
        if not pending_tasks.empty():
            device, r, g, b = pending_tasks.get()
            govee_api.change_color(device, r, g, b)
        time.sleep(1)

Thread(target=process_pending_tasks, daemon=True).start()

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

    r_adjusted = (r[0] + chosen_monitor.x, r[1] + chosen_monitor.y, r[2], r[3])
    return r_adjusted


def detect_flag(hsv):
    yellow_lower = np.array([20, 100, 100])
    yellow_upper = np.array([30, 255, 255])
    orange_lower = np.array([10, 100, 100])
    orange_upper = np.array([20, 255, 255])
    green_lower = np.array([35, 100, 100])
    green_upper = np.array([85, 255, 255])
    red_lower = np.array([0, 100, 100])
    red_upper = np.array([10, 255, 255])

    yellow_mask = cv2.inRange(hsv, yellow_lower, yellow_upper)
    orange_mask = cv2.inRange(hsv, orange_lower, orange_upper)
    green_mask = cv2.inRange(hsv, green_lower, green_upper)
    red_mask = cv2.inRange(hsv, red_lower, red_upper)

    yellow_count = cv2.countNonZero(yellow_mask)
    orange_count = cv2.countNonZero(orange_mask)
    green_count = cv2.countNonZero(green_mask)
    red_count = cv2.countNonZero(red_mask)

    if orange_count > 600:
        return Flag.SAFETY_CAR
    elif yellow_count > 600:
        return Flag.YELLOW_FLAG
    elif red_count > 600:
        return Flag.RED_FLAG
    elif green_count > 600:
        return Flag.TRACK_CLEAR
    else:
        return Flag.NO_FLAG

def main():
    roi = select_roi()
    current_flag = None

    while True:
        with mss.mss() as sct:
            monitor = {"top": roi[1], "left": roi[0], "width": roi[2], "height": roi[3]}
            sct_img = sct.grab(monitor)

        flag_image = np.array(sct_img)
        hsv = cv2.cvtColor(flag_image, cv2.COLOR_BGR2HSV)
        new_flag = detect_flag(hsv)

        if new_flag != current_flag:
            print(f"{new_flag.value} Detected!")
            current_flag = new_flag
            r, g, b = 255, 255, 255  # default color

            if current_flag == Flag.SAFETY_CAR:
                r, g, b = 255, 165, 0
            elif current_flag == Flag.YELLOW_FLAG:
                r, g, b = 255, 255, 0
            elif current_flag == Flag.RED_FLAG:
                r, g, b = 255, 0, 0
            elif current_flag == Flag.TRACK_CLEAR:
                r, g, b = 0, 255, 0

            for device in devices:
                govee_api.change_color(device, r, g, b)

if __name__ == "__main__":
    main()