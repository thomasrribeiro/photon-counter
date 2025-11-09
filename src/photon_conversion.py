"""
Photon conversion utilities for FLIR BFS-U3-04S2M-C camera.

This module provides functions to convert camera ADU (Analog-to-Digital Units)
to photon counts using EMVA 1288 standard parameters for the BFS-U3-04S2M-C
camera with Sony IMX287 sensor.

EMVA 1288 Specifications (from official FLIR documentation):
- System Gain (K): 0.35 e⁻/ADU
- Quantum Efficiency (QE): 61.82% at 525 nm (monochrome)
- Saturation Capacity: 22,187 electrons
- Read Noise: 3.71 electrons

References:
- EMVA 1288 Standard: https://www.emva.org/standards-technology/emva-1288/
- FLIR BFS-U3-04S2 EMVA Data: https://softwareservices.flir.com/BFS-U3-04S2/latest/EMVA/EMVA.html
"""

import numpy as np
from typing import Union, Optional


# EMVA 1288 measured parameters for BFS-U3-04S2M-C
SYSTEM_GAIN = 0.35  # electrons per ADU
QE_AT_525NM = 0.6182  # Quantum efficiency at 525 nm (61.82%)
SATURATION_ELECTRONS = 22187  # Full well capacity
READ_NOISE_ELECTRONS = 3.71  # Temporal dark noise


def adu_to_photons(
    signal_adu: Union[float, np.ndarray],
    dark_adu: Union[float, np.ndarray] = 0.0,
    gain: float = SYSTEM_GAIN,
    quantum_efficiency: float = QE_AT_525NM,
) -> Union[float, np.ndarray]:
    """
    Convert camera ADU values to incident photon count.

    The conversion follows the EMVA 1288 standard:
    1. ADU → Electrons: multiply by system gain (e⁻/ADU)
    2. Electrons → Photons: divide by quantum efficiency

    Formula:
        photons = (signal_adu - dark_adu) × gain / QE

    Parameters
    ----------
    signal_adu : float or np.ndarray
        Signal level in ADU (Analog-to-Digital Units)
    dark_adu : float or np.ndarray, optional
        Dark frame baseline in ADU. Default is 0.0
    gain : float, optional
        System gain in electrons/ADU. Default is 0.35 e⁻/ADU (BFS-U3-04S2M-C)
    quantum_efficiency : float, optional
        Quantum efficiency (0-1 range). Default is 0.6182 at 525nm

    Returns
    -------
    float or np.ndarray
        Estimated incident photon count

    Examples
    --------
    >>> # Convert single pixel value
    >>> photons = adu_to_photons(signal_adu=1000, dark_adu=100)
    >>> print(f"Photons: {photons:.1f}")
    Photons: 509.3

    >>> # Convert numpy array (e.g., ROI)
    >>> import numpy as np
    >>> roi = np.array([[1000, 1020], [980, 1010]])
    >>> dark = 100
    >>> photons = adu_to_photons(roi, dark)
    >>> print(f"Mean photons/pixel: {photons.mean():.1f}")
    Mean photons/pixel: 504.6

    Notes
    -----
    - This assumes shot-noise-limited regime where signal >> read noise
    - For low light levels (< 10 photons/pixel), read noise becomes significant
    - The result represents photons incident on the sensor, not photons absorbed
    - Negative values are clipped to zero (cannot have negative photon counts)
    """
    # Subtract dark baseline
    delta_adu = signal_adu - dark_adu

    # Clip negative values to zero (cannot have negative photon counts)
    if isinstance(delta_adu, np.ndarray):
        delta_adu = np.maximum(delta_adu, 0)
    else:
        delta_adu = max(0, delta_adu)

    # Convert ADU → electrons → photons
    electrons = delta_adu * gain
    photons = electrons / quantum_efficiency

    return photons


def adu_to_electrons(
    signal_adu: Union[float, np.ndarray],
    dark_adu: Union[float, np.ndarray] = 0.0,
    gain: float = SYSTEM_GAIN,
) -> Union[float, np.ndarray]:
    """
    Convert camera ADU values to photoelectrons.

    Parameters
    ----------
    signal_adu : float or np.ndarray
        Signal level in ADU
    dark_adu : float or np.ndarray, optional
        Dark frame baseline in ADU. Default is 0.0
    gain : float, optional
        System gain in electrons/ADU. Default is 0.35 e⁻/ADU

    Returns
    -------
    float or np.ndarray
        Photoelectron count
    """
    delta_adu = signal_adu - dark_adu

    if isinstance(delta_adu, np.ndarray):
        delta_adu = np.maximum(delta_adu, 0)
    else:
        delta_adu = max(0, delta_adu)

    return delta_adu * gain


def electrons_to_photons(
    electrons: Union[float, np.ndarray],
    quantum_efficiency: float = QE_AT_525NM,
) -> Union[float, np.ndarray]:
    """
    Convert photoelectrons to incident photons.

    Parameters
    ----------
    electrons : float or np.ndarray
        Number of photoelectrons
    quantum_efficiency : float, optional
        Quantum efficiency (0-1 range). Default is 0.6182 at 525nm

    Returns
    -------
    float or np.ndarray
        Estimated incident photon count
    """
    return electrons / quantum_efficiency


def get_qe_at_wavelength(wavelength_nm: float) -> float:
    """
    Get quantum efficiency at a specific wavelength.

    Currently only provides the measured value at 525 nm. For other wavelengths,
    you would need to interpolate from the full QE curve in the sensor datasheet.

    Parameters
    ----------
    wavelength_nm : float
        Wavelength in nanometers

    Returns
    -------
    float
        Quantum efficiency (0-1 range)

    Notes
    -----
    For accurate multi-wavelength work, obtain the full QE curve from:
    - Sony IMX287 sensor datasheet
    - FLIR BFS-U3-04S2M-C technical documentation
    """
    # Simplified: only have measured value at 525nm
    # For production use, interpolate from full QE curve
    if abs(wavelength_nm - 525) < 50:  # Within ±50nm of measurement
        return QE_AT_525NM
    else:
        import warnings
        warnings.warn(
            f"QE requested at {wavelength_nm} nm, but only measured at 525 nm. "
            "Using 525nm value - this may be inaccurate. "
            "Consult sensor datasheet for full QE curve."
        )
        return QE_AT_525NM


def calculate_snr(
    signal_photons: Union[float, np.ndarray],
    quantum_efficiency: float = QE_AT_525NM,
    read_noise_electrons: float = READ_NOISE_ELECTRONS,
) -> Union[float, np.ndarray]:
    """
    Calculate signal-to-noise ratio for photon counting measurement.

    SNR calculation includes shot noise and read noise:
        SNR = signal_electrons / sqrt(signal_electrons + read_noise²)

    Parameters
    ----------
    signal_photons : float or np.ndarray
        Signal in photons
    quantum_efficiency : float, optional
        Quantum efficiency. Default is 0.6182
    read_noise_electrons : float, optional
        Read noise in electrons. Default is 3.71 e⁻

    Returns
    -------
    float or np.ndarray
        Signal-to-noise ratio
    """
    signal_electrons = signal_photons * quantum_efficiency
    noise_electrons = np.sqrt(signal_electrons + read_noise_electrons**2)

    # Avoid division by zero
    if isinstance(signal_electrons, np.ndarray):
        snr = np.zeros_like(signal_electrons, dtype=float)
        mask = noise_electrons > 0
        snr[mask] = signal_electrons[mask] / noise_electrons[mask]
    else:
        snr = signal_electrons / noise_electrons if noise_electrons > 0 else 0

    return snr
