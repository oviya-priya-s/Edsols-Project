#!/usr/bin/env python
# coding: utf-8

# # Garbage sorting

# ### Import head file

# In[1]:


#!/usr/bin/env python
# coding: utf-8
import Arm_Lib
import cv2 as cv
from single_garbage_identify import single_garbage_identify
import threading
from time import sleep
import ipywidgets as widgets
from IPython.display import display


# ### Create an instance, initialize parameters

# In[ ]:


single_garbage = single_garbage_identify()

model = "General"


# ### Initialize the robot position

# In[ ]:


arm = Arm_Lib.Arm_Device()
joints_0 = [90, 90, 20, 15, 90, 30]
arm.Arm_serial_servo_write6_array(joints_0, 1000)


# ### Control widgets

# In[ ]:


button_layout      = widgets.Layout(width='320px', height='60px', align_self='center')
output = widgets.Output()

exit_button = widgets.Button(description='Exit', button_style='danger', layout=button_layout)
imgbox = widgets.Image(format='jpg', height=480, width=640, layout=widgets.Layout(align_self='center'))
controls_box = widgets.VBox([imgbox, exit_button], layout=widgets.Layout(align_self='center'))


# ### Exit widgets mode

# In[ ]:


def exit_button_Callback(value):
    global model
    model = 'Exit'
    with output: print(model)
exit_button.on_click(exit_button_Callback)


# ### Main process

# In[ ]:


import numpy as np
def change_brightness(img, alpha, beta):
   return cv.addWeighted(img, alpha, np.zeros(img.shape, img.dtype),0, beta)

def camera():
    capture = cv.VideoCapture(1)
    while capture.isOpened():
        try:
            _, img = capture.read()
            img = cv.resize(img, (640, 480))
            img = cv.flip(img, 1)
            
            img = change_brightness(img, 1.5, 0)
            img = single_garbage.single_garbage_run(img)
            if model == 'Exit':
                cv.destroyAllWindows()
                capture.release()
                break
            imgbox.value = cv.imencode('.jpg', img)[1].tobytes()
        except KeyboardInterrupt:capture.release()


# ### Start

# In[ ]:


display(controls_box,output)
threading.Thread(target=camera, ).start()


# In[ ]:




