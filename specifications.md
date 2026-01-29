# Application Specifications: SpectrumScanner

## 1. Overview
This application is a high-speed spectrum scanning and radio tool. It uses USB-connected SDR (Software Defined Radio) devices to monitor frequency bands and provides real-time audio demodulation in Manual Radio mode.

## 2. Current Implementation (Manual Radio Mode)
The application is currently focused on **Manual Radio mode** with the following features:

### Core Features
- **Real-Time Radio Reception:** Tune to any frequency and listen to live audio demodulation
- **Multiple Demodulation Modes:** NFM (Narrow FM), WFM (Broadcast FM), AM (Amplitude Modulation)
- **Spectrum Analyzer:** Real-time FFT-based spectrum display showing frequency distribution
- **Persistent Settings:** Automatically saves and restores:
  - Last tuned frequency (in MHz)
  - Volume level (0-100%)
  - All settings persist across application restarts
- **Real-Time Settings Control:**
  - **Frequency Control:** Digit-by-digit frequency entry (MHz.kkk.kkk.kk format) with individual up/down arrows
  - **Volume:** 0-100% slider with real-time audio output
  - **Squelch:** Noise gate to suppress weak signals
  - **Gain:** RF gain control (0 = auto, 1-49 dB)
  - **Threshold:** Signal detection threshold for noise floor
  - **PPM Correction:** Frequency calibration (-100 to +100 ppm) for hardware accuracy
  - **Buffer Size:** Audio buffer control (default 48kHz)
  - **Spectrum Toggle:** Enable/disable real-time spectrum display

### Audio Processing Pipeline
- **Sample Rate:** 960 kHz at RTL-SDR, decimated to 48 kHz for audio output
- **Audio Output:** sounddevice library for real-time playback
- **DSP Filtering:**
  - **NFM:** Phase-based demodulation with FIR decimation filter
  - **WFM:** Broadcast FM with IIR decimation and de-emphasis filter (100Hz high-pass)
  - **AM:** Envelope detection with DC removal and 5kHz low-pass filter
- **Volume Scaling:** Configurable output level (0-100%)

### Spectrum Display
- **FFT-Based:** 960-point FFT for frequency analysis
- **Optimization:** 4x downsampling reduces CPU load
- **Update Throttle:** 10-iteration throttle prevents audio clipping
- **Bin Averaging:** 50% reduction for smoother visualization
- **Frequency Reference:** Relative to tuned frequency with 1 kHz resolution

## 3. User Interface
- **Minimal Compact Design:** Auto-sizing window that fits all controls
- **Manual Radio Mode:** Default operating mode
- **Sidebar Layout:**
  - Mode selector (Manual Radio / Scanner)
  - Demodulation mode selection (NFM/WFM/AM)
  - Digit-by-digit frequency display with up/down arrows
  - Settings panel with labeled sliders (Squelch, Gain, Threshold, Volume, Buffer, PPM)
  - Spectrum display toggle

## 4. Technical Architecture
- **Language:** Python 3.13+
- **Threading:** Scanner runs in daemon thread; all SDR operations thread-safe with `threading.Lock`
- **Hardware Abstraction:** `SdrDriver` class wraps pyrtlsdr with error handling for USB disconnection
- **Hardware:**
  - RTL-SDR USB devices
  - Thread-safe concurrent access to hardware
  - Automatic reconnection handling

### Key Classes
- **`MainWindow`:** Tkinter-based GUI with digit entry, settings sliders, and real-time display
- **`Scanner`:** Main scanning/demodulation engine with thread-safe mode switching
- **`SdrDriver`:** RTL-SDR hardware wrapper with locking and PPM correction
- **`Demodulator`:** Multi-method signal processing (NFM/WFM/AM) with filtering and squelch

## 5. Configuration Files
- **`src/config/ui_state.json`:** Persists frequency (MHz) and volume (%) across sessions
  ```json
  {
    "frequency_mhz": 146.520,
    "volume_percent": 50
  }
  ```
- **`src/config/bands.json`:** Band frequency definitions (used by Scanner mode)
- **`src/config/settings.json`:** Application-wide defaults

## 6. Future Roadmap
- **Scanner Mode Enhancements:**
  - Automatic band sweeping with signal detection logging
  - Event recording to database with timestamp, frequency, power
- **Multi-SDR Support:** 
  - Parallel operation of multiple USB devices in separate threads
  - Coherent comparison mode (two devices on same frequency)
- **Advanced Features:**
  - Waterfall spectrogram display
  - Audio recording on signal detection
  - Frequency database and signal identification
- **UI Improvements:**
  - Visual signal strength meter
  - Frequency bookmarks/presets
  - Advanced filtering options

## 7. Design Principles
- **Thread Safety:** All SDR hardware access protected by locks
- **Non-Blocking UI:** Scanning/demodulation runs in background thread
- **Error Resilience:** USB disconnection handled gracefully with automatic reconnection attempts
- **User Persistence:** All frequency and volume settings automatically saved and restored
- **Type Hints:** Full Python 3.13+ type annotations for code clarity