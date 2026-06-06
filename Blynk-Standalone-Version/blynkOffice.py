import network
import time
import ntptime
import urequests
from machine import Pin
from secrets import WIFI_PASS, BLYNK_TOKEN

# --- Configuration ---
WIFI_SSID = "dd-wrt"

#  wifi password and blynk token in secrets.py

SENSOR_PIN = 22  # XIAO ESP32-C6 pin D4

# Blynk Virtual Pins (Set for Room 2)
VPIN_STATUS = "v1"
VPIN_DURATION = "v2"

# --- Network Setup ---
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(WIFI_SSID, WIFI_PASS)

print("Connecting to network...")
while not wlan.isconnected():
    time.sleep(1)
print("Network config:", wlan.ifconfig())

# --- Sync Network Time ---
try:
    ntptime.settime()
    print("Time synchronized successfully.")
except Exception as e:
    print("Failed to sync time:", e)

# --- Functions ---
def get_local_timestamp():
    # Grab current UTC time
    utc = time.localtime()
    
    # Apply Pacific Daylight Time (PDT) offset of -7 hours
    offset_hours = -7
    local_hour = (utc[3] + offset_hours) % 24
    
    # Format to 12-hour AM/PM
    am_pm = "AM" if local_hour < 12 else "PM"
    display_hour = local_hour % 12
    if display_hour == 0:
        display_hour = 12
        
    return f"{display_hour}:{utc[4]:02d} {am_pm}"

def send_to_blynk(status_text, duration_text):
    # Replace spaces with %20 so the URL is valid
    safe_status = status_text.replace(" ", "%20")
    safe_duration = duration_text.replace(" ", "%20")
    
    # Using the batch update endpoint for multiple pins
    url = f"https://blynk.cloud/external/api/batch/update?token={BLYNK_TOKEN}&{VPIN_STATUS}={safe_status}&{VPIN_DURATION}={safe_duration}"
    
    try:
        response = urequests.get(url)
        if response.status_code == 200:
            print(f"Sent to Blynk: {status_text} | {duration_text}")
        else:
            print(f"Blynk Server Error: {response.status_code}")
        response.close()
    except Exception as e:
        print("Network Error:", e)

# --- Main Monitoring Loop ---
sensor = Pin(SENSOR_PIN, Pin.IN)
is_occupied = False
occupancy_start_time = 0
last_minute_logged = -1
arrival_time_str = ""

print("System Ready. Monitoring Room 2...")

while True:
    current_state = sensor.value()
    
    # State Change: Empty -> Occupied
    if current_state == 1 and not is_occupied:
        is_occupied = True
        occupancy_start_time = time.time()
        last_minute_logged = 0
        
        arrival_time_str = get_local_timestamp()
        
        status = "Occupied"
        duration = f"Just arrived ({arrival_time_str})"
        send_to_blynk(status, duration)
        
    # State Change: Occupied -> Empty
    elif current_state == 0 and is_occupied:
        is_occupied = False
        
        departure_time_str = get_local_timestamp()
        
        status = "Empty"
        duration = f"Left at {departure_time_str}"
        send_to_blynk(status, duration)
        
    # Ongoing Occupancy: Update every minute
    elif is_occupied:
        elapsed_seconds = time.time() - occupancy_start_time
        elapsed_minutes = int(elapsed_seconds / 60)
        
        if elapsed_minutes > last_minute_logged:
            last_minute_logged = elapsed_minutes
            
            status = "Occupied"
            duration = f"For {elapsed_minutes} mins ({arrival_time_str})"
            send_to_blynk(status, duration)
            
    time.sleep(1)
