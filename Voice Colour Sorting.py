#!/usr/bin/env python
# coding: utf-8

# In[1]:


import sounddevice as sd

print(sd.query_devices())


# In[2]:


import cv2
import time
import gc
import threading
import queue
import json
import numpy as np
import sounddevice as sd
import ipywidgets as widgets
from IPython.display import display
from scipy.optimize import minimize
from vosk import Model, KaldiRecognizer
import Arm_Lib


# In[3]:


# ==========================================
# 1. HARDWARE & INITIALIZATION
# ==========================================
Arm = Arm_Lib.Arm_Device()
time.sleep(0.2)

HOME_POSE = [90, 120, 0, 0, 90, 10]
Arm.Arm_serial_servo_write6_array(HOME_POSE, 1000)

CAMERA_INDEX = 0
MIC_INDEX = 3
VOSK_MODEL_PATH = "vosk-model-small-en-us-0.15"


# In[4]:


# ==========================================
# 2. INVERSE KINEMATICS (IK)
# ==========================================
D0 = 0.0895; D1 = 0.0330; A2 = 0.08285; A3 = 0.08285; D4 = 0.07815; D5 = 0.0900

J_MIN = np.array([-np.pi/2]*5)
J_MAX = np.array([ np.pi/2, np.pi/2, np.pi/2, np.pi/2, np.pi])

def fk(q):
    q1, q2, q3, q4, q5 = q
    a2 = -q2; a3 = -(q2+q3); a4 = -(q2+q3+q4)
    r = A2*np.sin(a2) + A3*np.sin(a3) + (D4+D5)*np.sin(a4)
    z = D0 + D1 + A2*np.cos(a2) + A3*np.cos(a3) + (D4+D5)*np.cos(a4)
    return np.array([r*np.cos(q1), r*np.sin(q1), z])

def ik(target, seed=None):
    def cost(q):
        return np.sum((fk(q) - target) ** 2)
    x0 = seed if seed is not None else np.zeros(5)
    res = minimize(cost, x0, bounds=list(zip(J_MIN, J_MAX)))
    return res.x if res.fun < 1e-4 else None

def to_servo(q):
    return [(q[i] - J_MIN[i]) / (J_MAX[i] - J_MIN[i]) * 180 for i in range(5)]

def move_joints(angles, dur=1500):
    for i, a in enumerate(angles):
        Arm.Arm_serial_servo_write(i + 1, int(a), dur)
        time.sleep(0.02)
    time.sleep(dur / 1000)

_last_q = np.zeros(5)

def move_to_xyz(x, y, z, fixed_j5=90, dur=1500):
    global _last_q
    q = ik(np.array([x, y, z]), seed=_last_q)
    if q is None:
        print(f"IK failed for ({x:.3f},{y:.3f},{z:.3f})")
        return False
    _last_q = q
    angles = to_servo(q)
    angles[4] = fixed_j5
    move_joints(angles, dur)
    return True


# In[5]:


# ==========================================
# 3. MOTION & GESTURE ROUTINES
# ==========================================
def home():
    print("Home")
    Arm.Arm_serial_servo_write6_array(HOME_POSE, 1000)
    time.sleep(1.0)

def open_gripper():
    print("Open Gripper")
    Arm.Arm_serial_servo_write(6, 60, 500)
    time.sleep(0.6)

def close_gripper():
    print("Close Gripper")
    Arm.Arm_serial_servo_write(6, 180, 500)
    time.sleep(0.8)


# In[6]:


# ==========================================
# 4. PICK & PLACE CONFIGURATION
# ==========================================
PICK_Z, LIFT_Z, PRE_GRASP_Z = 0.03, 0.08, 0.15

POINTS_XY = {
    "P1": (0.2228,  0.0353), "P2": (0.2239, -0.0275),
    "P3": (0.1712,  0.0364), "P4": (0.1724, -0.0304),
}
DROP_X, DROP_Y, DROP_Z = 0.20, -0.15, PICK_Z

COLOR_HSV_RANGES = {
    "Red":    [(np.array([0, 92, 140]),   np.array([8, 255, 255]))],
    "Green":  [(np.array([37, 129, 40]),  np.array([87, 208, 205]))],
    "Blue":   [(np.array([104, 181, 52]), np.array([131, 255, 122]))],
    "Yellow": [(np.array([14, 145, 211]), np.array([107, 255, 255]))],
}
ROI_POINTS = {
    "P1": [48, 79, 104, 104], "P2": [369, 71, 104, 104],
    "P3": [38, 323, 104, 104], "P4": [400, 310, 104, 104],
}

live_detections = {}
is_running = True
is_busy = False
mic_enabled = False

MORPH_KERNEL = np.ones((5, 5), np.uint8)
JPEG_PARAMS = [int(cv2.IMWRITE_JPEG_QUALITY), 65]

