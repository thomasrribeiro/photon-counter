"""
Camera interface for FLIR BFS-U3-04S2M-C.

Provides functions for camera initialization, configuration,
and resource management using pure procedural programming.
"""

import PySpin
import gc
from typing import Tuple, Dict


def initialize_camera(
    exposure_us: int = 5000,
    camera_index: int = 0
) -> Tuple[PySpin.System, PySpin.CameraList, PySpin.Camera]:
    """
    Initialize camera and return system, cam_list, and cam objects.

    Parameters
    ----------
    exposure_us : int, optional
        Exposure time in microseconds. Default is 5000
    camera_index : int, optional
        Index of camera to use. Default is 0

    Returns
    -------
    tuple
        (system, cam_list, cam) PySpin objects

    Raises
    ------
    RuntimeError
        If no cameras detected

    Examples
    --------
    >>> system, cam_list, cam = initialize_camera(exposure_us=5000)
    >>> cam.BeginAcquisition()
    >>> # ... acquire frames ...
    >>> cleanup_camera(system, cam_list, cam, is_acquiring=True)
    """
    print("Initializing camera system...")
    system = PySpin.System.GetInstance()
    cam_list = system.GetCameras()

    num_cams = cam_list.GetSize()
    if num_cams == 0:
        cam_list.Clear()
        system.ReleaseInstance()
        raise RuntimeError("No cameras detected. Please check connection.")

    print(f"Found {num_cams} camera(s)")

    cam = cam_list.GetByIndex(camera_index)

    # Get camera model name using node map
    nodemap_tldevice = cam.GetTLDeviceNodeMap()
    device_model_name = PySpin.CStringPtr(nodemap_tldevice.GetNode('DeviceModelName'))
    if PySpin.IsAvailable(device_model_name) and PySpin.IsReadable(device_model_name):
        print(f"Camera detected: {device_model_name.GetValue()}")

    # Initialize camera
    cam.Init()

    # Configure exposure
    configure_exposure(cam, exposure_us)

    print("Camera initialized successfully")
    return system, cam_list, cam


def configure_exposure(cam: PySpin.Camera, exposure_us: int):
    """
    Configure camera exposure time.

    Parameters
    ----------
    cam : PySpin.Camera
        Camera instance
    exposure_us : int
        Exposure time in microseconds

    Examples
    --------
    >>> configure_exposure(cam, 10000)  # Set to 10ms
    """
    cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)
    cam.ExposureTime.SetValue(exposure_us)
    print(f"Exposure time set to {exposure_us} us")


def get_camera_info(cam: PySpin.Camera) -> Dict[str, str]:
    """
    Get camera information from device node map.

    Parameters
    ----------
    cam : PySpin.Camera
        Camera instance

    Returns
    -------
    dict
        Dictionary containing camera model, serial number, etc.

    Examples
    --------
    >>> info = get_camera_info(cam)
    >>> print(f"Model: {info['model']}")
    """
    nodemap = cam.GetTLDeviceNodeMap()
    info = {}

    # Get model name
    node = PySpin.CStringPtr(nodemap.GetNode('DeviceModelName'))
    if PySpin.IsAvailable(node) and PySpin.IsReadable(node):
        info['model'] = node.GetValue()

    # Get serial number
    node = PySpin.CStringPtr(nodemap.GetNode('DeviceSerialNumber'))
    if PySpin.IsAvailable(node) and PySpin.IsReadable(node):
        info['serial'] = node.GetValue()

    # Get vendor name
    node = PySpin.CStringPtr(nodemap.GetNode('DeviceVendorName'))
    if PySpin.IsAvailable(node) and PySpin.IsReadable(node):
        info['vendor'] = node.GetValue()

    return info


def cleanup_camera(
    system: PySpin.System,
    cam_list: PySpin.CameraList,
    cam: PySpin.Camera,
    is_acquiring: bool = False
):
    """
    Cleanup camera resources to avoid interface errors.

    This is critical to avoid -1004 interface errors. Must be called
    before program exit or when switching cameras.

    Parameters
    ----------
    system : PySpin.System
        Spinnaker system instance
    cam_list : PySpin.CameraList
        Camera list
    cam : PySpin.Camera
        Camera instance
    is_acquiring : bool, optional
        Whether camera is currently acquiring. Default is False

    Examples
    --------
    >>> cleanup_camera(system, cam_list, cam, is_acquiring=True)
    """
    print("\nCleaning up camera resources...")

    # End acquisition if active
    if is_acquiring:
        try:
            cam.EndAcquisition()
        except PySpin.SpinnakerException as e:
            print(f"Warning: Error ending acquisition: {e}")

    # Deinitialize camera
    try:
        cam.DeInit()
    except PySpin.SpinnakerException as e:
        print(f"Warning: Error during camera DeInit: {e}")

    # CRITICAL ORDER: Delete camera object BEFORE clearing camera list
    del cam
    gc.collect()

    # Now clear the camera list
    cam_list.Clear()
    del cam_list
    gc.collect()

    # Finally release system
    system.ReleaseInstance()
    del system
    gc.collect()

    print("Camera resources released cleanly")
