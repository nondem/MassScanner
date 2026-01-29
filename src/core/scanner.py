"""
Scanner Module

This module implements the main scanning thread that controls the SDR hardware,
performs frequency sweeps, detects signals, and reports events back to the UI.
"""

import threading
import time
from queue import Queue
from typing import List, Dict, Any, Optional
import numpy as np
from datetime import datetime

# Audio availability flag
AUDIO_AVAILABLE = False
try:
    import sounddevice as sd
    AUDIO_AVAILABLE = True
except ImportError:
    sd = None
    print("Warning: sounddevice not installed. Audio streaming disabled.")

from src.core.sdr_driver import SdrDriver
from src.core.demodulator import FMDemodulator


class Scanner(threading.Thread):
    """
    Main scanning thread for spectrum monitoring.
    
    This class manages the scanning loop that tunes through configured frequency
    bands, performs FFT analysis, detects signals above threshold, and sends
    detection events to the UI via a queue.
    """
    
    def __init__(
        self,
        driver: SdrDriver,
        result_queue: Queue,
        bands: List[Dict[str, Any]],
        raw_data_queue: Optional[Queue] = None
    ) -> None:
        """
        Initialize the scanner thread.
        
        Args:
            driver: SdrDriver instance for hardware control
            result_queue: Queue for sending detection events to UI
            bands: List of band configuration dictionaries from bands.json
            raw_data_queue: Optional queue for real-time spectrum data visualization
        """
        super().__init__(daemon=True)
        self.driver: SdrDriver = driver
        self.result_queue: Queue = result_queue
        self.bands: List[Dict[str, Any]] = bands
        self.raw_data_queue: Optional[Queue] = raw_data_queue
        
        # Pause/Resume control using threading.Event
        # When event is SET -> scanning active
        # When event is CLEAR -> scanning paused
        self.scan_paused: threading.Event = threading.Event()
        # Start in paused state
        self.scan_paused.clear()
        
        # Default scanning parameters
        self.num_samples: int = 2048  # Number of IQ samples per read
        self.sample_rate_hz: float = 2.4e6  # 2.4 MHz sample rate
        self.manual_sample_rate_hz: float = 1.92e6  # 1.92 MHz for manual mode (divisible for 48kHz)
        
        # Dynamic parameters (can be changed during scan)
        self._current_gain: float = 0.0  # 0 means auto
        self._current_threshold: float = 10.0  # Default threshold in dB
        self.squelch_value: float = -80.0  # Squelch threshold in dB (default: -80 dB)
        self._lock: threading.Lock = threading.Lock()  # Thread-safe parameter updates
        
        # Spectrum update throttling (to prevent UI lag)
        self._spectrum_counter: int = 0
        self._spectrum_update_interval: int = 4  # Send spectrum data every 4th iteration
        
        # Manual mode parameters (for audio streaming)
        self.manual_mode: bool = False
        self.manual_freq: float = 144.0e6  # Default: 2m amateur band
        self.buffer_size: int = 204800  # Default buffer size (200 * 1024, divisible by 20)
        
        # Initialize audio demodulator and stream
        self._init_audio_stream()
        
        # Start the thread immediately (in paused state)
        self.start()
    
    def _init_audio_stream(self) -> None:
        """
        Initialize audio demodulator and output stream.
        
        Sets up FM demodulation and creates an audio output stream for manual mode.
        """
        if not AUDIO_AVAILABLE:
            print("Audio streaming disabled (sounddevice not available)")
            self.audio_stream = None
            self.demodulator = None
            return
        
        try:
            # Initialize FM demodulator with manual mode sample rate
            # 1.92 MHz / 48 kHz = 40x decimation (clean integer ratio)
            self.demodulator: FMDemodulator = FMDemodulator(
                sample_rate=1.92e6,
                audio_rate=48000
            )
            
            # Initialize audio output stream
            if sd is not None:
                self.audio_stream = sd.OutputStream(
                    channels=1,
                    samplerate=48000,
                    blocksize=0,
                    latency='high',
                    dtype='float32'
                )
                self.audio_stream.start()
                print("Audio stream initialized with high latency mode")
            else:
                self.audio_stream = None
                print("Audio streaming disabled (sounddevice not available)")
        
        except Exception as e:
            print(f"Error initializing audio stream: {e}")
            self.audio_stream = None
            self.demodulator = None
    
    def run(self) -> None:
        """
        Main thread entry point - executes the scanning loop or manual mode.
        
        This method runs forever, checking the pause state. When not paused,
        it either operates in scan mode (band sweeping) or manual mode (single
        frequency audio streaming).
        """
        print("Scanner thread started (paused)")
        
        while True:
            # Check if scanning is paused
            if not self.scan_paused.is_set():
                # Paused state - sleep and continue
                time.sleep(0.1)
                continue
            
            # Check if in manual mode (audio streaming)
            if self.manual_mode:
                self._manual_mode_loop()
            else:
                self._scan_mode_loop()
    
    def _scan_mode_loop(self) -> None:
        """
        Scan mode: Iterate through bands and perform FFT detection.
        """
        # Initialize hardware on first active scan cycle
        if self.driver.is_connected and not hasattr(self, '_initialized'):
            if self.driver.set_sample_rate(self.sample_rate_hz):
                self._initialized = True
                print("Scanner initialized (scan mode)")
            else:
                print("Failed to set sample rate")
                time.sleep(1.0)
                return
        
        # Iterate through all configured bands
        for band in self.bands:
            # Check pause state during band iteration
            if not self.scan_paused.is_set():
                break
            
            # Check if switched to manual mode
            if self.manual_mode:
                break
            
            # Skip disabled bands
            if not band.get("enabled", False):
                continue
            
            # Scan the frequency band
            self._scan_band(band)
    
    def _manual_mode_loop(self) -> None:
        """
        Manual mode: Single frequency audio streaming via FM demodulation.
        """
        if not self.audio_stream or not self.demodulator:
            print("Audio stream or demodulator not available")
            self.manual_mode = False
            return
        
        # Tune to manual frequency
        if not self.driver.tune(self.manual_freq):
            print(f"Failed to tune to {self.manual_freq/1e6:.3f} MHz")
            return
        
        # Force sample rate to 960 kHz for clean 20x decimation to 48 kHz
        if not self.driver.set_sample_rate(960000):
            print("Failed to set manual mode sample rate")
            return
        
        print(f"Manual mode: streaming audio from {self.manual_freq/1e6:.3f} MHz at 960 kHz sample rate")
        
        while self.scan_paused.is_set() and self.manual_mode:
            try:
                # Read samples using dynamic buffer size (divisible by 20)
                samples = self.driver.read_samples(self.buffer_size)
                
                if samples is None:
                    time.sleep(0.01)
                    continue
                
                # Demodulate FM to audio (pass sample rate and squelch)
                audio_data = self.demodulator.demodulate(
                    samples, 
                    sample_rate=960000,
                    squelch_threshold_db=self.squelch_value
                )
                
                # Stream audio (non-blocking write)
                if len(audio_data) > 0:
                    self.audio_stream.write(audio_data)
            
            except Exception as e:
                print(f"Error in manual mode: {e}")
                time.sleep(0.1)
    
    def _scan_band(self, band: Dict[str, Any]) -> None:
        """
        Scan a single frequency band.
        
        Args:
            band: Band configuration dictionary
        """
        start_freq: float = band["start_freq_hz"]
        end_freq: float = band["end_freq_hz"]
        step_size: float = band["step_size_hz"]
        gain: float = band.get("gain", "auto")
        dwell_time_ms: float = band.get("dwell_time_ms", 250)
        threshold_db: float = band["threshold_db"]
        
        # Set gain for this band
        if isinstance(gain, str) and gain.lower() == "auto":
            self.driver.set_gain(0)  # 0 triggers auto gain
        else:
            self.driver.set_gain(float(gain))
        
        # Iterate through frequencies in the band
        current_freq: float = start_freq
        while current_freq <= end_freq and self.scan_paused.is_set():
            # Tune to frequency
            if not self.driver.tune(current_freq):
                print(f"Failed to tune to {current_freq} Hz")
                current_freq += step_size
                continue
            
            # Brief settling time after tuning
            time.sleep(dwell_time_ms / 1000.0)
            
            # Read samples
            samples: Optional[np.ndarray] = self.driver.read_samples(self.num_samples)
            if samples is None:
                print(f"Failed to read samples at {current_freq} Hz")
                current_freq += step_size
                continue
            
            # Perform signal analysis
            self._analyze_samples(samples, current_freq, threshold_db, band)
            
            # Move to next frequency
            current_freq += step_size
    
    def _analyze_samples(
        self,
        samples: np.ndarray,
        center_freq: float,
        threshold_db: float,
        band: Dict[str, Any]
    ) -> None:
        """
        Analyze IQ samples using FFT and detect signals above threshold.
        
        Args:
            samples: Complex IQ samples from the SDR
            center_freq: Center frequency of the samples
            threshold_db: Detection threshold in dB above noise floor
            band: Band configuration dictionary
        """
        try:
            # Perform FFT on the samples
            fft_result: np.ndarray = np.fft.fft(samples)
            
            # Shift zero frequency to center
            fft_shifted: np.ndarray = np.fft.fftshift(fft_result)
            
            # Calculate power spectrum in dB
            # Add small epsilon to avoid log(0)
            power_spectrum: np.ndarray = 10 * np.log10(
                np.abs(fft_shifted) ** 2 + 1e-10
            )
            
            # Send spectrum data for visualization (only if queue is empty to prevent lag)
            if self.raw_data_queue is not None and self.raw_data_queue.empty():
                # Calculate frequency bins for the spectrum
                freq_bin_width: float = self.sample_rate_hz / len(samples)
                frequencies: np.ndarray = center_freq + np.arange(
                    -len(samples) // 2, len(samples) // 2
                ) * freq_bin_width
                
                # Put spectrum data into queue (non-blocking)
                try:
                    self.raw_data_queue.put_nowait((frequencies, power_spectrum))
                except:
                    pass  # Queue full, skip this update
            
            # Calculate noise floor as median of power spectrum
            noise_floor: float = float(np.median(power_spectrum))
            
            # Find peak power
            peak_power: float = float(np.max(power_spectrum))
            peak_index: int = int(np.argmax(power_spectrum))
            
            # Check if peak exceeds threshold
            if peak_power > (noise_floor + threshold_db):
                # Calculate the actual frequency of the peak
                # FFT bins are spread across the sample rate
                freq_bin_width: float = self.sample_rate_hz / len(samples)
                offset_from_center: float = (peak_index - len(samples) // 2) * freq_bin_width
                peak_freq: float = center_freq + offset_from_center
                
                # Calculate relative power above noise floor
                relative_power: float = peak_power - noise_floor
                
                # Create detection event
                event: Dict[str, Any] = {
                    "timestamp": datetime.now().isoformat(),
                    "frequency_hz": peak_freq,
                    "center_freq_hz": center_freq,
                    "power_db": peak_power,
                    "noise_floor_db": noise_floor,
                    "relative_power_db": relative_power,
                    "band_id": band.get("id", "unknown"),
                    "band_name": band.get("name", "Unknown Band")
                }
                
                # Send event to UI via queue
                self.result_queue.put(event)
                
                print(f"Signal detected: {peak_freq/1e6:.4f} MHz, "
                      f"Power: {relative_power:.1f} dB above noise")
        
        except Exception as e:
            print(f"Error analyzing samples: {e}")
    
    def set_gain(self, gain: float) -> bool:
        """
        Set the RF gain dynamically during scan.
        
        Args:
            gain: Gain value in dB (0 for auto)
        
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            self._current_gain = gain
        
        # Apply immediately to hardware
        return self.driver.set_gain(gain)
    
    def set_threshold(self, threshold_db: float) -> None:
        """
        Set the detection threshold dynamically during scan.
        
        Args:
            threshold_db: Threshold in dB above noise floor
        """
        with self._lock:
            self._current_threshold = threshold_db
        
        print(f"Threshold updated to {threshold_db:.1f} dB")
    
    def set_squelch(self, value_db: float) -> None:
        """
        Set the squelch threshold directly in dB.
        
        Args:
            value_db: Threshold in dB (e.g., -110.0)
        """
        # FIX: Direct assignment. Range is -150 to -80 dB.
        with self._lock:
            self.squelch_value = float(value_db)
        
        print(f"Squelch updated to {self.squelch_value:.1f} dB")
    
    def set_buffer_size(self, size_int: int) -> None:
        """
        Set the buffer size for manual mode audio streaming.
        
        Ensures the size is divisible by the decimation factor (20).
        
        Args:
            size_int: Desired buffer size in samples
        """
        # Safety: Ensure buffer size is divisible by decimation factor (20)
        safe_size = size_int - (size_int % 20)
        
        with self._lock:
            self.buffer_size = safe_size
        
        print(f"Buffer size updated to {safe_size} samples (divisible by 20)")
    
    def get_current_gain(self) -> float:
        """
        Get the current gain setting.
        
        Returns:
            Current gain in dB
        """
        with self._lock:
            return self._current_gain
    
    def get_current_threshold(self) -> float:
        """
        Get the current threshold setting.
        
        Returns:
            Current threshold in dB
        """
        with self._lock:
            return self._current_threshold
    
    def set_manual_mode(self, frequency_hz: float) -> bool:
        """
        Enter manual mode for audio streaming at a specific frequency.
        
        Args:
            frequency_hz: Target frequency in Hz
        
        Returns:
            True if manual mode activated, False otherwise
        """
        with self._lock:
            self.manual_mode = True
            self.manual_freq = frequency_hz
        
        print(f"Manual mode enabled: {frequency_hz/1e6:.3f} MHz")
        return True
    
    def exit_manual_mode(self) -> None:
        """
        Exit manual mode and return to scan mode.
        """
        with self._lock:
            self.manual_mode = False
        
        print("Manual mode disabled")
    
    def is_manual_mode(self) -> bool:
        """
        Check if scanner is in manual mode.
        
        Returns:
            True if manual mode is active
        """
        with self._lock:
            return self.manual_mode
    
    @property
    def scanning(self):
        """
        Check if scanner is actively scanning (not paused).
        
        Returns:
            True if scanner is running (not paused)
        """
        return not self.scan_paused.is_set()
    
    def toggle_mode(self, is_manual: bool) -> None:
        """
        Toggle between scanner and manual radio mode.
        
        Args:
            is_manual: True for manual radio, False for scanner
        """
        if is_manual:
            self.set_manual_mode(self.manual_freq)
        else:
            self.exit_manual_mode()
    
    def set_manual_freq(self, frequency_hz: float) -> bool:
        """
        Set the manual mode frequency without changing mode state.
        
        Args:
            frequency_hz: Target frequency in Hz
        
        Returns:
            True if successful
        """
        with self._lock:
            self.manual_freq = frequency_hz
        
        print(f"Manual frequency set to {frequency_hz/1e6:.3f} MHz")
        return True
    
    def get_manual_freq(self) -> float:
        """
        Get the current manual mode frequency.
        
        Returns:
            Current manual frequency in Hz
        """
        with self._lock:
            return self.manual_freq
    
    def start_scan(self) -> bool:
        """
        Resume the scanning process.
        
        Returns:
            True if scan resumed successfully, False otherwise
        """
        if self.scan_paused.is_set():
            print("Scanner already active")
            return False
        
        if not self.driver.is_connected:
            print("Cannot start scan: SDR not connected")
            return False
        
        print("Resuming scanner...")
        self.scan_paused.set()  # Resume scanning
        return True
    
    def stop_scan(self) -> None:
        """
        Pause the scanning process.
        
        This method signals the scanning loop to pause without closing
        the SDR connection. Use shutdown() for complete cleanup.
        """
        if not self.scan_paused.is_set():
            print("Scanner not active")
            return
        
        print("Pausing scanner...")
        self.scan_paused.clear()  # Pause scanning
        time.sleep(0.2)  # Brief delay to allow current operation to complete
        print("Scanner paused")
    
    def shutdown(self) -> None:
        """
        Shutdown the scanner and cleanup resources.
        
        This method pauses scanning, closes the audio stream, and disconnects
        from the SDR hardware. Should be called when closing the application.
        """
        print("Shutting down scanner...")
        
        # Exit manual mode if active
        if self.manual_mode:
            self.exit_manual_mode()
        
        # Pause scanning first
        self.scan_paused.clear()
        time.sleep(0.3)  # Allow current operations to complete
        
        # Close audio stream
        if self.audio_stream is not None:
            try:
                self.audio_stream.stop()
                self.audio_stream.close()
                print("Audio stream closed")
            except Exception as e:
                print(f"Error closing audio stream: {e}")
        
        # Close driver connection
        if self.driver.is_connected:
            self.driver.disconnect()
        
        print("Scanner shutdown complete")
