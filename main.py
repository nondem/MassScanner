import customtkinter as ctk
import sys
import os

# Ensure the src directory is in the python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from ui.main_window import MainWindow

def main():
    # Set appearance mode (System, Dark, Light)
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")

    app = MainWindow()
    
    # Graceful exit handler
    try:
        app.mainloop()
    except KeyboardInterrupt:
        print("\nShutting down...")
        app.destroy()

if __name__ == "__main__":
    main()