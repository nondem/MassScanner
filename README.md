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
