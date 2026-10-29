"""
SoundCloud Downloader - Windows Native Application Launcher
Runs the local REST API server and launches a native desktop window (Edge WebView2) or default browser.
"""
import os
import sys
import time
import threading
import webbrowser
import urllib.request

# Ensure current directory is on sys.path
if getattr(sys, 'frozen', False):
    BASE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(sys.executable)))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import server

PORT = 5678
SERVER_URL = f"http://127.0.0.1:{PORT}"

def run_server():
    server.run_server(port=PORT)

def is_server_ready():
    try:
        req = urllib.request.urlopen(f"{SERVER_URL}/api/status", timeout=0.5)
        return req.getcode() == 200
    except Exception:
        return False

def main():
    # 1. Start local server in background
    srv_thread = threading.Thread(target=run_server, daemon=True)
    srv_thread.start()

    # 2. Wait up to 3 seconds for port to open
    for _ in range(30):
        if is_server_ready():
            break
        time.sleep(0.1)

    # 3. Launch Native WebView2 Window if available
    icon_path = os.path.join(BASE_DIR, "icon.ico")
    try:
        import webview
        window = webview.create_window(
            title="SoundCloud Downloader",
            url=SERVER_URL,
            width=960,
            height=780,
            min_size=(780, 560),
            background_color="#121316",
            text_select=True
        )
        # Use Edge WebView2 (Chromium) on Windows
        webview.start(gui="edgechromium", debug=False)
        sys.exit(0)
    except Exception:
        # Fallback to default browser
        webbrowser.open(SERVER_URL)
        print(f"SoundCloud Downloader running at {SERVER_URL}")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    main()
