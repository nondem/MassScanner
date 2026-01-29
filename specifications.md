# Application Specifications: SpectrumScanner

## 1. Overview
This application is a high-speed, unattended spectrum scanning tool. It uses USB-connected SDR (Software Defined Radio) devices to monitor multiple frequency bands. 

## 2. Core Workflow
1.  **Configuration:** Users define "Profiles" for frequency bands (e.g., "2m Amateur", "Airband").
    * Parameters per band: Start/End Freq, Step Size, Gain, Dwell Time, Threshold.
2.  **Scanning Loop:** * The app iterates through the enabled bands.
    * For each band: Tunes the SDR -> Measures Noise Floor -> Checks for signals above threshold.
3.  **Detection:** * If a signal is detected (Power > Noise Floor + Threshold), it is considered an "Event."
4.  **Logging:** * Events are logged with: Timestamp, Frequency, Bandwidth, Relative Power.
    * Focus is on data capture, not visualization.

## 3. Technical Constraints
-   **Hardware:** RTL-SDR (USB).
-   **Concurrency:** The scanning loop must NOT block the UI.
-   **Data Storage:** SQLite for event logs; Raw binary for signal samples.

## 4. Future Roadmap (Architecture must support these now)
-   **Multi-SDR Support:** The architecture must allow multiple USB devices to run in parallel threads (e.g., Device A scans Airband, Device B scans 2m).
-   **Coherent Scanning:** Ability to have two SDRs on the same frequency (using a splitter) to compare signal loss.
-   **Audio Capture:** Trigger audio recording (demodulation) if a signal meets specific criteria.
-   **Comparison Logic:** A mode to compare performance between direct sampling vs standard sampling.

## 5. UI Requirements
-   **Current:** Minimalist dashboard showing active frequency, signal strength, and last 5 detection events.
-   **Future:** Waterfall display and spectral density graphs.

## 6. Interactive Features (Phase 2)
-   **Settings Panel:** GUI controls (sliders/inputs) to adjust Gain, Squelch Threshold, and PPM Correction in real-time.
-   **Manual Mode:** User can pause scanning and tune to a specific frequency.
-   **Audio Output:** Real-time FM demodulation and audio playback when in Manual Mode.