def run_task_threaded(fn):
    global is_busy
    def _wrapper():
        global is_busy
        is_busy = True
        try:
            fn()
        finally:
            is_busy = False
            gc.collect()
    threading.Thread(target=_wrapper, daemon=True).start()

def full_pick_and_place_task(x, y, point_name):
    try:
        status_label.value = f"Status: Moving above {point_name}..."
        open_gripper()
        move_to_xyz(x, y, PRE_GRASP_Z, dur=1600)

        status_label.value = f"Status: Descending to {point_name}..."
        move_to_xyz(x, y, PICK_Z, dur=1200)

        status_label.value = "Status: Closing gripper..."
        close_gripper()

        status_label.value = "Status: Lifting straight up..."
        move_to_xyz(x, y, LIFT_Z, dur=1000)

        status_label.value = "Status: Moving to drop position..."
        move_to_xyz(DROP_X, DROP_Y, PRE_GRASP_Z, dur=1800)
        move_to_xyz(DROP_X, DROP_Y, DROP_Z, dur=1200)

        status_label.value = "Status: Releasing block..."
        open_gripper()

        status_label.value = "Status: Returning home..."
        move_to_xyz(DROP_X, DROP_Y, PRE_GRASP_Z, dur=1000)
        home()

        status_label.value = f"Status: Complete! Picked from {point_name}."
    except Exception as e:
        status_label.value = f"Error during motion: {e}"

def handle_color_pick(target_color):
    if is_busy:
        status_label.value = "Status: Arm is executing a task..."
        return
    for point_name, info in live_detections.items():
        if info["color"] == target_color:
            x, y = POINTS_XY[point_name]
            status_label.value = f"Status: Found {target_color} at {point_name}! Starting..."
            run_task_threaded(lambda: full_pick_and_place_task(x, y, point_name))
            return
    status_label.value = f"Status: No {target_color} block detected!"


# In[7]:


# ==========================================
# 5. CAMERA INIT & UI SETUP
# ==========================================
cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_V4L2)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
cam_ready = cap.isOpened()

image_widget = widgets.Image(format="jpeg", width=640, height=480)
status_label = widgets.Label(value=f"Status: Ready (/dev/video{CAMERA_INDEX})" if cam_ready else "Status: Camera Offline")
heard_label = widgets.Label(value="Heard: -")

btn_home   = widgets.Button(description="Home",        button_style="success", icon="home", layout=widgets.Layout(width="100px"))
btn_red    = widgets.Button(description="Pick Red",    button_style="danger",  layout=widgets.Layout(width="110px"))
btn_green  = widgets.Button(description="Pick Green",  button_style="success", layout=widgets.Layout(width="110px"))
btn_blue   = widgets.Button(description="Pick Blue",   button_style="primary", layout=widgets.Layout(width="110px"))
btn_yellow = widgets.Button(description="Pick Yellow", button_style="warning", layout=widgets.Layout(width="110px"))
btn_mic    = widgets.Button(description="Mic: OFF",    button_style="danger",  icon="microphone-slash", layout=widgets.Layout(width="130px"))

btn_home.on_click(lambda b: run_task_threaded(home))
btn_red.on_click(lambda b: handle_color_pick("Red"))
btn_green.on_click(lambda b: handle_color_pick("Green"))
btn_blue.on_click(lambda b: handle_color_pick("Blue"))
btn_yellow.on_click(lambda b: handle_color_pick("Yellow"))


# In[8]:



# ==========================================
# 6. VOSK VOICE CONTROL ENGINE
# ==========================================
GRAMMAR = ["home", "open", "close", "reset", "exit",
           "red", "green", "blue", "yellow", "stop"]

vosk_model = Model(VOSK_MODEL_PATH)
audio_q = queue.Queue()
last_command = ""

def callback(indata, frames, time_info, status):
    if status:
        print("Audio stream warning:", status)
    if mic_enabled:
        audio_q.put(bytes(indata))

def execute_command(text):
    global last_command
    text = text.lower().strip()

    if not text or text == last_command:
        return

    last_command = text
    heard_label.value = f"Heard: {text}"
    print("🧠 Voice Heard:", text)

    if is_busy and text not in ("stop", "exit"):
        status_label.value = f"Voice: Busy - command '{text}' ignored."
        return

    if "home" in text or "stop" in text or "reset" in text:
        run_task_threaded(home)
    elif "open" in text:
        run_task_threaded(open_gripper)
    elif "close" in text:
        run_task_threaded(close_gripper)
    elif text in ("red", "green", "blue", "yellow"):
        handle_color_pick(text.capitalize())
    elif "exit" in text:
        print("Stopping Voice...")
        run_task_threaded(home)
        toggle_mic(None)

