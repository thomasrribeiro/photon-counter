"""
Frame acquisition and photon counting logic.

Provides functions for acquiring frames from the camera,
performing baseline calibration, and converting to photon counts
using pure procedural programming.
"""

import numpy as np
import PySpin
from typing import Optional, Tuple, Dict, List
from photon_conversion import adu_to_photons, SYSTEM_GAIN, QE_AT_525NM


def acquire_frame(cam: PySpin.Camera, timeout_ms: int = 1000) -> Optional[np.ndarray]:
    """
    Acquire a single frame from the camera.

    NOTE: Returns a numpy array view. The PySpin image is released immediately
    to avoid memory buildup. Only the array data is kept temporarily.

    Parameters
    ----------
    cam : PySpin.Camera
        Camera instance
    timeout_ms : int, optional
        Image acquisition timeout in milliseconds. Default is 1000

    Returns
    -------
    np.ndarray or None
        Image array if successful, None if incomplete or timeout

    Examples
    --------
    >>> image = acquire_frame(cam, timeout_ms=1000)
    >>> if image is not None:
    ...     print(f"Image shape: {image.shape}")
    """
    try:
        img = cam.GetNextImage(timeout_ms)

        if img.IsIncomplete():
            print(f"Frame incomplete: {img.GetImageStatus()}")
            img.Release()
            return None

        # Get numpy array - this creates a copy, not a reference
        arr = img.GetNDArray().copy()
        # Release the PySpin image immediately to free camera buffer
        img.Release()
        return arr

    except PySpin.SpinnakerException as e:
        print(f"Spinnaker exception: {e}")
        return None


def extract_roi(image: np.ndarray, roi_size: Tuple[int, int]) -> np.ndarray:
    """
    Extract centered ROI from image.

    Parameters
    ----------
    image : np.ndarray
        Full frame image
    roi_size : tuple of int
        ROI dimensions (width, height)

    Returns
    -------
    np.ndarray
        ROI region

    Examples
    --------
    >>> roi = extract_roi(image, roi_size=(200, 200))
    >>> print(f"ROI shape: {roi.shape}")
    """
    h, w = image.shape
    roi_w, roi_h = roi_size

    # Calculate centered ROI coordinates
    x0 = w // 2 - roi_w // 2
    y0 = h // 2 - roi_h // 2

    # Extract ROI
    roi = image[y0:y0 + roi_h, x0:x0 + roi_w]
    return roi


def create_acquisition_state(
    baseline_frames: int = 50,
    gain: float = SYSTEM_GAIN,
    quantum_efficiency: float = QE_AT_525NM
) -> Dict:
    """
    Create a state dictionary for tracking acquisition progress.

    Parameters
    ----------
    baseline_frames : int, optional
        Number of frames for baseline calibration. Default is 50
    gain : float, optional
        System gain in e-/ADU. Default is 0.35
    quantum_efficiency : float, optional
        Quantum efficiency. Default is 0.6182

    Returns
    -------
    dict
        State dictionary with keys: 'frame_idx', 'baseline_vals', 'mean_dark',
        'is_calibrated', 'baseline_frames', 'gain', 'qe'

    Examples
    --------
    >>> state = create_acquisition_state(baseline_frames=50)
    >>> print(state['is_calibrated'])
    False
    """
    return {
        'frame_idx': 0,
        'baseline_vals': [],
        'mean_dark': 0.0,
        'is_calibrated': False,
        'baseline_frames': baseline_frames,
        'gain': gain,
        'qe': quantum_efficiency
    }


