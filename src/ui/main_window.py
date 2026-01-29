"""
Main Window Module

This module implements the main application GUI using customtkinter.
It displays detection events in real-time and provides controls for
scanning operations.
"""

import customtkinter as ctk
import json
import os
import time
from queue import Queue, Empty
from typing import List, Dict, Any, Optional
from datetime import datetime
import numpy as np

import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from src.core.sdr_driver import SdrDriver
from src.core.scanner import Scanner


class MainWindow(ctk.CTk):
    """
    Main application window using customtkinter.
    """
    
    def __init__(self) -> None:
        """
        Initialize the main application window.
        """
        super().__init__()
        
        # Configure window
        self.title("SpectrumScanner")
        self.geometry("1200x900") # Force a large default size
        
        # Force maximize after 100ms to ensure OS is ready
        self.after(100, lambda: self._maximize_window())
        
        # Initialize queues
        self.result_queue: Queue = Queue()
        self.raw_queue: Queue = Queue(maxsize=1) 
        
        # Load band configuration
        self.bands: List[Dict[str, Any]] = self._load_bands()
        
        # Initialize SDR driver
        self.driver: SdrDriver = SdrDriver(device_index=0)
        
        # Initialize scanner
        self.scanner: Scanner = Scanner(
            driver=self.driver,
            result_queue=self.result_queue,
            bands=self.bands,
            raw_data_queue=self.raw_queue
        )
        
        # Scanning state tracking
        self.is_scanning: bool = False
        self.max_log_entries: int = 100
        self.detection_count: int = 0
        
        # Create GUI components
        self._create_widgets()
        
        # Set up window close handler
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Start polling the queue
        self.poll_queue()
        
    def _maximize_window(self):
        """Try to maximize window, fail gracefully if not supported"""
        try:
            self.state("zoomed")
        except:
            pass

    def _load_bands(self) -> List[Dict[str, Any]]:
        """Load band configuration from bands.json."""
        bands_path: str = "src/config/bands.json"
        try:
            with open(bands_path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading bands: {e}")
            return []
    
    def _create_sidebar(self) -> None:
        """
        Create the command center sidebar using a SCROLLABLE frame.
        """
        # USE SCROLLABLE FRAME: This ensures controls are never cut off
        sidebar = ctk.CTkScrollableFrame(self, width=250, label_text="Command Center")
        sidebar.grid(row=0, column=0, rowspan=5, sticky="nsew", padx=(10, 0), pady=10)
        
        # --- Frame 1: Mode Control ---
        mode_frame = ctk.CTkFrame(sidebar)
        mode_frame.pack(fill="x", padx=5, pady=(0, 15))
        
        mode_label = ctk.CTkLabel(mode_frame, text="Mode", font=ctk.CTkFont(size=12, weight="bold"))
        mode_label.pack(pady=(5, 5))
        
        self.mode_button = ctk.CTkSegmentedButton(
            mode_frame,
            values=["Scanner", "Manual Radio"],
            command=self._on_mode_change
        )
        self.mode_button.set("Manual Radio")
        self.mode_button.pack(fill="x", padx=5, pady=(0, 10))
        
        # --- Demodulation Mode ---
        demod_frame = ctk.CTkFrame(sidebar)
        demod_frame.pack(fill="x", padx=5, pady=(0, 15))
        
        demod_label = ctk.CTkLabel(demod_frame, text="Demod Mode", font=ctk.CTkFont(size=12, weight="bold"))
        demod_label.pack(pady=(5, 5))
        
        self.demod_mode = ctk.StringVar(value="NFM")
        nfm_radio = ctk.CTkRadioButton(demod_frame, text="NFM (Narrow)", variable=self.demod_mode, 
                                       value="NFM", command=self._on_demod_mode_change)
        nfm_radio.pack(anchor="w", padx=10, pady=2)
        
        wfm_radio = ctk.CTkRadioButton(demod_frame, text="WFM (Broadcast)", variable=self.demod_mode, 
                                       value="WFM", command=self._on_demod_mode_change)
        wfm_radio.pack(anchor="w", padx=10, pady=2)
        
        am_radio = ctk.CTkRadioButton(demod_frame, text="AM", variable=self.demod_mode, 
                                      value="AM", command=self._on_demod_mode_change)
        am_radio.pack(anchor="w", padx=10, pady=2)
        
        # --- Frame 2: Manual Tuning ---
        tuning_frame = ctk.CTkFrame(sidebar)
        tuning_frame.pack(fill="x", padx=5, pady=(0, 15))
        
        tuning_label = ctk.CTkLabel(tuning_frame, text="Tuning", font=ctk.CTkFont(size=12, weight="bold"))
        tuning_label.pack(pady=(5, 5))
        
        freq_entry_label = ctk.CTkLabel(tuning_frame, text="Frequency (MHz)", font=ctk.CTkFont(size=10))
        freq_entry_label.pack(anchor="w", padx=5, pady=(0, 2))
        
        # Digit-by-digit frequency entry with up/down controls
        digit_container = ctk.CTkFrame(tuning_frame, fg_color="transparent")
        digit_container.pack(fill="x", padx=5, pady=(0, 8))
        
        self.freq_digits = []
        self.freq_labels = []
        digit_positions = [0, 1, 2, None, 3, 4, 5, None, 6, 7, 8, None, 9, 10, 11]  # None = dot separator
        
        for idx, pos in enumerate(digit_positions):
            if pos is None:
                # Add dot separator
                dot_label = ctk.CTkLabel(digit_container, text=".", font=ctk.CTkFont(size=16, weight="bold"), width=10)
                dot_label.grid(row=1, column=idx, padx=2)
            else:
                # Create digit column with up/down arrows
                digit_frame = ctk.CTkFrame(digit_container, fg_color="transparent")
                digit_frame.grid(row=0, column=idx, rowspan=3, padx=2)
                
                # Up arrow
                up_btn = ctk.CTkButton(digit_frame, text="▲", width=30, height=20, 
                                      command=lambda p=pos: self._increment_digit(p),
                                      font=ctk.CTkFont(size=10), state="disabled")
                up_btn.pack()
                
                # Digit display
                digit_label = ctk.CTkLabel(digit_frame, text="0", font=ctk.CTkFont(size=16, weight="bold"),
                                          width=30, height=30, fg_color="#2b2b2b", corner_radius=5)
                digit_label.pack(pady=2)
                
                # Down arrow
                down_btn = ctk.CTkButton(digit_frame, text="▼", width=30, height=20,
                                        command=lambda p=pos: self._decrement_digit(p),
                                        font=ctk.CTkFont(size=10), state="disabled")
                down_btn.pack()
                
                self.freq_digits.append(digit_label)
                self.freq_labels.append((up_btn, down_btn))
        
        # Initialize frequency display to 146.520.000.000
        self._set_frequency_display(146.520)
        
        stepper_frame = ctk.CTkFrame(tuning_frame, fg_color="transparent")
        stepper_frame.pack(fill="x", padx=5, pady=(0, 8))
        
        self.freq_down_button = ctk.CTkButton(stepper_frame, text="-25k", command=self._on_freq_down, width=80, state="disabled")
        self.freq_down_button.pack(side="left", padx=(0, 5))
        
        self.freq_up_button = ctk.CTkButton(stepper_frame, text="+25k", command=self._on_freq_up, width=80, state="disabled")
        self.freq_up_button.pack(side="left")
        
        self.tune_button = ctk.CTkButton(tuning_frame, text="Tune", command=self._on_tune_clicked, state="disabled", fg_color="#3498db")
        self.tune_button.pack(fill="x", padx=5, pady=(0, 10))
        
        # --- Frame 3: Settings ---
        settings_frame = ctk.CTkFrame(sidebar)
        settings_frame.pack(fill="both", expand=True, padx=5, pady=(0, 10))
        
        settings_label = ctk.CTkLabel(settings_frame, text="Settings", font=ctk.CTkFont(size=12, weight="bold"))
        settings_label.pack(pady=(5, 10))
        
        # Spectrum Display Toggle
        self.spectrum_enabled = ctk.BooleanVar(value=True)
        spectrum_check = ctk.CTkCheckBox(settings_frame, text="Spectrum Display", variable=self.spectrum_enabled,
                                         command=self._on_spectrum_toggle)
        spectrum_check.pack(anchor="w", padx=10, pady=(0, 10))
        
        # Squelch Level
        ctk.CTkLabel(settings_frame, text="Squelch Level", font=ctk.CTkFont(size=11, weight="bold")).pack(pady=(5, 0))
        self.squelch_value_label = ctk.CTkLabel(settings_frame, text="-40.0 dB", text_color="#3498db")
        self.squelch_value_label.pack(pady=(0, 2))
        self.squelch_slider = ctk.CTkSlider(settings_frame, from_=-100, to=0, number_of_steps=100, command=self._on_squelch_change)
        self.squelch_slider.set(-40)
        self.squelch_slider.pack(fill="x", padx=5, pady=(0, 10))
        
        # Gain
        ctk.CTkLabel(settings_frame, text="Gain (dB)", font=ctk.CTkFont(size=11, weight="bold")).pack(pady=(5, 0))
        self.gain_value_label = ctk.CTkLabel(settings_frame, text="Auto", text_color="#3498db")
        self.gain_value_label.pack(pady=(0, 2))
        self.gain_slider = ctk.CTkSlider(settings_frame, from_=0, to=50, number_of_steps=50, command=self._on_gain_change)
        self.gain_slider.set(0)
        self.gain_slider.pack(fill="x", padx=5, pady=(0, 10))
        
        # Threshold
        ctk.CTkLabel(settings_frame, text="Threshold (dB)", font=ctk.CTkFont(size=11, weight="bold")).pack(pady=(5, 0))
        self.threshold_value_label = ctk.CTkLabel(settings_frame, text="10.0 dB", text_color="#3498db")
        self.threshold_value_label.pack(pady=(0, 2))
        self.threshold_slider = ctk.CTkSlider(settings_frame, from_=0, to=30, number_of_steps=60, command=self._on_threshold_change)
        self.threshold_slider.set(10.0)
        self.threshold_slider.pack(fill="x", padx=5, pady=(0, 10))


        # Volume
        ctk.CTkLabel(settings_frame, text="Volume", font=ctk.CTkFont(size=11, weight="bold")).pack(pady=(5, 0))
        self.volume_value_label = ctk.CTkLabel(settings_frame, text="50%", text_color="#3498db")
        self.volume_value_label.pack(pady=(0, 2))
        self.volume_slider = ctk.CTkSlider(settings_frame, from_=0, to=100, number_of_steps=100, command=self._on_volume_change)
        self.volume_slider.set(50)
        self.volume_slider.pack(fill="x", padx=5, pady=(0, 10))
        
        # Buffer
        ctk.CTkLabel(settings_frame, text="Buffer Size", font=ctk.CTkFont(size=11, weight="bold")).pack(pady=(5, 0))
        self.buffer_value_label = ctk.CTkLabel(settings_frame, text="200k", text_color="#3498db")
        self.buffer_value_label.pack(pady=(0, 2))
        self.buffer_slider = ctk.CTkSlider(settings_frame, from_=50000, to=500000, number_of_steps=450, command=self._on_buffer_change)
        self.buffer_slider.set(204800)
        self.buffer_slider.pack(fill="x", padx=5, pady=(0, 10))
        
        # PPM Correction
        ctk.CTkLabel(settings_frame, text="PPM Correction", font=ctk.CTkFont(size=11, weight="bold")).pack(pady=(5, 0))
        self.ppm_value_label = ctk.CTkLabel(settings_frame, text="0 ppm", text_color="#3498db")
        self.ppm_value_label.pack(pady=(0, 2))
        self.ppm_slider = ctk.CTkSlider(settings_frame, from_=-100, to=100, number_of_steps=200, command=self._on_ppm_change)
        self.ppm_slider.set(0)
        self.ppm_slider.pack(fill="x", padx=5, pady=(0, 10))
    
    def _create_widgets(self) -> None:
        """Create and layout all GUI components."""
        # Configure grid
        self.grid_rowconfigure(2, weight=1)  # Spectrum plot
        self.grid_rowconfigure(3, weight=1)  # Log area
        self.grid_columnconfigure(0, weight=0)  # Sidebar
        self.grid_columnconfigure(1, weight=1)  # Main content
        
        # --- Settings Sidebar ---
        self._create_sidebar()
        
        # --- Header Frame ---
        header_frame = ctk.CTkFrame(self)
        header_frame.grid(row=0, column=1, sticky="ew", padx=10, pady=10)
        header_frame.grid_columnconfigure(1, weight=1)
        
        title_label = ctk.CTkLabel(header_frame, text="SpectrumScanner - RTL-SDR Monitor", font=ctk.CTkFont(size=16, weight="bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 10))
        
        # --- Control Frame ---
        control_frame = ctk.CTkFrame(self)
        control_frame.grid(row=1, column=1, sticky="ew", padx=10, pady=5)
        control_frame.grid_columnconfigure(2, weight=1)
        
        self.start_button = ctk.CTkButton(control_frame, text="Start", command=self._on_start_scan, fg_color="#2ecc71")
        self.start_button.grid(row=0, column=0, padx=5)
        
        self.stop_button = ctk.CTkButton(control_frame, text="Stop", command=self._on_stop_scan, fg_color="#e74c3c", state="disabled")
        self.stop_button.grid(row=0, column=1, padx=5)
        
        self.status_label = ctk.CTkLabel(control_frame, text="Status: Idle", font=ctk.CTkFont(size=12), text_color="#95a5a6")
        self.status_label.grid(row=0, column=2, padx=20, sticky="e")
        
        # --- Spectrum Plot Frame ---
        spectrum_frame = ctk.CTkFrame(self)
        spectrum_frame.grid(row=2, column=1, sticky="nsew", padx=10, pady=5)
        spectrum_frame.grid_rowconfigure(0, weight=1)
        spectrum_frame.grid_columnconfigure(0, weight=1)
        
        self.spectrum_fig = Figure(figsize=(8, 3), dpi=100)
        self.spectrum_ax = self.spectrum_fig.add_subplot(111)
        self.spectrum_ax.set_xlabel('Frequency (MHz)', fontsize=9)
        self.spectrum_ax.set_ylabel('Power (dB)', fontsize=9)
        self.spectrum_ax.set_title('Real-Time Spectrum', fontsize=10, weight='bold')
        self.spectrum_ax.grid(True, alpha=0.3)
        self.spectrum_ax.tick_params(labelsize=8)
        self.spectrum_line, = self.spectrum_ax.plot([], [], 'b-', linewidth=1)
        self.spectrum_ax.set_xlim(0, 1000)
        self.spectrum_ax.set_ylim(-80, 0)
        self.spectrum_fig.tight_layout()
        
        self.spectrum_canvas = FigureCanvasTkAgg(self.spectrum_fig, master=spectrum_frame)
        self.spectrum_canvas.draw()
        self.spectrum_canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        
        # --- Log Frame ---
        log_frame = ctk.CTkFrame(self)
        log_frame.grid(row=3, column=1, sticky="nsew", padx=10, pady=10)
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(log_frame, text="Detection Log", font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.log_textbox = ctk.CTkTextbox(log_frame, font=ctk.CTkFont(family="Courier", size=10), state="disabled")
        self.log_textbox.grid(row=1, column=0, sticky="nsew")
        
        # --- Info Frame ---
        info_frame = ctk.CTkFrame(self)
        info_frame.grid(row=4, column=1, sticky="ew", padx=10, pady=5)
        info_frame.grid_columnconfigure(0, weight=1)
        
        self.counter_label = ctk.CTkLabel(info_frame, text="Detections: 0", font=ctk.CTkFont(size=11), text_color="#3498db")
        self.counter_label.grid(row=0, column=0, sticky="w")
        
        enabled_bands = [b.get("name", "Unknown") for b in self.bands if b.get("enabled", False)]
        band_text = f"Enabled Bands: {', '.join(enabled_bands) if enabled_bands else 'None'}"
        self.band_label = ctk.CTkLabel(info_frame, text=band_text, font=ctk.CTkFont(size=10), text_color="#95a5a6")
        self.band_label.grid(row=1, column=0, sticky="w")
        
        # Initialize Manual Radio mode after all widgets are created
        self._on_mode_change("Manual Radio")
    
    def _set_frequency_display(self, freq_mhz: float) -> None:
        """Update the digit display with a frequency value."""
        # Format: xxx.xxx.xxx.xxx (12 digits total)
        # Example: 146.520 MHz = 146.520000000
        freq_str = f"{freq_mhz:012.6f}".replace(".", "")
        for i, digit_label in enumerate(self.freq_digits):
            digit_label.configure(text=freq_str[i] if i < len(freq_str) else "0")
    
    def _get_frequency_from_display(self) -> float:
        """Read the frequency from the digit display."""
        freq_str = "".join([label.cget("text") for label in self.freq_digits])
        # Insert decimal point after 3rd digit: xxx.xxxxxxxxx
        freq_with_decimal = freq_str[:3] + "." + freq_str[3:]
        return float(freq_with_decimal)
    
    def _increment_digit(self, position: int) -> None:
        """Increment a specific digit position."""
        current = int(self.freq_digits[position].cget("text"))
        new_value = (current + 1) % 10
        self.freq_digits[position].configure(text=str(new_value))
        self._apply_frequency_change()
    
    def _decrement_digit(self, position: int) -> None:
        """Decrement a specific digit position."""
        current = int(self.freq_digits[position].cget("text"))
        new_value = (current - 1) % 10
        self.freq_digits[position].configure(text=str(new_value))
        self._apply_frequency_change()
    
    def _apply_frequency_change(self) -> None:
        """Apply the frequency shown in the digit display."""
        try:
            freq_mhz = self._get_frequency_from_display()
            freq_hz = freq_mhz * 1e6
            self.scanner.set_manual_freq(freq_hz)
            
            # If scanner is running, immediately tune the hardware
            if self.is_scanning and self.driver.is_connected:
                self.driver.tune(freq_hz)
            
            print(f"Tuned to {freq_mhz:.6f} MHz")
        except Exception as e:
            print(f"Error applying frequency: {e}")
    
    def _on_gain_change(self, value: float) -> None:
        gain: float = float(value)
        if gain == 0:
            self.gain_value_label.configure(text="Auto")
        else:
            self.gain_value_label.configure(text=f"{gain:.1f} dB")
        self.scanner.set_gain(gain)
    
    def _on_threshold_change(self, value: float) -> None:
        threshold: float = float(value)
        self.threshold_value_label.configure(text=f"{threshold:.1f} dB")
        self.scanner.set_threshold(threshold)
    
    def _on_squelch_change(self, value: float) -> None:
        squelch_db = float(value)
        self.squelch_value_label.configure(text=f"{squelch_db:.1f} dB")
        if hasattr(self.scanner, 'set_squelch'):
             self.scanner.set_squelch(squelch_db)
    
    def _on_mode_change(self, mode: str) -> None:
        is_manual = (mode == "Manual Radio")
        self.scanner.toggle_mode(is_manual)
        state = "normal" if is_manual else "disabled"
        
        # Enable/disable digit controls
        for up_btn, down_btn in self.freq_labels:
            up_btn.configure(state=state)
            down_btn.configure(state=state)
        
        self.tune_button.configure(state=state)
        self.freq_down_button.configure(state=state)
        self.freq_up_button.configure(state=state)
    
    def _on_tune_clicked(self) -> None:
        """Apply the current frequency from digit display."""
        self._apply_frequency_change()
    
    def change_freq_step(self, step_mhz: float) -> None:
        current_freq = self._get_frequency_from_display()
        new_freq = max(0.001, current_freq + step_mhz)
        self._set_frequency_display(new_freq)
        self._apply_frequency_change()
    
    def _on_freq_down(self) -> None:
        self.change_freq_step(-0.025)
    
    def _on_freq_up(self) -> None:
        self.change_freq_step(0.025)
    
    def _on_spectrum_toggle(self) -> None:
        """Handle spectrum display toggle."""
        enabled = self.spectrum_enabled.get()
        self.scanner.set_spectrum_enabled(enabled)
        print(f"Spectrum display {'enabled' if enabled else 'disabled'}")
    
    def _on_demod_mode_change(self) -> None:
        """Handle demodulation mode change (NFM, WFM, AM)."""
        mode = self.demod_mode.get()
        self.scanner.set_demod_mode(mode)
        print(f"Demodulation mode changed to {mode}")
    
    def _on_volume_change(self, value: float) -> None:
        vol = int(float(value))
        self.volume_value_label.configure(text=f"{vol}%")
        if hasattr(self.scanner, 'demodulator') and self.scanner.demodulator:
            if hasattr(self.scanner.demodulator, 'set_volume'):
                self.scanner.demodulator.set_volume(vol / 100.0)
    
    def _on_buffer_change(self, value: float) -> None:
        buf = int(float(value))
        self.buffer_value_label.configure(text=f"{buf/1000:.0f}k")
        self.scanner.set_buffer_size(buf)
    
    def _on_ppm_change(self, value: float) -> None:
        ppm = int(float(value))
        self.ppm_value_label.configure(text=f"{ppm} ppm")
        
        # If running, stop temporarily to apply PPM correction cleanly
        was_running = self.is_scanning
        if was_running:
            self.scanner.stop_scan()
            time.sleep(0.1)  # Brief pause for thread to stop
        
        # Apply PPM correction
        self.driver.set_ppm_correction(ppm)
        
        # Restart if it was running
        if was_running:
            if self.scanner.is_manual_mode():
                current_freq = self.scanner.get_manual_freq()
                self.driver.tune(current_freq)
                print(f"Re-tuned to {current_freq/1e6:.3f} MHz with PPM {ppm}")
            self.scanner.start_scan()
        ppm = int(float(value))
        self.ppm_value_label.configure(text=f"{ppm} ppm")
        
        # If running, stop temporarily to apply PPM correction cleanly
        was_running = self.is_scanning
        if was_running:
            self.scanner.stop_scan()
            time.sleep(0.1)  # Brief pause for thread to stop
        
        # Apply PPM correction
        self.driver.set_ppm_correction(ppm)
        
        # Restart if it was running
        if was_running:
            if self.scanner.is_manual_mode():
                current_freq = self.scanner.get_manual_freq()
                self.driver.tune(current_freq)
                print(f"Re-tuned to {current_freq/1e6:.3f} MHz with PPM {ppm}")
            self.scanner.start_scan()
    
    def _on_start_scan(self) -> None:
        if self.is_scanning: return
        if not self.driver.connect():
            self._update_log("ERROR: Failed to connect to SDR")
            self._update_status("Error: No SDR", "#e74c3c")
            return
        if not self.scanner.start_scan():
            self._update_log("ERROR: Failed to start scanner")
            self.driver.disconnect()
            return
        self.is_scanning = True
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self._update_status("Scanning", "#2ecc71")
        self._update_log("Scan resumed")
        self.detection_count = 0
        self._update_counter()
    
    def _on_stop_scan(self) -> None:
        if not self.is_scanning: return
        self.scanner.stop_scan()
        self.driver.disconnect()
        self.is_scanning = False
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self._update_status("Idle", "#95a5a6")
        self._update_log("Scan paused")
    
    def poll_queue(self) -> None:
        try:
            while True:
                event = self.result_queue.get_nowait()
                self._handle_detection_event(event)
        except Empty: pass
        
        try:
            freqs, power = self.raw_queue.get_nowait()
            self._update_spectrum_plot(freqs, power)
        except Empty: pass
        
        if self.scanner.is_manual_mode():
            freq = self.scanner.get_manual_freq() / 1e6
            status = "Manual" if not self.is_scanning else f"Manual: {freq:.3f} MHz"
            color = "#e74c3c" if self.is_scanning else "#95a5a6"
            self._update_status(status, color)
        else:
            status = "Scanning" if self.is_scanning else "Scanner Idle"
            color = "#27ae60" if self.is_scanning else "#95a5a6"
            self._update_status(status, color)
            
        self.after(100, self.poll_queue)
    
    def _handle_detection_event(self, event: Dict[str, Any]) -> None:
        try:
            ts = event.get("timestamp", "").split("T")[1][:8]
            freq = event.get("frequency_hz", 0) / 1e6
            pwr = event.get("relative_power_db", 0)
            band = event.get("band_name", "Unknown")
            self._update_log(f"[{ts}] {freq:10.4f} MHz | Power: {pwr:6.1f} dB | Band: {band}")
            self.detection_count += 1
            self._update_counter()
        except Exception as e: print(f"Error handling event: {e}")
    
    def _update_spectrum_plot(self, frequencies: np.ndarray, power_spectrum: np.ndarray) -> None:
        try:
            freq_mhz = frequencies / 1e6
            self.spectrum_line.set_xdata(freq_mhz)
            self.spectrum_line.set_ydata(power_spectrum)
            self.spectrum_ax.set_xlim(freq_mhz.min(), freq_mhz.max())
            p_min, p_max = power_spectrum.min(), power_spectrum.max()
            margin = (p_max - p_min) * 0.1
            self.spectrum_ax.set_ylim(p_min - margin, p_max + margin)
            self.spectrum_canvas.draw_idle()
        except Exception: pass
    
    def _update_log(self, entry: str) -> None:
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", entry + "\n")
        # Optimization: Don't read full text, just check line count
        if int(self.log_textbox.index('end-1c').split('.')[0]) > self.max_log_entries:
            self.log_textbox.delete("1.0", "2.0")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")
    
    def _update_status(self, status: str, color: str) -> None:
        self.status_label.configure(text=f"Status: {status}", text_color=color)
    
    def _update_counter(self) -> None:
        self.counter_label.configure(text=f"Detections: {self.detection_count}")
    
    def _on_closing(self) -> None:
        print("Closing...")
        self.scanner.shutdown()
        self.destroy()

def main() -> None:
    app = MainWindow()
    app.mainloop()

if __name__ == "__main__":
    main()