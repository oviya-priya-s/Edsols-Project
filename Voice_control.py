#!/usr/bin/env python
# coding: utf-8

# In[1]:


import sounddevice as sd

print(sd.query_devices())


# In[2]:


#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import sounddevice as sd
import queue
import json
import time

from vosk import Model, KaldiRecognizer
import Arm_Lib


# In[ ]:


Arm = Arm_Lib.Arm_Device()

HOME = [90,135,0,0,90,10]

Arm.Arm_serial_servo_write6_array(HOME,1000)


# In[4]:


def home():
    print("Home")
    Arm.Arm_serial_servo_write6_array(HOME,1000)


def open_gripper():
    print("Open Gripper")
    Arm.Arm_serial_servo_write(6,60,500)


def close_gripper():
    print("Close Gripper")
    Arm.Arm_serial_servo_write(6,180,500)


# In[5]:


def wave():

    print("Wave")

    pose1=[90,90,45,45,90,10]
    pose2=[90,90,45,45,130,10]
    pose3=[90,90,45,45,50,10]

    Arm.Arm_serial_servo_write6_array(pose1,800)

    for i in range(3):

        Arm.Arm_serial_servo_write6_array(pose2,500)
        time.sleep(0.6)

        Arm.Arm_serial_servo_write6_array(pose3,500)
        time.sleep(0.6)

    home()


# In[6]:


def dance():
    print("Dancing...")

    Arm.Arm_serial_servo_write6(90, 90, 90, 90, 90, 90, 500)
    time.sleep(1)

    # Up
    Arm.Arm_serial_servo_write(2, 60, 500)
    Arm.Arm_serial_servo_write(3, 120, 500)
    Arm.Arm_serial_servo_write(4, 60, 500)
    time.sleep(0.5)

    Arm.Arm_serial_servo_write(2, 45, 500)
    Arm.Arm_serial_servo_write(3, 135, 500)
    Arm.Arm_serial_servo_write(4, 45, 500)
    time.sleep(0.5)

    Arm.Arm_serial_servo_write(2, 60, 500)
    Arm.Arm_serial_servo_write(3, 120, 500)
    Arm.Arm_serial_servo_write(4, 60, 500)
    time.sleep(0.5)

    Arm.Arm_serial_servo_write(2, 90, 500)
    Arm.Arm_serial_servo_write(3, 90, 500)
    Arm.Arm_serial_servo_write(4, 90, 500)
    time.sleep(0.5)

    # Down
    Arm.Arm_serial_servo_write(2, 100, 500)
    Arm.Arm_serial_servo_write(3, 80, 500)
    Arm.Arm_serial_servo_write(4, 80, 500)
    time.sleep(0.5)

    Arm.Arm_serial_servo_write(2, 120, 500)
    Arm.Arm_serial_servo_write(3, 60, 500)
    Arm.Arm_serial_servo_write(4, 60, 500)
    time.sleep(0.5)

    Arm.Arm_serial_servo_write(2, 135, 500)
    Arm.Arm_serial_servo_write(3, 45, 500)
    Arm.Arm_serial_servo_write(4, 45, 500)
    time.sleep(0.5)

    Arm.Arm_serial_servo_write(2, 90, 500)
    Arm.Arm_serial_servo_write(3, 90, 500)
    Arm.Arm_serial_servo_write(4, 90, 500)
    time.sleep(0.5)

    # Wrist dance
    for _ in range(2):
        Arm.Arm_serial_servo_write(4, 20, 500)
        Arm.Arm_serial_servo_write(6, 150, 500)
        time.sleep(0.5)

        Arm.Arm_serial_servo_write(4, 90, 500)
        Arm.Arm_serial_servo_write(6, 90, 500)
        time.sleep(0.5)

    # Side pose
    Arm.Arm_serial_servo_write(1, 0, 500)
    Arm.Arm_serial_servo_write(5, 0, 500)
    time.sleep(0.5)

    # Final spin
    Arm.Arm_serial_servo_write(3, 180, 500)
    Arm.Arm_serial_servo_write(4, 0, 500)
    time.sleep(0.5)

    Arm.Arm_serial_servo_write(6, 180, 500)
    time.sleep(0.5)

    Arm.Arm_serial_servo_write(6, 0, 1000)
    time.sleep(0.5)

    # Return home
    Arm.Arm_serial_servo_write6(90,135,0,0,90,10,1000)
    time.sleep(1)

    print("Dance complete!")


# In[7]:


def left_right():

    print("Left Right")

    for i in range(2):

        Arm.Arm_serial_servo_write(1,50,400)
        time.sleep(0.5)

        Arm.Arm_serial_servo_write(1,130,400)
        time.sleep(0.5)

    home()


# In[8]:


# Voice Setup
model = Model("vosk-model-small-en-us-0.15")

q = queue.Queue()

def callback(indata, frames, time, status):
    q.put(bytes(indata))

mic_index = 3
device_info = sd.query_devices(mic_index, 'input')
samplerate = int(device_info['default_samplerate'])

rec = KaldiRecognizer(
    model,
    samplerate,
    '["home", "open", "wave", "close", "dance", "left right", "reset", "exit" ]'
)


# In[9]:


running = True

last_command = ""

def execute_command(text):

    global running
    global last_command

    text = text.lower().strip()

    if text == last_command:
        return

    last_command = text

    print("Command :", text)

    if "home" in text:
        home()

    elif "open" in text:
        open_gripper()

    elif "close" in text:
        close_gripper()

    elif "wave" in text:
        wave()

    elif "dance" in text:
        dance()

    elif "left right" in text:
        left_right()

    elif "stop" in text:
        home()

    elif "exit" in text:
        print("Stopping...")
        home()
        running = False

    else:
        print("Unknown command")


# In[ ]:


with sd.RawInputStream(
    device=mic_index,
    samplerate=samplerate,
    blocksize=4096,
    dtype='int16',
    channels=1,
    callback=callback):
    print("----------------------------------")
    print("Voice Control Started")
    print("----------------------------------")
    print("Commands:")
    print("home")
    print("open")
    print("close")
    print("wave")
    print("dance")
    print("left right")
    print("stop")
    print("exit")
    print("----------------------------------")

    while running:
        data = q.get()

        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            text = result.get("text", "")

            if text:
                print("🧠 Heard:", text)
                execute_command(text)

print("Listener stopped")
home()

del Arm


# In[ ]:





# In[ ]:




