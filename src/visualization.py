"""
PyQtGraph visualization for real-time photon counting.

Provides functions for creating and updating plots using pure procedural programming.
"""

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets
from typing import Tuple, Dict, List


def setup_plot(
    title: str = "Photon Count Monitor",
    roi_size: Tuple[int, int] = (200, 200),
    exposure_us: int = 5000,
    window_size: Tuple[int, int] = (1000, 600)
) -> Dict:
    """
    Setup PyQtGraph visualization components.

    Parameters
    ----------
    title : str, optional
        Window title
    roi_size : tuple of int, optional
        ROI dimensions (width, height). Default is (200, 200)
    exposure_us : int, optional
        Exposure time in microseconds. Default is 5000
    window_size : tuple of int, optional
        Window size (width, height). Default is (1000, 600)

    Returns
    -------
    dict
        Dictionary containing: 'app', 'win', 'plot', 'curve', 'text'

    Examples
    --------
    >>> plot_dict = setup_plot(roi_size=(200, 200), exposure_us=5000)
    >>> app = plot_dict['app']
    >>> curve = plot_dict['curve']
    """
    # Create Qt application if needed
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])

    # Create window
    win = pg.GraphicsLayoutWidget(title=title)
    win.resize(*window_size)

    # Create plot
    roi_w, roi_h = roi_size
    plot_title = f"ROI: {roi_w}x{roi_h} px | Exposure: {exposure_us} us"
    plot = win.addPlot(
        title=plot_title,
        labels={'bottom': 'Frame Number', 'left': 'Photons / pixel / exposure'}
    )
    plot.showGrid(x=True, y=True, alpha=0.3)
    plot.setDownsampling(mode='peak')
    plot.setClipToView(True)

    # Create curve
    curve = plot.plot(pen=pg.mkPen(color='y', width=2))

    # Add text overlay
    text = pg.TextItem(anchor=(0, 1))
    plot.addItem(text)
    text.setPos(0, 0)

    # Show window
    win.show()

    return {
        'app': app,
        'win': win,
        'plot': plot,
        'curve': curve,
        'text': text
    }


def update_plot(
    plot_dict: Dict,
    data_x: List[int],
    data_y: List[float],
    frame_number: int,
    photon_count: float
):
    """
    Update plot with new data point.

    Parameters
    ----------
    plot_dict : dict
        Dictionary from setup_plot() containing plot components
    data_x : list
        List of x-axis values (frame numbers)
    data_y : list
        List of y-axis values (photon counts)
    frame_number : int
        Current frame number
    photon_count : float
        Current photon count

    Examples
    --------
    >>> data_x, data_y = [], []
    >>> update_plot(plot_dict, data_x, data_y, 100, 500.5)
    """
    curve = plot_dict['curve']
    text = plot_dict['text']
    app = plot_dict['app']

    # Add new data
    data_x.append(frame_number)
    data_y.append(photon_count)

    # Update curve
    if len(data_x) > 0:
        curve.setData(data_x, data_y)

        # Update text overlay
        mean_photons = np.mean(data_y)
        text.setText(
            f"Current: {photon_count:.1f} photons/px\n"
            f"Mean: {mean_photons:.1f} photons/px"
        )

        if len(data_y) > 1:
            text.setPos(data_x[0], max(data_y))

        # Force Qt to process events
        app.processEvents()


def limit_plot_history(data_x: List, data_y: List, max_points: int):
    """
    Limit plot data to maximum number of points.

    Modifies lists in-place.

    Parameters
    ----------
    data_x : list
        X-axis data
    data_y : list
        Y-axis data
    max_points : int
        Maximum number of points to keep

    Examples
    --------
    >>> limit_plot_history(data_x, data_y, 500)
    """
    while len(data_x) > max_points:
        data_x.pop(0)
        data_y.pop(0)


def clear_plot(plot_dict: Dict, data_x: List, data_y: List):
    """
    Clear all data from the plot.

    Parameters
    ----------
    plot_dict : dict
        Dictionary from setup_plot()
    data_x : list
        X-axis data to clear
    data_y : list
        Y-axis data to clear

    Examples
    --------
    >>> clear_plot(plot_dict, data_x, data_y)
    """
    curve = plot_dict['curve']
    text = plot_dict['text']

    data_x.clear()
    data_y.clear()
    curve.setData([], [])
    text.setText("")


def create_timer(callback, interval_ms: int = 0) -> QtCore.QTimer:
    """
    Create a Qt timer for continuous acquisition.

    Parameters
    ----------
    callback : callable
        Function to call on timer timeout
    interval_ms : int, optional
        Timer interval in milliseconds. Default is 0 (as fast as possible)

    Returns
    -------
    QtCore.QTimer
        Qt timer instance

    Examples
    --------
    >>> def update_frame():
    ...     print("Frame acquired")
    >>> timer = create_timer(update_frame, interval_ms=0)
    >>> timer.start()
    """
    timer = QtCore.QTimer()
    timer.timeout.connect(callback)
    return timer
