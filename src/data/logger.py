"""
Logger Module

This module implements database logging functionality for detected signal events.
All detection events are stored in a SQLite database for later analysis.
"""

import sqlite3
import threading
from typing import Dict, Any, Optional
import os


class SignalLogger:
    """
    SQLite-based logger for signal detection events.
    
    This class provides thread-safe database operations for logging
    detected signals with timestamp, frequency, power level, and band information.
    """
    
    def __init__(self, db_path: str = "scan_results.db") -> None:
        """
        Initialize the signal logger and create database schema.
        
        Args:
            db_path: Path to the SQLite database file (default: scan_results.db)
        """
        self.db_path: str = db_path
        self._lock: threading.Lock = threading.Lock()
        
        # Create the database and table if they don't exist
        self._initialize_database()
    
    def _initialize_database(self) -> None:
        """
        Create the detections table if it doesn't exist.
        
        Schema:
            - id: Auto-incrementing primary key
            - timestamp: Detection timestamp (ISO 8601 format)
            - frequency_hz: Detected frequency in Hz
            - power_db: Signal power in dB
            - band_name: Name of the band where signal was detected
        """
        try:
            conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=10.0
            )
            cursor = conn.cursor()
            
            # Create detections table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS detections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    frequency_hz REAL NOT NULL,
                    power_db REAL NOT NULL,
                    band_name TEXT NOT NULL
                )
            """)
            
            # Create indexes for common queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON detections(timestamp)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_frequency 
                ON detections(frequency_hz)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_band 
                ON detections(band_name)
            """)
            
            conn.commit()
            conn.close()
            
            print(f"Database initialized: {self.db_path}")
        
        except sqlite3.Error as e:
            print(f"Database initialization error: {e}")
    
    def log_event(self, event_dict: Dict[str, Any]) -> bool:
        """
        Log a detection event to the database.
        
        Args:
            event_dict: Dictionary containing event data with keys:
                - timestamp: ISO format timestamp string
                - frequency_hz: Detected frequency in Hz
                - relative_power_db or power_db: Signal power
                - band_name: Name of the band
        
        Returns:
            True if logging successful, False otherwise
        """
        try:
            # Extract required fields
            timestamp: str = event_dict.get("timestamp", "")
            frequency_hz: float = event_dict.get("frequency_hz", 0.0)
            
            # Try both field names for power
            power_db: float = event_dict.get(
                "relative_power_db",
                event_dict.get("power_db", 0.0)
            )
            
            band_name: str = event_dict.get("band_name", "Unknown")
            
            # Validate required fields
            if not timestamp or frequency_hz == 0:
                print("Warning: Invalid event data, skipping log entry")
                return False
            
            # Thread-safe database write
            with self._lock:
                conn = sqlite3.connect(
                    self.db_path,
                    check_same_thread=False,
                    timeout=10.0
                )
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO detections (timestamp, frequency_hz, power_db, band_name)
                    VALUES (?, ?, ?, ?)
                """, (timestamp, frequency_hz, power_db, band_name))
                
                conn.commit()
                conn.close()
            
            return True
        
        except sqlite3.Error as e:
            print(f"Database write error: {e}")
            return False
        
        except Exception as e:
            print(f"Unexpected error logging event: {e}")
            return False
    
    def get_recent_detections(self, limit: int = 100) -> list:
        """
        Retrieve the most recent detection events.
        
        Args:
            limit: Maximum number of records to retrieve (default: 100)
        
        Returns:
            List of tuples (id, timestamp, frequency_hz, power_db, band_name)
        """
        try:
            with self._lock:
                conn = sqlite3.connect(
                    self.db_path,
                    check_same_thread=False,
                    timeout=10.0
                )
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id, timestamp, frequency_hz, power_db, band_name
                    FROM detections
                    ORDER BY id DESC
                    LIMIT ?
                """, (limit,))
                
                results = cursor.fetchall()
                conn.close()
                
                return results
        
        except sqlite3.Error as e:
            print(f"Database read error: {e}")
            return []
    
    def get_detection_count(self) -> int:
        """
        Get the total number of detections in the database.
        
        Returns:
            Total detection count
        """
        try:
            with self._lock:
                conn = sqlite3.connect(
                    self.db_path,
                    check_same_thread=False,
                    timeout=10.0
                )
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM detections")
                count = cursor.fetchone()[0]
                
                conn.close()
                
                return count
        
        except sqlite3.Error as e:
            print(f"Database query error: {e}")
            return 0
    
    def clear_all_detections(self) -> bool:
        """
        Clear all detection records from the database.
        
        WARNING: This permanently deletes all logged data.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._lock:
                conn = sqlite3.connect(
                    self.db_path,
                    check_same_thread=False,
                    timeout=10.0
                )
                cursor = conn.cursor()
                
                cursor.execute("DELETE FROM detections")
                cursor.execute("VACUUM")  # Reclaim space
                
                conn.commit()
                conn.close()
                
                print("All detections cleared from database")
                return True
        
        except sqlite3.Error as e:
            print(f"Database clear error: {e}")
            return False