def resolve_mic_index(preferred_index):
    try:
        sd.query_devices(preferred_index, 'input')
        return preferred_index
    except Exception:
        for idx, dev in enumerate(sd.query_devices()):
            if dev.get('max_input_channels', 0) > 0:
                print(f"MIC_INDEX {preferred_index} invalid -- using device {idx}: {dev['name']}")
                return idx
        raise RuntimeError("No input audio devices found.")

def voice_listen_loop():
    global mic_enabled
    with audio_q.mutex:
        audio_q.queue.clear()

    try:
        active_mic = resolve_mic_index(MIC_INDEX)
        
        # Enforce strict 16000 Hz for Vosk model compatibility
        target_samplerate = 16000
        rec = KaldiRecognizer(vosk_model, target_samplerate, json.dumps(GRAMMAR))

        with sd.RawInputStream(
            device=active_mic,
            samplerate=target_samplerate,
            blocksize=4096,
            dtype='int16',
            channels=1,
            callback=callback
        ):
            print(f"Voice Listener running on Mic Index {active_mic} at 16000 Hz...")
            status_label.value = f"Voice: Active (Mic {active_mic})"
            
            while mic_enabled:
                try:
                    data = audio_q.get(timeout=0.5)
                except queue.Empty:
                    continue
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text = result.get("text", "")
                    if text:
                        execute_command(text)
                        
    except Exception as e:
        print("Voice Thread Error:", e)
        status_label.value = f"Voice Error: {e}"
        mic_enabled = False
        btn_mic.description, btn_mic.button_style, btn_mic.icon = "Mic: OFF", "danger", "microphone-slash"

def toggle_mic(b):
    global mic_enabled
    mic_enabled = not mic_enabled
    if mic_enabled:
        btn_mic.description, btn_mic.button_style, btn_mic.icon = "Mic: ON", "success", "microphone"
        status_label.value = "Voice: Listening..."
        threading.Thread(target=voice_listen_loop, daemon=True).start()
    else:
        btn_mic.description, btn_mic.button_style, btn_mic.icon = "Mic: OFF", "danger", "microphone-slash"
        status_label.value = "Voice: Stopped."

btn_mic.on_click(toggle_mic)

# Display Layout
ui = widgets.VBox([
    widgets.HBox([btn_home, btn_red, btn_green, btn_blue, btn_yellow, btn_mic]),
    status_label,
    heard_label,
    image_widget,
])
display(ui)


# In[9]:


# ==========================================
# 7. CAMERA FEED THREAD
# ==========================================
def scan_all_rois_live(frame_processed):
    global live_detections
    live_detections.clear()
    hsv = cv2.cvtColor(frame_processed, cv2.COLOR_BGR2HSV)

    for point_name, (x, y, w, h) in ROI_POINTS.items():
        x1, y1 = max(0, x), max(0, y)
        x2, y2 = min(640, x + w), min(480, y + h)
        roi_hsv = hsv[y1:y2, x1:x2]

        best_color, max_pixels = None, 0
        for color_name, ranges in COLOR_HSV_RANGES.items():
            color_count = 0
            for lower, upper in ranges:
                mask = cv2.inRange(roi_hsv, lower, upper)
                mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, MORPH_KERNEL)
                color_count += cv2.countNonZero(mask)
            if color_count > 150 and color_count > max_pixels:
                max_pixels, best_color = color_count, color_name

        if best_color:
            live_detections[point_name] = {"color": best_color, "pixels": max_pixels}

def camera_feed_thread():
    while is_running:
        if not cap.isOpened():
            time.sleep(0.2)
            continue

        ret, frame = cap.read()
        if not ret or frame is None:
            time.sleep(0.02)
            continue

        if is_busy:
            time.sleep(0.05)
            continue

        # frame_draw = np.ascontiguousarray(np.flip(frame, axis=(0, 1)))
        frame_draw = frame
        scan_all_rois_live(frame_draw)

        for name, (x, y, w, h) in ROI_POINTS.items():
            if name in live_detections:
                box_color = (0, 255, 255)
                label_text = f"{name}: {live_detections[name]['color']} ({live_detections[name]['pixels']}px)"
            else:
                box_color = (0, 255, 0)
                label_text = name
            cv2.rectangle(frame_draw, (x, y), (x + w, y + h), box_color, 2)
            cv2.putText(frame_draw, label_text, (x, max(y - 8, 15)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, box_color, 2)

        success, jpeg = cv2.imencode(".jpg", frame_draw, JPEG_PARAMS)
        if success:
            image_widget.value = jpeg.tobytes()

        time.sleep(0.05)

    cap.release()

threading.Thread(target=camera_feed_thread, daemon=True).start()


# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:




