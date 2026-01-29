import numpy as np
import scipy.signal

class FMDemodulator:
    """
    Multi-mode Demodulator class.
    
    Handles the conversion of raw IQ samples (complex) into audio samples (float).
    Supports NFM, WFM, and AM demodulation with filtering, downsampling (decimation), and squelch logic.
    """
    
    def __init__(self, sample_rate: float = 2.048e6, audio_rate: int = 48000) -> None:
        """
        Initialize the demodulator.
        
        Args:
            sample_rate: Input sample rate from SDR (default 2.048 MHz)
            audio_rate: Target audio output rate (default 48 kHz)
        """
        self.sample_rate = sample_rate
        self.audio_rate = audio_rate
        self.volume = 1.0  # Default volume (0.0 to 1.0)
        
        # Calculate initial decimation factor (can be overridden in demodulate)
        self.decimation = int(sample_rate / audio_rate)
    
    def set_volume(self, volume: float) -> None:
        """
        Set the output volume gain.
        
        Args:
            volume: Float between 0.0 and 1.0
        """
        self.volume = max(0.0, min(1.0, volume))

    def demodulate(
        self, 
        samples: np.ndarray, 
        sample_rate: float = None, 
        squelch_threshold_db: float = -80.0,
        mode: str = "NFM"
    ) -> np.ndarray:
        """
        Perform demodulation on raw IQ samples (FM or AM).
        
        Args:
            samples: Complex numpy array of IQ data
            sample_rate: Current SDR sample rate (if different from init)
            squelch_threshold_db: Power threshold in dB. Signals below this are silenced.
            mode: Demodulation mode ("NFM", "WFM", or "AM")
            
        Returns:
            Numpy array of float32 audio samples
        """
        if len(samples) == 0:
            return np.array([], dtype=np.float32)
        
        # Dispatch to appropriate demodulation method
        if mode == "AM":
            return self._demodulate_am(samples, sample_rate, squelch_threshold_db)
        elif mode == "WFM":
            return self._demodulate_wfm(samples, sample_rate, squelch_threshold_db)
        else:  # NFM (default)
            return self._demodulate_nfm(samples, sample_rate, squelch_threshold_db)
    
    def _demodulate_nfm(self, samples: np.ndarray, sample_rate: float, squelch_threshold_db: float) -> np.ndarray:
        """Narrow FM demodulation (standard FM radio)."""
        if len(samples) == 0:
            return np.array([], dtype=np.float32)
            
        # 1. Squelch Check (Power Calculation)
        power_db = 10 * np.log10(np.mean(np.abs(samples)**2) + 1e-10)
        
        if np.random.random() < 0.1:
            print(f"DEBUG: Noise: {power_db:.2f} dB | Limit: {squelch_threshold_db:.2f} dB")

        if power_db < squelch_threshold_db:
            current_rate = sample_rate if sample_rate else self.sample_rate
            decimation = int(current_rate / self.audio_rate)
            num_output_samples = len(samples) // decimation
            return np.zeros(num_output_samples, dtype=np.float32)

        # 2. FM Demodulation
        x = samples[1:] * np.conj(samples[:-1])
        demodulated = np.angle(x)
        
        # 3. Decimation
        if sample_rate:
            decimation = int(sample_rate / self.audio_rate)
        else:
            decimation = self.decimation
            
        audio = scipy.signal.decimate(demodulated, decimation, ftype='fir')
        
        # 4. Volume
        audio = audio * (self.volume * 0.5)
        
        return audio.astype(np.float32)
    
    def _demodulate_wfm(self, samples: np.ndarray, sample_rate: float, squelch_threshold_db: float) -> np.ndarray:
        """Wide FM demodulation (broadcast FM, wider bandwidth)."""
        if len(samples) == 0:
            return np.array([], dtype=np.float32)
        
        # 1. Squelch Check
        power_db = 10 * np.log10(np.mean(np.abs(samples)**2) + 1e-10)
        if power_db < squelch_threshold_db:
            current_rate = sample_rate if sample_rate else self.sample_rate
            decimation = int(current_rate / self.audio_rate)
            num_output_samples = len(samples) // decimation
            return np.zeros(num_output_samples, dtype=np.float32)
        
        # 2. FM Demodulation
        x = samples[1:] * np.conj(samples[:-1])
        demodulated = np.angle(x)
        
        # 3. Decimation with wider passband filter
        if sample_rate:
            decimation = int(sample_rate / self.audio_rate)
        else:
            decimation = self.decimation
        
        audio = scipy.signal.decimate(demodulated, decimation, ftype='iir')
        
        # 4. De-emphasis filter for WFM
        b, a = scipy.signal.butter(1, 100, btype='high', fs=self.audio_rate)
        audio = scipy.signal.lfilter(b, a, audio)
        
        audio = audio * (self.volume * 0.5)
        return audio.astype(np.float32)
    
    def _demodulate_am(self, samples: np.ndarray, sample_rate: float, squelch_threshold_db: float) -> np.ndarray:
        """Amplitude Modulation (AM) demodulation."""
        if len(samples) == 0:
            return np.array([], dtype=np.float32)
        
        # 1. Squelch Check
        power_db = 10 * np.log10(np.mean(np.abs(samples)**2) + 1e-10)
        if power_db < squelch_threshold_db:
            current_rate = sample_rate if sample_rate else self.sample_rate
            decimation = int(current_rate / self.audio_rate)
            num_output_samples = len(samples) // decimation
            return np.zeros(num_output_samples, dtype=np.float32)
        
        # 2. AM Demodulation: envelope detection
        demodulated = np.abs(samples)
        
        # 3. Remove DC component
        demodulated = demodulated - np.mean(demodulated)
        
        # 4. Decimation
        if sample_rate:
            decimation = int(sample_rate / self.audio_rate)
        else:
            decimation = self.decimation
        
        audio = scipy.signal.decimate(demodulated, decimation, ftype='fir')
        
        # 5. Apply low-pass filter for AM audio
        b, a = scipy.signal.butter(1, 5000, btype='low', fs=self.audio_rate)
        audio = scipy.signal.lfilter(b, a, audio)
        
        audio = audio * (self.volume * 0.3)
        return audio.astype(np.float32)