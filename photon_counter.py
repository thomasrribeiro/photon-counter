#!/usr/bin/env python3
"""
Real-time photon counting monitor for FLIR BFS-U3-04S2M-C camera.

This script captures frames from the camera and converts pixel values to photon
counts using EMVA 1288 calibrated parameters. Results are displayed in real-time
using PyQtGraph.

Usage:
    python photon_counter.py

Controls:
    - Press Ctrl+C to exit and cleanup the camera
    - Close the plot window to exit
    - The first 50 frames are used for dark baseline calibration

Author: Thomas Ribeiro
"""

import sys
import signal
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from camera import initialize_camera, cleanup_camera
from visualization import setup_plot, update_plot, limit_plot_history, create_timer
from acquisition import create_acquisition_state, process_frame


# ============================================================================
# Configuration Parameters
# ============================================================================

EXPOSURE_US = 5000  # Exposure time in microseconds
ROI_SIZE = (200, 200)  # ROI dimensions (width, height)
BASELINE_FRAMES = 50  # Number of frames to average for dark baseline
PLOT_HISTORY = 500  # Number of frames to display in plot


# ============================================================================
# Main Application
# ============================================================================

def main():
    """Main application entry point."""

    # Initialize camera
    try:
        system, cam_list, cam = initialize_camera(exposure_us=EXPOSURE_US)
    except RuntimeError as e:
        print(f"Error: {e}")
        return 1

    # Setup visualization
    plot_dict = setup_plot(
        title="Photon Count Monitor - BFS-U3-04S2M-C",
        roi_size=ROI_SIZE,
        exposure_us=EXPOSURE_US
    )

    # Create acquisition state
    acq_state = create_acquisition_state(baseline_frames=BASELINE_FRAMES)

    # Data storage for plotting
    data_x = []
    data_y = []

    # Start acquisition
    cam.BeginAcquisition()
    is_acquiring = True
    print(f"Acquiring {BASELINE_FRAMES} frames for dark baseline calibration...")

    # Timer callback for frame acquisition and plot update
    def update():
        """Process one frame and update plot."""
        photons = process_frame(cam, acq_state, ROI_SIZE)

        # Update plot only after calibration is complete
        # Note: photons can be 0 if signal is darker than baseline (correct behavior)
        if photons is not None and acq_state['is_calibrated']:
            update_plot(plot_dict, data_x, data_y, acq_state['frame_idx'], photons)
            limit_plot_history(data_x, data_y, PLOT_HISTORY)

    # Setup timer for continuous acquisition
    timer = create_timer(callback=update, interval_ms=0)
    timer.start()

    # Cleanup handler
    def cleanup():
        """Cleanup camera resources on exit."""
        nonlocal is_acquiring
        timer.stop()
        cleanup_camera(system, cam_list, cam, is_acquiring=is_acquiring)
        is_acquiring = False

    # Register cleanup on window close
    plot_dict['win'].closeEvent = lambda event: (cleanup(), event.accept())

    # Setup signal handlers for Ctrl+C and Ctrl+Z
    def signal_handler(signum, frame):
        """Handle interrupt signals gracefully."""
        print(f"\nReceived signal {signum}. Shutting down gracefully...")
        cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTSTP, signal_handler)  # Ctrl+Z

    # Run application
    try:
        return_code = plot_dict['app'].exec()
        cleanup()  # Cleanup if window closed normally
        return return_code
    except Exception as e:
        print(f"\nError during execution: {e}")
        cleanup()
        return 1


if __name__ == "__main__":
    sys.exit(main())
