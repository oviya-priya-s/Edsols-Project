#!/usr/bin/env python
# coding: utf-8

# # HSV calibration

# ### Import header file

# In[3]:


#!/usr/bin/env python
# coding: utf-8
import threading
import cv2 as cv
from time import sleep
from dofbot_config import *
import ipywidgets as widgets
from IPython.display import display


# ### Create an instance, initialize parameters

# In[4]:


# Create and update HSV instance
update_hsv = update_hsv()
# Initialize the num parameter
num=0
# Initialization mode
model = "General"
# Initialize HSV name
HSV_name=None
# Initialize HSV value
color_hsv  = {"red"   : ((0, 43, 46), (10, 255, 255)),
              "green" : ((35, 43, 46), (77, 255, 255)),
              "blue"  : ((100, 43, 46), (124, 255, 255)),
              "yellow": ((26, 43, 46), (34, 255, 255))}
# Set random colors
color = [[random.randint(0, 255) for _ in range(3)] for _ in range(255)]
# HSV parameter path
HSV_path="HSV_config.txt"
# Read HSV configuration file, update HSV value
try: read_HSV(HSV_path,color_hsv)
except Exception: print("Read HSV_config Error!!!")


# In[5]:


import Arm_Lib
Arm = Arm_Lib.Arm_Device()
joints_0 = [90, 125, 0, 0, 90, 30]
Arm.Arm_serial_servo_write6_array(joints_0, 1000)


# ### Initialize the DFOBOT position

# ### Create widgets

# In[6]:


# Create layout
button_layout      = widgets.Layout(width='260px', height='40px', align_self='center')
# Output part
output = widgets.Output()
# Enter color update mode
HSV_update_red     = widgets.Button(description='HSV_update_red',    button_style='success', layout=button_layout)
HSV_update_green   = widgets.Button(description='HSV_update_green',  button_style='success', layout=button_layout)
HSV_update_blue    = widgets.Button(description='HSV_update_blue',   button_style='success', layout=button_layout)
HSV_update_yellow  = widgets.Button(description='HSV_update_yellow', button_style='success', layout=button_layout)
HSV_write_file     = widgets.Button(description='HSV_write_file',    button_style='primary', layout=button_layout)
Color_Binary       = widgets.Button(description='Color/Binary',      button_style='info',    layout=button_layout)
# Adjust the slider
H_min_slider       = widgets.IntSlider(description='H_min :', value=0, min=0, max=255, step=1, orientation='horizontal')
S_min_slider       = widgets.IntSlider(description='S_min :', value=43, min=0, max=255, step=1, orientation='horizontal')
V_min_slider       = widgets.IntSlider(description='V_min :', value=46, min=0, max=255, step=1, orientation='horizontal')
H_max_slider       = widgets.IntSlider(description='H_max :', value=10, min=0, max=255, step=1, orientation='horizontal')
S_max_slider       = widgets.IntSlider(description='S_max :', value=255, min=0, max=255, step=1, orientation='horizontal')
V_max_slider       = widgets.IntSlider(description='V_max :', value=255, min=0, max=255, step=1, orientation='horizontal')
# Exit button
exit_button = widgets.Button(description='Exit', button_style='danger', layout=button_layout)
# Image control
imgbox = widgets.Image(format='jpg', height=480, width=640, layout=widgets.Layout(align_self='center'))
# Debug button layout
HSV_slider = widgets.VBox(
    [H_min_slider, S_min_slider, V_min_slider, H_max_slider, S_max_slider, V_max_slider, HSV_update_red,
     HSV_update_green, HSV_update_blue, HSV_update_yellow, Color_Binary,HSV_write_file, exit_button],
    layout=widgets.Layout(align_self='center'))
# overall layout
controls_box = widgets.HBox([imgbox,HSV_slider], layout=widgets.Layout(align_self='center'))


# ### Color update callback

# In[7]:


def update_red_Callback(value):
    # Click the red button, call back function
    global HSV_name
    HSV_name = "red"
    H_min_slider.value=color_hsv[HSV_name][0][0]
    S_min_slider.value=color_hsv[HSV_name][0][1]
    V_min_slider.value=color_hsv[HSV_name][0][2]
    H_max_slider.value=color_hsv[HSV_name][1][0]
    S_max_slider.value=color_hsv[HSV_name][1][1]
    V_max_slider.value=color_hsv[HSV_name][1][2]
