# SpectrumScanner Project Context
**Date:** January 28, 2026
**Status:** Manual Mode & Squelch Logic **FIXED**.
**Frameworks:** Python, CustomTkinter, PyRTLSDR, SoundDevice, NumPy, SciPy.

## 1. Project Overview
We are building a desktop Spectrum Scanner application for RTL-SDR dongles. It has two modes:
1.  **Scanner Mode:** Sweeps through frequency bands (defined in JSON) to log signals.
2.  **Manual Radio Mode:** Tunes to a specific frequency and streams FM audio.

## 2. Recent Critical Fixes (Do Not Regress)
We spent significant time stabilizing the audio pipeline and controls. **Do not change these settings without understanding the math.**

### A. Audio Stability (The "Clipping" Fix)
* **Problem:** Audio was stuttering/clipping due to fractional decimation rates.
* **Solution:** We use **integer-divisible sample rates**.
    * **Sample Rate:** `960,000` Hz (or `1,920,000` Hz).
    * **Audio Rate:** `48,000` Hz.
    * **Decimation:** 960k / 48k = 20 (Perfect Integer).
* **Buffer Size:** We use a variable buffer (slider controlled), currently default around **204,800 samples**. This MUST remain divisible by the decimation factor (20).

### B. Squelch Logic (The "Double Math" Fix)
* **Problem:** The UI was mapping 0-100 to dB, and the Scanner was *also* trying to map it, resulting in thresholds like -150dB that never triggered.
* **Solution:** **Direct dB Assignment.**
    * **UI (`main_window.py`):** Slider outputs raw float dB values (Range: `-100` to `0`).
    * **Scanner (`scanner.py`):** `set_squelch` accepts the float and stores it. **No conversion math.**
    * **Demodulator (`demodulator.py`):** Calculates signal power. If `Power < Threshold`, returns `np.zeros` (Silence).

### C. UI Layout (The "Invisible Slider" Fix)
* **Problem:** Controls were overflowing off the screen.
* **Solution:**
    * Replaced the sidebar `CTkFrame` with **`CTkScrollableFrame`**.
    * Added `self.after(100, lambda: self._maximize())` to force the window to maximize on launch.

---

## 3. Code State Snapshots

### `src/core/demodulator.py` (Current)
*Contains active Debug Prints (Noise Floor vs Limit).*
```python
def demodulate(self, samples, sample_rate=None, squelch_threshold_db=-80.0):
    # 1. Power Calc
    power_db = 10 * np.log10(np.mean(np.abs(samples)**2) + 1e-10)

    # DEBUG: Active truth-teller print
    if np.random.random() < 0.1:
         print(f"DEBUG: Noise: {power_db:.2f} dB | Limit: {squelch_threshold_db:.2f} dB")

    # 2. Squelch Gate
    if power_db < squelch_threshold_db:
         return np.zeros(...) # Returns Silence
    
    # ... FM Demodulation Logic ...