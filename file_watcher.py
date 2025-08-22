# file_watcher.py
import time
import threading
import logging
from app import run_smart_rescan_bg, STATE, STATE_LOCK

SCAN_INTERVAL_SECONDS = 60  # check every 1 minute

def start_file_watch():
    while True:
        with STATE_LOCK:
            already_running = STATE["job"]["status"] == "running"
            print("🟢 termsAccepted:", STATE["termsAccepted"])
            print("🟡 already_running:", already_running)
        if not already_running and STATE["termsAccepted"]:
            logging.info("🔄 Auto Smart Rescan Triggered from watcher.")
            threading.Thread(target=run_smart_rescan_bg, daemon=True).start()
        time.sleep(SCAN_INTERVAL_SECONDS)