def update_green_Callback(value):
    # Click the green button to call back function
    global HSV_name
    HSV_name = "green"
    H_min_slider.value=color_hsv[HSV_name][0][0]
    S_min_slider.value=color_hsv[HSV_name][0][1]
    V_min_slider.value=color_hsv[HSV_name][0][2]
    H_max_slider.value=color_hsv[HSV_name][1][0]
    S_max_slider.value=color_hsv[HSV_name][1][1]
    V_max_slider.value=color_hsv[HSV_name][1][2]
def update_blue_Callback(value):
    # Click the blue button to call back function
    global HSV_name
    HSV_name = "blue"
    H_min_slider.value=color_hsv[HSV_name][0][0]
    S_min_slider.value=color_hsv[HSV_name][0][1]
    V_min_slider.value=color_hsv[HSV_name][0][2]
    H_max_slider.value=color_hsv[HSV_name][1][0]
    S_max_slider.value=color_hsv[HSV_name][1][1]
    V_max_slider.value=color_hsv[HSV_name][1][2]
def update_yellow_Callback(value):
    # Click the yellow button to call back function
    global HSV_name
    HSV_name = "yellow"
    H_min_slider.value=color_hsv[HSV_name][0][0]
    S_min_slider.value=color_hsv[HSV_name][0][1]
    V_min_slider.value=color_hsv[HSV_name][0][2]
    H_max_slider.value=color_hsv[HSV_name][1][0]
    S_max_slider.value=color_hsv[HSV_name][1][1]
    V_max_slider.value=color_hsv[HSV_name][1][2]
# Click the button
HSV_update_red.on_click(update_red_Callback)
HSV_update_green.on_click(update_green_Callback)
HSV_update_blue.on_click(update_blue_Callback)
HSV_update_yellow.on_click(update_yellow_Callback)


# ### Mode switch control

# In[8]:


# Mode setting
def write_file_Callback(value):
    global model
    model = 'Write_file'
def Color_Binary_Callback(value):
    global model,num
    if num%2==0: model="Binary"
    if num%2==1: model="General"
    num+=1
def exit_button_Callback(value):
    global model
    model = 'Exit'
    with output: print(model)
# Click the button
HSV_write_file.on_click(write_file_Callback)
Color_Binary.on_click(Color_Binary_Callback)
exit_button.on_click(exit_button_Callback)


# ### Camera function

# In[9]:


def camera():
    global HSV_name,model,color_hsv,num
    # Open camera
    capture = cv.VideoCapture(0)
    # Loop when the camera is normally opened
    while capture.isOpened():
        try:
            # Read every frame of the camera
            _, img = capture.read()
            # Uniform image size
            img = cv.resize(img, (640, 480))
            #print("HSVName: ", HSV_name)
            if HSV_name!=None:
                # Add text
                cv.putText(img, HSV_name, (int(img.shape[0] / 2)+40, 50), cv.FONT_HERSHEY_SIMPLEX, 2, color[random.randint(0, 254)], 2)
                # Modify the HSV value of the color in real time
                color_hsv[HSV_name] = ((H_min_slider.value, S_min_slider.value, V_min_slider.value), (H_max_slider.value, S_max_slider.value, V_max_slider.value))
                # Contour detection
                img, binary = update_hsv.get_contours(img, HSV_name, color_hsv[HSV_name],color_hsv)
                if model == "Binary":
                    # Binary graph display
                    _, img = update_hsv.get_contours(img, HSV_name, color_hsv[HSV_name],color_hsv)
                if model == 'Write_file':
                    # Write file
                    try: write_HSV(HSV_path,color_hsv)
                    except Exception: print("File Path Error!!!")
                    # Invert all colors
                    cv.bitwise_not(img, img)
                    num=0
                    model="General"
            if model == 'Exit':
                # Exit
                cv.destroyAllWindows()
                capture.release()
                break
            # Image format conversion
            imgbox.value = cv.imencode('.jpg', img)[1].tobytes()
        except KeyboardInterrupt:
            capture.release()


# ### Display

# In[10]:


# Display layout
display(controls_box,output)
# Start thread
threading.Thread(target=camera, ).start()


# In[40]:


# RED = (hMin = 4 , sMin = 43, vMin = 46), (hMax = 89 , sMax = 255, vMax = 255)
# GREEN = (hMin = 35 , sMin = 43, vMin = 46), (hMax = 77 , sMax = 255, vMax = 255)
# BLUE = (hMin = 100 , sMin = 43, vMin = 46), (hMax = 124 , sMax = 255, vMax = 255)
# YELLOW = (hMin = 23 , sMin = 43, vMin = 46), (hMax = 34 , sMax = 255, vMax = 255)


# In[ ]:




