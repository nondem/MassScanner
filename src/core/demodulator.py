import numpy as np
import scipy.signal

class FMDemodulator:
    """
    FM Demodulator class.
    
    Handles the conversion of raw IQ samples (complex) into audio samples (float).
    Includes filtering, downsampling (decimation), and squelch logic.
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
        squelch_threshold_db: float = -80.0
    ) -> np.ndarray:
        """
        Perform FM demodulation on raw IQ samples.
        
        Args:
            samples: Complex numpy array of IQ data
            sample_rate: Current SDR sample rate (if different from init)
            squelch_threshold_db: Power threshold in dB. Signals below this are silenced.
            
        Returns:
            Numpy array of float32 audio samples
        """
        if len(samples) == 0:
            return np.array([], dtype=np.float32)
            
        # 1. Squelch Check (Power Calculation)
        # Calculate average power of the chunk in dB
        # We add 1e-10 to avoid log(0)
        power_db = 10 * np.log10(np.mean(np.abs(samples)**2) + 1e-10)
        
        # DEBUG: Print noise floor every ~10th chunk
        if np.random.random() < 0.1:
            print(f"DEBUG: Noise: {power_db:.2f} dB | Limit: {squelch_threshold_db:.2f} dB")

        # If signal is too weak, return silence immediately
        if power_db < squelch_threshold_db:
            # Calculate how many audio samples we WOULDA had
            current_rate = sample_rate if sample_rate else self.sample_rate
            decimation = int(current_rate / self.audio_rate)
            num_output_samples = len(samples) // decimation
            # Return silence (zeros)
            return np.zeros(num_output_samples, dtype=np.float32)

        # 2. FM Demodulation
        # Calculate phase difference between consecutive samples
        # angle( s[n] * conj(s[n-1]) )
        x = samples[1:] * np.conj(samples[:-1])
        demodulated = np.angle(x)
        
        # 3. Decimation (Downsampling) and Filtering
        # Use current sample rate if provided (Manual Mode uses 960k, Scan uses 2.048M)
        if sample_rate:
            decimation = int(sample_rate / self.audio_rate)
        else:
            decimation = self.decimation
            
        # scipy.signal.decimate applies a low-pass filter (anti-aliasing) 
        # and then throws away samples to reach the target rate.
        # This is heavy math, but yields better audio than simple slicing.
        audio = scipy.signal.decimate(demodulated, decimation, ftype='fir')
        
        # 4. Volume and Formatting
        # Scale the audio (FM angle output is roughly -pi to pi)
        audio = audio * (self.volume * 0.5)
        
        # Ensure correct type for sounddevice
        return audio.astype(np.float32)