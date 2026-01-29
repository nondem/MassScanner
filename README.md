# MassScanner

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-Active-success)

**MassScanner** is a dual-mode desktop application for RTL-SDR dongles. It combines a wide-band frequency scanner with a manual FM radio receiver, allowing users to detect signals and immediately tune in to listen.

Built with **Python**, **CustomTkinter**, and **PyRTLSDR**, it features a modern dark-mode GUI, real-time spectrum visualization, and robust DSP audio processing.

## 🌟 Features

* **Dual Operating Modes:**
    * **Scanner Mode:** Automatically sweeps through user-defined frequency bands (configured in JSON) to detect and log signals above a set threshold.
    * **Manual Radio Mode:** Tunes to a specific frequency to demodulate and play live FM audio (Narrowband FM).
* **Advanced Audio Pipeline:**
    * Integer-ratio decimation for glitch-free audio.
    * **Dynamic Buffer Control:** Adjustable buffer size slider to balance between low-latency and audio stability on different PCs.
    * **DSP Squelch:** Power-based squelch logic (-100dB to 0dB) to mute static when no signal is present.
* **Modern Command Center:**
    * Real-time FFT Spectrum Plot (Matplotlib).
    * Scrollable sidebar controls for Gain, Threshold, Volume, and Squelch.
    * Detection logging with timestamps and signal strength (dB).

## 🛠️ Hardware Requirements

* **RTL-SDR Dongle:** Any generic RTL2832U-based USB dongle (e.g., RTL-SDR Blog V3/V4, Nooelec NESDR).
* **Antenna:** Appropriate antenna for the frequencies you wish to scan.

## 📦 Installation

### 1. Clone the Repository
```bash
git clone [https://github.com/YOUR_USERNAME/MassScanner.git](https://github.com/YOUR_USERNAME/MassScanner.git)
cd MassScanner
2. Set Up Virtual Environment (Recommended)
Bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
3. Install Dependencies
Bash
pip install -r requirements.txt
(Note: If you don't have a requirements.txt yet, create one with: customtkinter pyrtlsdr sounddevice numpy scipy matplotlib)

4. ⚠️ Driver Installation (Critical)
For Windows Users: To use the RTL-SDR with Python, you must replace the default Windows driver with WinUSB.

Plug in your RTL-SDR dongle.

Download Zadig.

Open Zadig and select Options > List All Devices.

Select "Bulk-In, Interface (Interface 0)" (or "RTL2838UHIDIR").

Ensure the target driver is WinUSB.

Click Replace Driver (or Install Driver).

Additionally: You may need the librtlsdr.dll in your system path or the project folder. (Usually installed automatically with pyrtlsdr, but if you get a "DLL not found" error, download the dll from osmocom and place it in the src folder).

For Linux Users: Ensure you have the development libraries installed:

Bash
sudo apt-get install librtlsdr-dev
🚀 Usage
Run the application from the root directory:

Bash
python main.py
Controls Guide
Mode Switch: Toggle between "Scanner" (automated sweeping) and "Manual Radio" (listening).

Tuning: Type a frequency (e.g., 162.550) and click Tune. Use the +25k / -25k buttons or your arrow keys/mouse wheel to fine-tune.

Squelch Slider:

Right (0 dB): High threshold (Silence).

Left (-100 dB): Low threshold (Static).

Tip: Move the slider right until the static just disappears.

Buffer Size: If audio stutters, increase the buffer size. If audio is delayed (laggy), decrease it.

⚙️ Configuration
Frequency bands for the scanner are defined in src/config/bands.json. You can add or modify bands as needed:

JSON
[
  {
    "id": "2m_band",
    "name": "2 Meter Amateur",
    "enabled": true,
    "start_freq_hz": 144000000,
    "end_freq_hz": 148000000,
    "step_size_hz": 25000,
    "threshold_db": 15
  }
]
🐛 Troubleshooting
"Error loading librtlsdr"

Ensure you ran Zadig (Windows) or installed librtlsdr-dev (Linux).

Ensure the dongle is plugged in securely.

Audio is "Clipping" or "Popping"

This is usually a buffer underrun. Increase the Buffer Size slider in the Settings panel until the audio is smooth.

Squelch isn't working / I hear constant static

The noise floor might be louder than your setting. Move the Squelch Slider closer to 0 dB (Right) until the static cuts out.

🤝 Contributing
Contributions are welcome! Please fork the repository and submit a Pull Request.

📄 License
This project is licensed under the MIT License - see the LICENSE file for details.
