import requests
import json

API_KEY = '224e9e51-04ba-48f9-971f-9f6862dba1d3'
HEADERS = {
    'Govee-API-Key': API_KEY
}
url = 'https://developer-api.govee.com/v1/devices'

response = requests.get(url, headers=HEADERS)
devices_info = response.json()

# Loop through and print out device IDs
for device in devices_info.get('data', {}).get('devices', []):
    print(f"Device Name: {device.get('deviceName')}, Model: {device.get('model')}, Device ID: {device.get('device')}")
