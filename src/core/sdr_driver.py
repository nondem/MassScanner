"""
SDR Driver Module

This module provides a wrapper class for the pyrtlsdr.RtlSdr library to control
RTL-SDR USB devices. It includes error handling for USB connectivity issues and
supports multi-device configurations.
"""

from typing import Optional, TYPE_CHECKING
import numpy as np
import threading
from rtlsdr import RtlSdr

if TYPE_CHECKING:
    from rtlsdr import RtlSdr as RtlSdrType


class SdrDriver:
    """
    Wrapper class for RTL-SDR hardware control.
    
    This class encapsulates all hardware interactions with RTL-SDR devices,
    providing error handling and a clean interface for the scanning application.
    Designed to support multi-SDR configurations through device_index parameter.
    """
    
    def __init__(self, device_index: int = 0) -> None:
        """
        Initialize the SDR driver.
        
        Args:
            device_index: USB device index for multi-SDR support (default: 0)
        """
        self.device_index: int = device_index
        self.sdr: Optional["RtlSdr"] = None
        self.is_connected: bool = False
        self.ppm_error: int = 0  # Frequency correction in PPM
        self._device_lock: threading.Lock = threading.Lock()  # Thread-safe device access
    
    def connect(self) -> bool:
        """
        Connect to the RTL-SDR device.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.sdr = RtlSdr(device_index=self.device_index)
            # Apply PPM correction if set
            if self.ppm_error != 0:
                self.sdr.freq_correction = self.ppm_error
                print(f"Applied PPM correction: {self.ppm_error}")
            self.is_connected = True
            return True
        except Exception as e:
            print(f"Failed to connect to SDR device {self.device_index}: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self) -> None:
        """
        Disconnect from the RTL-SDR device and release resources.
        """
        try:
            if self.sdr is not None:
                self.sdr.close()
                self.is_connected = False
        except Exception as e:
            print(f"Error disconnecting SDR device {self.device_index}: {e}")
        finally:
            self.sdr = None
            self.is_connected = False
    
    def tune(self, freq_hz: float) -> bool:
        """
        Tune the SDR to a specific frequency.
        
        Args:
            freq_hz: Target frequency in Hz
            
        Returns:
            True if tuning successful, False otherwise
        """
        if not self.is_connected or self.sdr is None:
            print("Cannot tune: SDR not connected")
            return False
        
        with self._device_lock:
            try:
                self.sdr.center_freq = freq_hz
                return True
            except Exception as e:
                print(f"Failed to tune to {freq_hz} Hz: {e}")
                return False
    
    def set_gain(self, gain: float) -> bool:
        """
        Set the RF gain.
        
        Args:
            gain: Gain value in dB (use 'auto' mode if gain=0)
            
        Returns:
            True if gain setting successful, False otherwise
        """
        if not self.is_connected or self.sdr is None:
            print("Cannot set gain: SDR not connected")
            return False
        
        with self._device_lock:
            try:
                if gain == 0:
                    # Enable automatic gain control
                    self.sdr.gain = 'auto'
                else:
                    self.sdr.gain = gain
                return True
            except Exception as e:
                print(f"Failed to set gain to {gain} dB: {e}")
                return False
    
    def read_samples(self, num_samples: int) -> Optional[np.ndarray]:
        """
        Read IQ samples from the SDR.
        
        Args:
            num_samples: Number of samples to read
            
        Returns:
            NumPy array of complex IQ samples, or None if read fails
        """
        if not self.is_connected or self.sdr is None:
            print("Cannot read samples: SDR not connected")
            return None
        
        with self._device_lock:
            try:
                samples = self.sdr.read_samples(num_samples)
                return samples
            except Exception as e:
                print(f"Failed to read {num_samples} samples: {e}")
                return None
    
    def set_sample_rate(self, rate_hz: float) -> bool:
        """
        Set the sample rate.
        
        Args:
            rate_hz: Sample rate in Hz
            
        Returns:
            True if setting successful, False otherwise
        """
        if not self.is_connected or self.sdr is None:
            print("Cannot set sample rate: SDR not connected")
            return False
        
        with self._device_lock:
            try:
                self.sdr.sample_rate = rate_hz
                return True
            except Exception as e:
                print(f"Failed to set sample rate to {rate_hz} Hz: {e}")
                return False
    
    def get_center_freq(self) -> Optional[float]:
        """
        Get the current center frequency.
        
        Returns:
            Current center frequency in Hz, or None if unavailable
        """
        if not self.is_connected or self.sdr is None:
            return None
        
        try:
            return self.sdr.center_freq
        except Exception as e:
            print(f"Failed to get center frequency: {e}")
            return None
    
    def get_sample_rate(self) -> Optional[float]:
        """
        Get the current sample rate.
        
        Returns:
            Current sample rate in Hz, or None if unavailable
        """
        if not self.is_connected or self.sdr is None:
            return None
        
        try:
            return self.sdr.sample_rate
        except Exception as e:
            print(f"Failed to get sample rate: {e}")
            return None
    
    def set_ppm_correction(self, ppm: int) -> bool:
        """
        Set the frequency correction in PPM (Parts Per Million).
        
        Args:
            ppm: PPM correction value (typically -100 to +100)
            
        Returns:
            True if setting successful, False otherwise
        """
        self.ppm_error = ppm
        
        if not self.is_connected or self.sdr is None:
            print(f"PPM correction set to {ppm} (will apply on next connect)")
            return True
        
        with self._device_lock:
            try:
                self.sdr.freq_correction = ppm
                print(f"PPM correction applied: {ppm}")
                return True
            except Exception as e:
                print(f"Failed to set PPM correction to {ppm}: {e}")
                return False
    
    def get_ppm_correction(self) -> int:
        """
        Get the current PPM correction value.
        
        Returns:
            Current PPM correction
        """
        if self.is_connected and self.sdr is not None:
            try:
                return self.sdr.freq_correction
            except:
                return self.ppm_error
        return self.ppm_error
