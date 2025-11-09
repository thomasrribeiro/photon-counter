# %%
# Imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from utils import enable_autoreload
enable_autoreload()

import PySpin
import numpy as np
import matplotlib.pyplot as plt
import gc

# %%
# Initialize system and camera
system = PySpin.System.GetInstance()
cam_list = system.GetCameras()

num_cams = cam_list.GetSize()
if num_cams == 0:
    print("No cameras detected.")
    cam_list.Clear()
    system.ReleaseInstance()
else:
    cam = cam_list.GetByIndex(0)
    nodemap_tldevice = cam.GetTLDeviceNodeMap()
    device_model_name = PySpin.CStringPtr(nodemap_tldevice.GetNode('DeviceModelName'))
    if PySpin.IsAvailable(device_model_name) and PySpin.IsReadable(device_model_name):
        print(f"Camera detected: {device_model_name.GetValue()}")
    cam.Init()
    print("Camera initialized.")

# %%
# Acquire a single frame
cam.BeginAcquisition()
image = cam.GetNextImage()

if image.IsIncomplete():
    print("Image incomplete:", image.GetImageStatus())
else:
    width, height = image.GetWidth(), image.GetHeight()
    arr = image.GetNDArray()
    print(f"Image size: {width} x {height}")
    print(f"Mean pixel value: {arr.mean():.2f}")

image.Release()
cam.EndAcquisition()

# %%
# Display captured frame

plt.figure(figsize=(6,4))
plt.imshow(arr, cmap='gray')
plt.colorbar()
plt.title("Captured Frame")
plt.axis('off')
plt.show()

# %%
# Proper teardown and cleanup
cam.DeInit()
cam_list.Clear()
del cam
del cam_list
gc.collect()

system.ReleaseInstance()
del system
gc.collect()

print("System released cleanly.")
# %%