def process_frame(
    cam: PySpin.Camera,
    state: Dict,
    roi_size: Tuple[int, int],
    timeout_ms: int = 1000
) -> Optional[float]:
    """
    Acquire and process a single frame.

    Handles baseline calibration phase and photon conversion.

    Parameters
    ----------
    cam : PySpin.Camera
        Camera instance
    state : dict
        Acquisition state from create_acquisition_state()
    roi_size : tuple of int
        ROI dimensions (width, height)
    timeout_ms : int, optional
        Acquisition timeout in milliseconds. Default is 1000

    Returns
    -------
    float or None
        Photon count per pixel, or None if frame acquisition failed.
        Returns 0 during baseline calibration phase.

    Examples
    --------
    >>> state = create_acquisition_state()
    >>> photons = process_frame(cam, state, roi_size=(200, 200))
    """
    # Acquire frame
    image = acquire_frame(cam, timeout_ms)
    if image is None:
        state['frame_idx'] += 1
        return None

    # Extract ROI and calculate mean immediately
    roi = extract_roi(image, roi_size)
    mean_adu = float(roi.mean())

    # Delete full image to free memory immediately - we only need the mean
    del image, roi

    # Baseline calibration phase
    if not state['is_calibrated']:
        state['baseline_vals'].append(mean_adu)
        state['frame_idx'] += 1

        if len(state['baseline_vals']) >= state['baseline_frames']:
            complete_calibration(state)

        return 0  # Return 0 photons during calibration

    # Convert to photons
    photons = adu_to_photons(
        signal_adu=mean_adu,
        dark_adu=state['mean_dark'],
        gain=state['gain'],
        quantum_efficiency=state['qe']
    )

    state['frame_idx'] += 1

    # Debug output every 100 frames
    if state['frame_idx'] % 100 == 0:
        delta = mean_adu - state['mean_dark']
        print(f"Frame {state['frame_idx']}: {photons:.1f} photons/px | "
              f"ADU: {mean_adu:.1f} | Dark: {state['mean_dark']:.1f} | "
              f"Delta: {delta:.1f}")

    return photons


def complete_calibration(state: Dict):
    """
    Complete baseline calibration and print statistics.

    Modifies state dictionary in-place.

    Parameters
    ----------
    state : dict
        Acquisition state dictionary

    Examples
    --------
    >>> complete_calibration(state)
    """
    state['mean_dark'] = np.mean(state['baseline_vals'])
    dark_std = np.std(state['baseline_vals'])

    print(f"\nBaseline calibration complete!")
    print(f"Mean dark level: {state['mean_dark']:.2f} ADU")
    print(f"Dark noise (std): {dark_std:.2f} ADU")
    print(f"Dark noise (e-): {dark_std * state['gain']:.2f} electrons")
    print(f"\nNow acquiring signal frames...\n")

    state['is_calibrated'] = True


def reset_calibration(state: Dict):
    """
    Reset baseline calibration to start over.

    Modifies state dictionary in-place.

    Parameters
    ----------
    state : dict
        Acquisition state dictionary

    Examples
    --------
    >>> reset_calibration(state)
    """
    state['baseline_vals'].clear()
    state['mean_dark'] = 0.0
    state['is_calibrated'] = False
    state['frame_idx'] = 0
    print("Baseline calibration reset")


def get_calibration_progress(state: Dict) -> float:
    """
    Get baseline calibration progress.

    Parameters
    ----------
    state : dict
        Acquisition state dictionary

    Returns
    -------
    float
        Progress as fraction from 0 to 1

    Examples
    --------
    >>> progress = get_calibration_progress(state)
    >>> print(f"Calibration: {progress*100:.0f}%")
    """
    if state['is_calibrated']:
        return 1.0
    return len(state['baseline_vals']) / state['baseline_frames']


def calculate_roi_photons(
    image: np.ndarray,
    roi_size: Tuple[int, int],
    dark_adu: float = 0.0,
    gain: float = SYSTEM_GAIN,
    quantum_efficiency: float = QE_AT_525NM
) -> float:
    """
    Calculate photon count from centered ROI in image.

    Convenience function for one-off photon calculations.

    Parameters
    ----------
    image : np.ndarray
        Full frame image
    roi_size : tuple of int
        ROI dimensions (width, height)
    dark_adu : float, optional
        Dark baseline level in ADU. Default is 0.0
    gain : float, optional
        System gain in e-/ADU. Default is 0.35
    quantum_efficiency : float, optional
        Quantum efficiency. Default is 0.6182

    Returns
    -------
    float
        Mean photon count per pixel in ROI

    Examples
    --------
    >>> photons = calculate_roi_photons(image, (200, 200), dark_adu=100)
    >>> print(f"Photons: {photons:.1f}")
    """
    # Extract centered ROI
    roi = extract_roi(image, roi_size)

    # Calculate mean ADU
    mean_adu = float(roi.mean())

    # Convert to photons
    photons = adu_to_photons(
        signal_adu=mean_adu,
        dark_adu=dark_adu,
        gain=gain,
        quantum_efficiency=quantum_efficiency
    )

    return photons
