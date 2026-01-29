# Project: SpectrumScanner
This is a high-speed, unattended spectrum scanning tool using Python, Tkinter, and PyRTLSDR.

## Architectural Rules
1. **Thread Safety:** The UI runs on the main thread. All SDR scanning, FFT processing, and data logging MUST run in a separate `threading.Thread` or `multiprocessing.Process`.
2. **Communication:** Use `queue.Queue` to pass signal events from the Scanner Thread to the UI. Never update UI widgets directly from the scanner thread.
3. **Hardware Handling:** All calls to `sdr.read_samples` or `sdr.center_freq` must be wrapped in `try/except` blocks to handle USB device disconnection gracefully.
4. **Math:** Use `numpy` for all signal processing (FFT, dB calculation). Do not use Python lists for sample data.

## Code Style
- Use Python 3.12+ type hinting (e.g., `def calculate_power(samples: np.ndarray) -> float:`).
- Prefer `customtkinter` over standard `tkinter` for UI components.