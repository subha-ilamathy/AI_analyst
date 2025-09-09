#!/usr/bin/env python3
"""Launcher script for the Streamlit app."""

import subprocess
import sys
import os


def main():
    """Launch the Streamlit app."""
    # Check if streamlit is installed
    try:
        import streamlit
    except ImportError:
        print("Streamlit not found. Installing dependencies...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    
    # Launch the app
    app_path = os.path.join(os.path.dirname(__file__), "app.py")
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", app_path,
        "--server.port", "8501",
        "--server.address", "localhost"
    ])


if __name__ == "__main__":
    main()
