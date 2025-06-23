import serial
from serial.serialutil import SerialException
from pynput.keyboard import Controller
import time
import math
import platform
import sys
import vgamepad as vg

baud = 115200
prev_angle = None
ANGLE_THRESHOLD = 1

try:
    from vgamepad import VX360Gamepad
    HAS_GAMEPAD = True
except ImportError as e:
    print(e)
    exit()

# Detect platform
current_platform = platform.system()
keyboard = Controller()

# Set serial port for each platform
if current_platform == "Windows":
    port = 'COM5'
else:
    print("Unsupported platform")
    sys.exit()

def apply_response_curve(value, exponent=2.0):
    sign = 1 if value >= 0 else -1
    normalized = abs(value) / 32767
    curved = normalized ** exponent
    return int(sign * curved * 32767)

def map_potentiometer_to_angle(pot_value, in_min=25, in_max=1010, out_min=-180, out_max=180):
    return (pot_value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

if current_platform == "Windows" and HAS_GAMEPAD:
    gamepad = VX360Gamepad()
    def handle_joystick_input(angle, magnitude):
        if angle > 90:
            angle = 90
        elif angle < -90:
            angle = -90
        angle_rad = math.radians(angle)
        x = math.sin(angle_rad)
        max_val = 32767
        x_val = int(x * magnitude * max_val)
        curved_val=apply_response_curve(x_val)
        gamepad.left_joystick(x_value=curved_val, y_value=0)
        gamepad.update()
else:
    def handle_joystick_input(pot_value):
        angle = map_potentiometer_to_angle(pot_value)

def connect_serial():
    while True:
        try:
            ser = serial.Serial(port, baud, timeout=1)
            print(f"Connected to {port}")
            return ser
        except Exception as e:
            print(f"Serial connection failed: {e}")
            print("Retrying in 3 seconds...")
            time.sleep(3)

ser = connect_serial()

for i in range(0, 3):
    print("Loading" + "." * i, end="\r")
    time.sleep(1)

print("Listening for serial input...")

def tap_button(button_id, delay=0.05):
    gamepad.press_button(button=button_id)
    gamepad.update()
    time.sleep(delay)
    gamepad.release_button(button=button_id)
    gamepad.update()

button_actions = {
    "Button1": lambda: tap_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_A),
    "Button2": lambda: tap_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_B),
    "Button3": lambda: tap_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_X),
    "Button4": lambda: tap_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_Y),
    "Button5": lambda: tap_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT),
    "Button6": lambda: tap_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT),
    "Button7": lambda: tap_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER),  # LB
    "Button8": lambda: tap_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER), # RB
    "upShift": lambda: tap_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER), # RB
    "downShift": lambda: tap_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER) # LB
}

# main loop
while True:
    try:
        if ser.in_waiting:
            line = ser.readline().decode('utf-8').strip()
            if not line:
                continue

            matched_key = next((key for key in button_actions if key in line), None)

            if matched_key:
                try:
                    button_actions[matched_key]()
                except Exception as e:
                    print(f"Error executing action for {matched_key}: {e}")
            else:
                try:
                    pot_value = int(line)
                    angle = map_potentiometer_to_angle(pot_value)
                    if prev_angle is None or abs(angle - prev_angle) >= ANGLE_THRESHOLD:
                        handle_joystick_input(angle*-1, 1)
                        prev_angle = angle
                except ValueError:
                    print(f"Invalid input received: '{line}'")

    except SerialException as e:
        print(f"Serial error: {e}")
        print("Attempting to reconnect to serial...")
        try:
            ser.close()
        except:
            pass
        time.sleep(1)
        ser = connect_serial()
