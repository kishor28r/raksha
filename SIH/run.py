"""
RAKSHA: AI-Powered Emergency Response & Resource Allocation System
Single-Command Startup Script for Smart India Hackathon Prototype

Usage:
    py run.py
"""

import sys
import os
import webbrowser
import time
import threading

# Add workspace directory to python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn


def open_browser():
    """Wait for server to start, then open the browser dashboard."""
    time.sleep(1.5)
    url = "http://127.0.0.1:8000"
    print(f"\n=======================================================")
    print(f">> RAKSHA AI Command Center is LIVE at: {url}")
    print(f"=======================================================\n")
    try:
        webbrowser.open(url)
    except Exception:
        pass


if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("Starting RAKSHA Emergency Response & Resource Allocation System...")
    # Start browser opener in background thread
    threading.Thread(target=open_browser, daemon=True).start()

    # Launch FastAPI Server via Uvicorn
    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info"
    )
