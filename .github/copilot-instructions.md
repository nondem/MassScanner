# Project: SpectrumScanner

MassScanner is a dual-mode RTL-SDR desktop application combining automated spectrum scanning with manual FM radio listening. Current focus is **Manual Radio Mode** with real-time audio demodulation (NFM/WFM/AM).

## Architecture Overview

**Three-Layer Design:**
1. **Hardware Layer** (`src/core/sdr_driver.py`): RTL-SDR USB device wrapper with thread-safe access via `threading.Lock`
2. **Processing Layer** (`src/core/scanner.py`): Daemon thread handling tuning, FFT analysis, demodulation, and signal detection
3. **UI Layer** (`src/ui/main_window.py`): CustomTkinter main window with real-time controls and Matplotlib spectrum visualization

**Data Flow (Manual Mode):**
- User sets frequency via digit-by-digit entry → Scanner tunes SDR → Reads 960 kHz samples
- Demodulator processes samples (NFM/WFM/AM) → Decimates to 48 kHz audio → Applies squelch/volume
- Audio streams to sounddevice; spectrum data queued to UI for visualization

## Critical Rules

### 1. Thread Safety Architecture
- **Main Thread:** UI only (CustomTkinter widgets). Must call `self.after()` for background updates.
- **Scanner Thread:** All SDR operations, FFT, demodulation, data logging
- **Communication:** Always use `queue.Queue` for thread-to-thread messaging (see `MainWindow.__init__`: `self.result_queue`, `self.raw_queue`)
- **Shared State:** Protect with `threading.Lock` (e.g., `SdrDriver._device_lock`, `Scanner._lock`)
- **Never:** Call `widget.configure()`, `update()`, or any CTk method from scanner thread

### 2. Hardware Abstraction & Error Handling
- All RTL-SDR calls (tune, read_samples, gain, freq_correction) must be wrapped in try/except
- Handle USB disconnection gracefully with `SdrDriver.is_connected` flag
- Use `SdrDriver._device_lock` when accessing `self.sdr` object
- Example pattern from `sdr_driver.py`:
  ```python
  with self._device_lock:
      try:
          self.sdr.center_freq = freq_hz
      except Exception as e:
          print(f"Failed to tune: {e}")
          self.is_connected = False
  ```

### 3. Signal Processing Pipeline
- **Input:** Complex IQ samples (960 kHz from SDR) as `np.ndarray`
- **Demodulation:** `FMDemodulator.demodulate()` supports NFM/WFM/AM modes
- **Decimation:** Use `scipy.signal.decimate()` for sample rate reduction (960 kHz → 48 kHz)
- **Squelch Logic:** Power-based (`power_db = 10 * np.log10(np.mean(np.abs(samples)**2) + 1e-10)`)
- **Output:** Audio samples as `np.float32` to sounddevice

### 4. Configuration & Persistence
- **UI State** (`src/config/ui_state.json`): Saves frequency (MHz) and volume (%)
- **Band Definitions** (`src/config/bands.json`): JSON array of band objects with `id`, `name`, `start_freq_hz`, `end_freq_hz`, `enabled`
- **Settings** (`src/config/settings.json`): App defaults (squelch, gain, buffer size) - currently not loaded but prepared
- **Logging** (`src/data/logger.py`): SQLite database for signal detections via `SignalLogger` class

## Development Patterns

### Mode Switching (Scanner vs Manual)
- `Scanner.mode` property toggles behavior without stopping thread
- Manual mode uses `self.manual_sample_rate_hz = 1.92e6` (divisible for 48 kHz decimation)
- Scanner mode uses `self.sample_rate_hz = 2.4e6` with FFT analysis

### Real-Time Parameter Updates
- Sliders/controls update `Scanner` parameters via thread-safe methods (e.g., `set_threshold()`, `set_squelch()`)
- Use lock pattern: acquire → check/update → release

### Spectrum Visualization
- FFT computed every iteration, throttled with `_spectrum_counter` before queueing
- Matplotlib canvas embedded in CTk with `FigureCanvasTkAgg`
- Data passed as dict `{"frequencies": [], "power_db": []}` via queue

### Type Hints & Code Style
- Python 3.13+ required with full type hints: `def demodulate(self, samples: np.ndarray) -> np.ndarray:`
- Use CustomTkinter, not standard Tkinter
- Docstrings for all public methods with Args/Returns
- Import from `src.*` modules using relative paths (main.py adds src to sys.path)

## Key Files & Responsibilities

| File | Purpose | Key Classes |
|------|---------|------------|
| [main.py](main.py) | Application entry point | - |
| [src/core/sdr_driver.py](src/core/sdr_driver.py) | Hardware wrapper with locking | `SdrDriver` |
| [src/core/scanner.py](src/core/scanner.py) | Daemon thread (960 kHz I/O, FFT, demod) | `Scanner` (threading.Thread) |
| [src/core/demodulator.py](src/core/demodulator.py) | NFM/WFM/AM demodulation, filtering | `FMDemodulator` |
| [src/ui/main_window.py](src/ui/main_window.py) | CustomTkinter GUI, queue polling | `MainWindow` (ctk.CTk) |
| [src/data/logger.py](src/data/logger.py) | SQLite event logging | `SignalLogger` |

## Running & Testing

- **Start App:** `python main.py` (requires RTL-SDR dongle plugged in, WinUSB driver on Windows)
- **Check Imports:** `mcp_pylance_mcp_s_pylanceImports` to verify all dependencies
- **Syntax:** Files use Python 3.13+ syntax; validate with Pylance before commit