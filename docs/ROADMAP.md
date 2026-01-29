# MassScanner Roadmap

**Current Focus:** Phase 1 - Persistence & Core Logging
**Status:** MVP (Manual Mode & Squelch Logic Fixed)

---

## 🚧 Phase 1: Persistence (The "Don't Forget" Update)
*Goal: Ensure user settings and detection data survive application restarts.*

- [ ] **Settings Manager**
    - [ ] Create `SettingsManager` class to handle `settings.json`.
    - [ ] Auto-save on exit / Auto-load on startup for:
        - [ ] Squelch Threshold (dB)
        - [ ] Gain Level
        - [ ] Buffer Size
        - [ ] Master Volume
        - [ ] Last used mode (Scanner vs Manual)
- [ ] **Database Integration**
    - [ ] Initialize SQLite database (`scanner_data.db`).
    - [ ] Hook up existing `SignalLogger` class to the Scanner loop.
    - [ ] Store detection events: Frequency, Timestamp, Signal Strength (dB), Band Name.
- [ ] **Data Export**
    - [ ] Add "Export Logs" button to the UI.
    - [ ] Implement CSV export functionality.

## 🛠️ Phase 2: Band Management (The "Power User" Update)
*Goal: Remove the need to manually edit JSON files.*

- [ ] **UI Band Editor**
    - [ ] Create a new "Bands" tab or Settings modal.
    - [ ] UI for CRUD operations (Create, Read, Update, Delete) on frequency bands.
- [ ] **Quick Toggles**
    - [ ] Add checkboxes to the Sidebar to Enable/Disable specific bands on the fly.
- [ ] **Hot Reload**
    - [ ] Ensure the Scanner refreshes the band list without requiring an app restart.

## 🎙️ Phase 3: The Recorder (The "Spy" Update)
*Goal: Capture interesting signals automatically.*

- [ ] **Triggered Recording**
    - [ ] Implement "Squelch Break" listener in Manual Mode.
    - [ ] Auto-record audio to `.wav` when signal > threshold.
- [ ] **Scanner Recording**
    - [ ] Option to record brief samples when a hit is detected during a scan.
- [ ] **Playback UI**
    - [ ] Add a "Play" button next to log entries that have associated audio.

## 📊 Phase 4: Visuals & Advanced (The "Pro" Update)
*Goal: Professional-grade visualization and hardware support.*

- [ ] **Waterfall Display**
    - [ ] Replace or augment the Line Plot with a scrolling Waterfall FFT (Spectrogram).
- [ ] **Multi-SDR Support**
    - [ ] Detect multiple plugged-in dongles.
    - [ ] "Dedicated Scanner" mode: Use one dongle to scan while the other holds a frequency.
- [ ] **Coherent Scanning**
    - [ ] Compare signals between antennas (Direction Finding foundations).

## 🧹 Technical Debt & Maintenance
- [ ] **Unit Tests:** Add tests for DSP logic (Squelch, Demodulation).
- [ ] **Documentation:** Create a user manual / Help tab.
- [ ] **Error Handling:** Improve recovery when USB device is unplugged.