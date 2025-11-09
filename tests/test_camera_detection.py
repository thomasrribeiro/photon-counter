#%%
# Imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from utils import enable_autoreload
enable_autoreload()

import PySpin
#%%
# Check if cameras are detected

system = PySpin.System.GetInstance()
v = system.GetLibraryVersion()
print(f"Spinnaker: {v.major}.{v.minor}.{v.type}.{v.build}")
cams = system.GetCameras()
print("Cameras detected:", cams.GetSize())
cams.Clear()
system.ReleaseInstance()
# %%
