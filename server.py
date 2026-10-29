#!/usr/bin/env python3
"""
SoundCloud Downloader Local API Server
Provides high-performance JSON API and static file serving for the native macOS UI.
"""

import os
import sys
import json
import urllib.parse
import subprocess
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
import engine

PORT = 5678
if getattr(sys, 'frozen', False):
    BASE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(sys.executable)))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Keep track of downloaded history
history = []

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

class AppRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _set_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def _read_json_body(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            body = self.rfile.read(content_length).decode("utf-8")
            return json.loads(body)
        return {}

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/api/status":
            self._set_headers()
            data = {
                "status": "online",
                "ffmpeg_ready": bool(engine.FFMPEG_PATH),
                "ffmpeg_path": engine.FFMPEG_PATH,
                "default_output_dir": os.path.expanduser("~/Downloads"),
                "qualities": engine.QUALITY_CONFIGS
            }
            self.wfile.write(json.dumps(data).encode("utf-8"))
            return

        elif path == "/api/progress":
            task_id = query.get("id", [""])[0]
            task = engine.get_task(task_id)
            if not task:
                self._set_headers(404)
                self.wfile.write(json.dumps({"error": "Task not found"}).encode("utf-8"))
                return

            task_dict = task.to_dict()
            if task.status == "completed" and task.result_path:
                # Add to history if not already there
                if not any(h.get("result_path") == task.result_path for h in history):
                    history.insert(0, {
                        "filename": task.result_filename,
                        "result_path": task.result_path,
                        "filesize": task.result_filesize,
                        "time": task_id
                    })

            self._set_headers()
            self.wfile.write(json.dumps(task_dict).encode("utf-8"))
            return

        elif path == "/api/history":
            self._set_headers()
            self.wfile.write(json.dumps({"history": history}).encode("utf-8"))
            return

        elif path == "/api/file":
            # Direct file download through browser
            file_path = query.get("path", [""])[0]
            if not file_path or not os.path.exists(file_path):
                self._set_headers(404)
                self.wfile.write(json.dumps({"error": "File not found"}).encode("utf-8"))
                return

            filename = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(file_size))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            with open(file_path, "rb") as f:
                shutil.copyfileobj(f, self.wfile)
            return

        # Serve static web files
        if path == "/":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/info":
            try:
                body = self._read_json_body()
                url = body.get("url", "")
                if not url:
                    self._set_headers(400)
                    self.wfile.write(json.dumps({"error": "URL обязателен"}).encode("utf-8"))
                    return

                info = engine.extract_media_info(url)
                self._set_headers()
                self.wfile.write(json.dumps(info).encode("utf-8"))
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        elif path == "/api/download":
            try:
                body = self._read_json_body()
                url = body.get("url", "")
                quality = body.get("quality", "mp3_320")
                as_zip = body.get("as_zip", True)
                output_dir = body.get("output_dir") or os.path.expanduser("~/Downloads")
                selected_tracks = body.get("selected_tracks")
                embed_artwork = body.get("embed_artwork", True)
                embed_metadata = body.get("embed_metadata", True)
                normalize_quiet = body.get("normalize_quiet", True)

                task = engine.create_task(
                    url=url,
                    quality=quality,
                    as_zip=as_zip,
                    output_dir=output_dir,
                    selected_tracks=selected_tracks,
                    embed_artwork=embed_artwork,
                    embed_metadata=embed_metadata,
                    normalize_quiet=normalize_quiet
                )

                self._set_headers()
                self.wfile.write(json.dumps({"task_id": task.task_id}).encode("utf-8"))
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        elif path == "/api/cancel":
            body = self._read_json_body()
            task_id = body.get("id")
            task = engine.get_task(task_id)
            if task:
                task.cancel()
            self._set_headers()
            self.wfile.write(json.dumps({"status": "cancelled"}).encode("utf-8"))
            return

        elif path == "/api/reveal":
            body = self._read_json_body()
            file_path = body.get("path")
            if file_path and os.path.exists(file_path):
                if sys.platform == "darwin":
                    subprocess.run(["open", "-R", file_path], check=False)
                elif sys.platform == "win32":
                    subprocess.run(["explorer", f"/select,{os.path.normpath(file_path)}"], check=False)
                else:
                    subprocess.run(["xdg-open", os.path.dirname(file_path)], check=False)
                self._set_headers()
                self.wfile.write(json.dumps({"status": "ok"}).encode("utf-8"))
            else:
                self._set_headers(404)
                self.wfile.write(json.dumps({"error": "Path does not exist"}).encode("utf-8"))
            return

        elif path == "/api/choose_directory":
            try:
                folder = None
                if sys.platform == "darwin":
                    script = 'POSIX path of (choose folder with prompt "Выберите папку для сохранения музыки SoundCloud:")'
                    res = subprocess.run(
                        ["osascript", "-e", script],
                        capture_output=True,
                        text=True,
                        check=False
                    )
                    if res.returncode == 0 and res.stdout.strip():
                        folder = res.stdout.strip().rstrip("/")
                elif sys.platform == "win32":
                    ps_cmd = (
                        "Add-Type -AssemblyName System.Windows.Forms; "
                        "$dialog = New-Object System.Windows.Forms.FolderBrowserDialog; "
                        "$dialog.Description = 'Выберите папку для сохранения музыки SoundCloud'; "
                        "$dialog.ShowNewFolderButton = $true; "
                        "if ($dialog.ShowDialog() -eq 'OK') { Write-Output $dialog.SelectedPath }"
                    )
                    res = subprocess.run(
                        ["powershell", "-NoProfile", "-Command", ps_cmd],
                        capture_output=True,
                        text=True,
                        check=False
                    )
                    if res.returncode == 0 and res.stdout.strip():
                        folder = res.stdout.strip()
                else:
                    try:
                        import tkinter as tk
                        from tkinter import filedialog
                        root = tk.Tk()
                        root.withdraw()
                        folder = filedialog.askdirectory(title="Выберите папку для сохранения музыки SoundCloud")
                        root.destroy()
                    except Exception:
                        pass

                if folder:
                    self._set_headers()
                    self.wfile.write(json.dumps({"path": folder}).encode("utf-8"))
                else:
                    self._set_headers()
                    self.wfile.write(json.dumps({"cancelled": True}).encode("utf-8"))
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        elif path == "/api/shutdown":
            self._set_headers()
            self.wfile.write(json.dumps({"status": "stopping"}).encode("utf-8"))
            threading.Thread(target=self.server.shutdown).start()
            return

        self._set_headers(404)
        self.wfile.write(json.dumps({"error": "Not found"}).encode("utf-8"))

def run_server(port=PORT):
    # Find free port if 5678 is occupied
    actual_port = port
    server = None
    for attempt_port in range(port, port + 10):
        try:
            server = ThreadedHTTPServer(("127.0.0.1", attempt_port), AppRequestHandler)
            actual_port = attempt_port
            break
        except OSError:
            continue

    if not server:
        raise RuntimeError("Could not find free port for local server")

    print(f"SoundCloud Downloader Server running on http://127.0.0.1:{actual_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
    finally:
        server.server_close()

if __name__ == "__main__":
    p = PORT
    if len(sys.argv) > 1:
        try:
            p = int(sys.argv[1])
        except ValueError:
            pass
    run_server(p)
