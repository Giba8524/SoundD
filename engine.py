#!/usr/bin/env python3
"""
SoundCloud Downloader Engine
Supports: Single tracks, Playlists, Albums, Quality selection, ZIP archiving, Cover embedding, ID3 tagging.
"""

import os
import re
import sys
import time
import shutil
import zipfile
import threading
import subprocess
from typing import Optional, Dict, Any, List, Callable

# Auto-detect or import static_ffmpeg if available
FFMPEG_PATH = None
FFPROBE_PATH = None

try:
    import static_ffmpeg
    f_path, p_path = static_ffmpeg.run.get_or_fetch_platform_executables_else_raise()
    if os.path.exists(f_path):
        FFMPEG_PATH = f_path
        FFPROBE_PATH = p_path
except Exception as e:
    pass

if not FFMPEG_PATH:
    # Check default fallback locations for macOS and Windows
    potential_paths = [
        shutil.which("ffmpeg"),
        shutil.which("ffmpeg.exe"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg.exe"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin", "ffmpeg.exe"),
        "C:\\ffmpeg\\bin\\ffmpeg.exe",
        "/Users/mihail/Library/Python/3.9/lib/python/site-packages/static_ffmpeg/bin/darwin_arm64/ffmpeg",
        "/opt/homebrew/bin/ffmpeg",
        "/usr/local/bin/ffmpeg"
    ]
    for p in potential_paths:
        if p and os.path.exists(p):
            FFMPEG_PATH = p
            break

import yt_dlp

QUALITY_CONFIGS = {
    "direct_stream": {
        "label": "Оригинальный поток (Direct Stream)",
        "sublabel": "Без перекодирования (1:1 с SoundCloud)",
        "badge": "Без пережатия",
        "codec": "copy",
        "quality": "0",
        "ext": "m4a",
        "lossless": False
    },
    "mp3_320": {
        "label": "MP3 320 kbps (Максимальный MP3)",
        "sublabel": "Рекомендуется для плееров и авто",
        "badge": "Популярный",
        "codec": "mp3",
        "quality": "320",
        "ext": "mp3",
        "lossless": False
    },
    "mp3_256": {
        "label": "MP3 256 kbps (Высокое качество)",
        "sublabel": "Оптимальный баланс размера и звука",
        "badge": "Стандарт+",
        "codec": "mp3",
        "quality": "256",
        "ext": "mp3",
        "lossless": False
    },
    "mp3_128": {
        "label": "MP3 128 kbps (Стандартный стрим)",
        "sublabel": "Базовое качество SoundCloud",
        "badge": "Стандарт",
        "codec": "mp3",
        "quality": "128",
        "ext": "mp3",
        "lossless": False
    },
    "m4a_256": {
        "label": "M4A / AAC 256 kbps (Apple формат)",
        "sublabel": "Для Apple Music, iPhone и Mac",
        "badge": "Apple",
        "codec": "m4a",
        "quality": "256",
        "ext": "m4a",
        "lossless": False
    },
    "flac": {
        "label": "FLAC (Lossless контейнер)",
        "sublabel": "Аудио без дополнительного сжатия",
        "badge": "Lossless",
        "codec": "flac",
        "quality": "0",
        "ext": "flac",
        "lossless": True
    },
    "wav": {
        "label": "WAV (Студийный несжатый)",
        "sublabel": "Несжатый PCM звук (без обложки)",
        "badge": "PCM",
        "codec": "wav",
        "quality": "0",
        "ext": "wav",
        "lossless": True
    }
}

SUPPORTED_THUMBNAIL_EXTS = {"mp3", "m4a", "flac", "ogg", "opus"}

def smart_boost_quiet_audio(filepath: str, max_headroom_threshold: float = -2.0, target_headroom: float = 0.5) -> float:
    """
    Intelligently amplifies quiet tracks without reducing loud tracks.
    If track's max peak has more than 2 dB of headroom, boosts it to -0.5 dB True Peak.
    If track is already loud (peak >= -2.0 dB), leaves it 100% untouched.
    Returns the amount of boost in dB applied (0.0 if untouched).
    """
    if not FFMPEG_PATH or not os.path.exists(filepath):
        return 0.0

    try:
        # Step 1: Detect volume peak
        res = subprocess.run(
            [FFMPEG_PATH, "-i", filepath, "-af", "volumedetect", "-f", "null", "-"],
            capture_output=True,
            text=True,
            check=False
        )
        m = re.search(r"max_volume:\s*(-?[\d\.]+)\s*dB", res.stderr)
        if not m:
            return 0.0

        max_vol = float(m.group(1))

        # Only boost if quiet (more than threshold headroom, e.g. -2.0 dB)
        if max_vol < max_headroom_threshold:
            boost_db = abs(max_vol) - target_headroom
            if boost_db <= 0.5:
                return 0.0

            _, ext = os.path.splitext(filepath)
            ext_clean = ext.lstrip(".").lower()
            codec_args = []

            if ext_clean == "mp3":
                codec_args = ["-c:a", "libmp3lame", "-b:a", "320k"]
            elif ext_clean == "m4a":
                codec_args = ["-c:a", "aac", "-b:a", "256k"]
            elif ext_clean == "flac":
                codec_args = ["-c:a", "flac"]
            elif ext_clean == "wav":
                codec_args = ["-c:a", "pcm_s16le"]
            else:
                codec_args = ["-c:a", "aac", "-b:a", "256k"]

            temp_output = filepath + f".temp_boost.{ext_clean}"
            apply_res = subprocess.run(
                [
                    FFMPEG_PATH, "-y", "-i", filepath,
                    "-af", f"volume={boost_db:.1f}dB",
                    *codec_args,
                    "-map_metadata", "0",
                    temp_output
                ],
                capture_output=True,
                check=False
            )

            if apply_res.returncode == 0 and os.path.exists(temp_output) and os.path.getsize(temp_output) > 1000:
                os.replace(temp_output, filepath)
                return boost_db
            else:
                if os.path.exists(temp_output):
                    os.remove(temp_output)
                return 0.0
        else:
            # Already loud, do nothing
            return 0.0
    except Exception as e:
        print(f"Warning in smart_boost_quiet_audio: {e}")
        return 0.0

def analyze_transcodings(transcodings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Parse SoundCloud transcodings list to determine max available bitrate and codec."""
    if not transcodings:
        return {
            "bitrate": 128,
            "codec": "MP3",
            "label": "MP3 128 kbps",
            "is_hq": False,
            "has_original": False,
            "streams": ["MP3 128 kbps"]
        }

    max_br = 0
    codec = "MP3"
    streams = []
    has_orig = False

    for item in transcodings:
        preset = str(item.get("preset", "")).lower()
        mime = str(item.get("format", {}).get("mime_type", "")).lower()
        
        # Check presets
        br = 0
        cur_codec = "MP3"
        if "160" in preset:
            br = 160
        elif "256" in preset:
            br = 256
        elif "128" in preset:
            br = 128
        elif "96" in preset:
            br = 96
        elif "64" in preset:
            br = 64

        if "aac" in preset or "mp4" in mime:
            cur_codec = "AAC"
        elif "opus" in preset or "ogg" in mime:
            cur_codec = "Opus"
        elif "mp3" in preset or "mpeg" in mime:
            cur_codec = "MP3"
        elif "original" in preset or "lossless" in preset:
            cur_codec = "Original Lossless"
            has_orig = True
            br = 320

        if br > max_br:
            max_br = br
            codec = cur_codec

        stream_name = f"{cur_codec} {br} kbps" if br else cur_codec
        if stream_name not in streams:
            streams.append(stream_name)

    if max_br == 0:
        max_br = 128
        codec = "MP3"

    label = f"{codec} {max_br} kbps"
    if has_orig:
        label = "Оригинал (Studio Lossless / WAV / FLAC)"

    return {
        "bitrate": max_br,
        "codec": codec,
        "label": label,
        "is_hq": max_br >= 160 or has_orig,
        "has_original": has_orig,
        "streams": streams
    }

def analyze_formats_from_ytdl(formats: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Parse yt-dlp extracted formats to determine available source stream quality."""
    if not formats:
        return {
            "bitrate": 128,
            "codec": "MP3",
            "label": "MP3 128 kbps",
            "is_hq": False,
            "has_original": False,
            "streams": ["MP3 128 kbps"]
        }

    max_br = 0
    codec = "MP3"
    has_orig = False
    streams = []

    for f in formats:
        fid = str(f.get("format_id", "")).lower()
        abr = f.get("abr") or f.get("tbr") or 0
        acodec = str(f.get("acodec", "")).lower()

        if "original" in fid:
            has_orig = True

        cur_codec = "MP3"
        if "mp4a" in acodec or "aac" in acodec or "aac" in fid:
            cur_codec = "AAC"
        elif "opus" in acodec or "opus" in fid:
            cur_codec = "Opus"
        elif "mp3" in acodec or "mp3" in fid:
            cur_codec = "MP3"
        elif "flac" in acodec or "wav" in acodec:
            cur_codec = "Lossless"
            has_orig = True

        br = int(abr) if abr else 0
        if br > max_br:
            max_br = br
            codec = cur_codec

        st_label = f"{cur_codec} {br} kbps" if br else cur_codec
        if st_label not in streams:
            streams.append(st_label)

    if max_br == 0:
        max_br = 128
        codec = "MP3"

    label = f"{codec} {max_br} kbps"
    if has_orig:
        label = "Оригинал от автора"

    return {
        "bitrate": max_br,
        "codec": codec,
        "label": label,
        "is_hq": max_br >= 160 or has_orig,
        "has_original": has_orig,
        "streams": streams
    }

def sanitize_filename(name: str) -> str:
    """Sanitize string to be safe for macOS filesystem."""
    if not name:
        return "untitled"
    # Replace slashes and colons (special in macOS / HFS+)
    clean = re.sub(r'[/\\:\*\?"<>\|]', '_', name)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean[:200]

def format_duration(seconds: Optional[float]) -> str:
    """Format duration in seconds to mm:ss or hh:mm:ss."""
    if not seconds or seconds < 0:
        return "--:--"
    total_sec = int(round(seconds))
    hrs = total_sec // 3600
    mins = (total_sec % 3600) // 60
    secs = total_sec % 60
    if hrs > 0:
        return f"{hrs}:{mins:02d}:{secs:02d}"
    return f"{mins}:{secs:02d}"

def format_size(bytes_num: Optional[int]) -> str:
    """Format bytes into readable string."""
    if not bytes_num or bytes_num <= 0:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_num < 1024.0:
            return f"{bytes_num:.1f} {unit}"
        bytes_num /= 1024.0
    return f"{bytes_num:.1f} TB"

def get_best_artwork(info: Dict[str, Any]) -> Optional[str]:
    """Extract highest quality artwork URL from metadata."""
    if not info:
        return None
    # Check thumbnails list
    thumbnails = info.get("thumbnails") or []
    if thumbnails:
        # Sort by preference / resolution
        best = thumbnails[-1].get("url")
        if best:
            # Upgrade standard soundcloud -large.jpg to -t500x500.jpg or -original.jpg
            best = re.sub(r'-large\.(jpg|png)', r'-t500x500.\1', best)
            return best
    thumb = info.get("thumbnail")
    if thumb:
        return re.sub(r'-large\.(jpg|png)', r'-t500x500.\1', thumb)
    return None

def fetch_soundcloud_hydration(url: str) -> Optional[Dict[str, Any]]:
    """
    Fast extraction using SoundCloud webpage hydration data.
    Provides instant tracklist, durations, artwork, and titles.
    """
    try:
        import urllib.request
        import json
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        )
        with urllib.request.urlopen(req, timeout=6) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        # Extract og:image if available
        og_image = None
        og_m = re.search(r'<meta property="og:image" content="([^"]+)"', html)
        if og_m:
            og_image = og_m.group(1).replace("-large.", "-t500x500.")

        m = re.search(r'window\.__sc_hydration\s*=\s*(\[.*?\]);</script>', html, re.DOTALL)
        if not m:
            return None

        hydration = json.loads(m.group(1))
        for item in hydration:
            data = item.get("data", {})
            if item.get("hydratable") in ("playlist", "system_playlist") or "tracks" in data:
                p_title = data.get("title") or "SoundCloud Playlist"
                user_info = data.get("user") or {}
                uploader = user_info.get("username") or "SoundCloud Artist"
                artwork = data.get("artwork_url") or og_image
                if artwork:
                    artwork = artwork.replace("-large.", "-t500x500.")

                raw_tracks = data.get("tracks", [])
                track_list = []
                total_duration = 0.0

                for idx, t in enumerate(raw_tracks, start=1):
                    t_title = t.get("title")
                    if not t_title:
                        continue
                    t_user = t.get("user") or {}
                    t_uploader = t_user.get("username") or uploader
                    t_dur_ms = t.get("duration") or 0
                    t_dur_s = float(t_dur_ms) / 1000.0 if t_dur_ms else 0.0
                    total_duration += t_dur_s

                    t_thumb = t.get("artwork_url") or artwork
                    if t_thumb:
                        t_thumb = t_thumb.replace("-large.", "-t500x500.")

                    t_url = t.get("permalink_url")
                    if not t_url and t.get("permalink") and user_info.get("permalink"):
                        t_url = f"https://soundcloud.com/{user_info.get('permalink')}/{t.get('permalink')}"

                    track_list.append({
                        "index": idx,
                        "id": str(t.get("id") or idx),
                        "title": t_title,
                        "uploader": t_uploader,
                        "duration": t_dur_s,
                        "duration_formatted": format_duration(t_dur_s),
                        "artwork": t_thumb,
                        "url": t_url or url
                    })

                is_album = "/albums" in url or data.get("set_type") == "album"
                expected_count = data.get("track_count") or len(raw_tracks)
                
                # Analyze source stream quality
                first_transcodings = []
                if raw_tracks and isinstance(raw_tracks[0], dict):
                    first_transcodings = raw_tracks[0].get("media", {}).get("transcodings", [])
                source_info = analyze_transcodings(first_transcodings)

                return {
                    "type": "album" if is_album else "playlist",
                    "is_playlist": True,
                    "title": p_title,
                    "uploader": uploader,
                    "uploader_url": user_info.get("permalink_url"),
                    "artwork": artwork,
                    "track_count": expected_count,
                    "total_duration": total_duration,
                    "total_duration_formatted": format_duration(total_duration),
                    "tracks": track_list,
                    "url": url,
                    "qualities": QUALITY_CONFIGS,
                    "source_info": source_info,
                    "_partial": len(track_list) < expected_count
                }

            elif item.get("hydratable") == "sound" and "title" in data:
                # Single track
                s_title = data.get("title") or "SoundCloud Track"
                user_info = data.get("user") or {}
                uploader = user_info.get("username") or "SoundCloud Artist"
                dur_ms = data.get("duration") or 0
                dur_s = float(dur_ms) / 1000.0 if dur_ms else 0.0
                artwork = data.get("artwork_url") or og_image
                if artwork:
                    artwork = artwork.replace("-large.", "-t500x500.")

                transcodings = data.get("media", {}).get("transcodings", [])
                source_info = analyze_transcodings(transcodings)

                return {
                    "type": "track",
                    "is_playlist": False,
                    "title": s_title,
                    "uploader": uploader,
                    "uploader_url": user_info.get("permalink_url"),
                    "artwork": artwork,
                    "duration": dur_s,
                    "duration_formatted": format_duration(dur_s),
                    "genre": data.get("genre"),
                    "description": (data.get("description") or "")[:300],
                    "url": data.get("permalink_url") or url,
                    "qualities": QUALITY_CONFIGS,
                    "source_info": source_info
                }
    except Exception:
        pass
    return None

def extract_media_info(url: str) -> Dict[str, Any]:
    """
    Extract metadata from a SoundCloud URL.
    Returns structured data for either a single track, playlist, or album.
    """
    url = url.strip()
    if not url:
        raise ValueError("URL cannot be empty")

    # Fast path: Try webpage hydration first (0.3s response time!)
    fast_info = fetch_soundcloud_hydration(url)
    if fast_info and not fast_info.get("_partial"):
        return fast_info

    # Fallback to yt-dlp to get all tracks for large playlists
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    if FFMPEG_PATH:
        ydl_opts["ffmpeg_location"] = FFMPEG_PATH

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if not info:
            if fast_info:
                return fast_info
            raise ValueError("Не удалось получить информацию по ссылке")

    is_playlist = info.get("_type") == "playlist" or "entries" in info

    if is_playlist:
        entries = info.get("entries") or []
        track_list = []
        total_duration = 0.0

        for idx, entry in enumerate(entries, start=1):
            if not entry:
                continue
            e_title = entry.get("title")
            if not e_title:
                e_url = entry.get("url") or ""
                slug = e_url.rstrip("/").split("/")[-1]
                e_title = slug.replace("-", " ").capitalize() if slug else f"Track {idx}"

            e_uploader = entry.get("uploader") or info.get("uploader") or (fast_info.get("uploader") if fast_info else "SoundCloud Artist")
            e_uploader = e_uploader.strip('"\'')
            dur = entry.get("duration")
            if dur:
                total_duration += float(dur)

            thumb = get_best_artwork(entry) or (fast_info.get("artwork") if fast_info else get_best_artwork(info))
            track_url = entry.get("url") or entry.get("webpage_url")
            if track_url and not track_url.startswith("http"):
                track_url = f"https://soundcloud.com{track_url}"

            track_list.append({
                "index": idx,
                "id": str(entry.get("id") or idx),
                "title": e_title,
                "uploader": e_uploader,
                "duration": dur,
                "duration_formatted": format_duration(dur),
                "artwork": thumb,
                "url": track_url or url
            })

        album_title = info.get("title") or (fast_info.get("title") if fast_info else "SoundCloud Playlist")
        uploader = (info.get("uploader") or (fast_info.get("uploader") if fast_info else "SoundCloud Artist")).strip('"\'')
        artwork = (fast_info.get("artwork") if fast_info else None) or get_best_artwork(info)
        if not artwork and track_list and track_list[0].get("artwork"):
            artwork = track_list[0]["artwork"]

        is_album = "/albums" in url or info.get("album_type") == "album"

        source_info = analyze_formats_from_ytdl(info.get("formats", []))

        return {
            "type": "album" if is_album else "playlist",
            "is_playlist": True,
            "title": album_title,
            "uploader": uploader,
            "uploader_url": info.get("uploader_url") or (fast_info.get("uploader_url") if fast_info else None),
            "artwork": artwork,
            "track_count": len(track_list),
            "total_duration": total_duration,
            "total_duration_formatted": format_duration(total_duration),
            "tracks": track_list,
            "url": url,
            "qualities": QUALITY_CONFIGS,
            "source_info": source_info
        }
    else:
        # Single track
        title = info.get("title") or "SoundCloud Track"
        uploader = (info.get("uploader") or "SoundCloud Artist").strip('"\'')
        duration = info.get("duration")
        artwork = get_best_artwork(info)
        genre = info.get("genre")
        description = info.get("description")
        source_info = analyze_formats_from_ytdl(info.get("formats", []))

        return {
            "type": "track",
            "is_playlist": False,
            "title": title,
            "uploader": uploader,
            "uploader_url": info.get("uploader_url"),
            "artwork": artwork,
            "duration": duration,
            "duration_formatted": format_duration(duration),
            "genre": genre,
            "description": description[:300] if description else None,
            "url": url,
            "qualities": QUALITY_CONFIGS,
            "source_info": source_info
        }

def trigger_macos_notification(title: str, subtitle: str, message: str):
    """Fire a native OS notification (macOS or Windows)."""
    try:
        if sys.platform == "darwin":
            clean_title = title.replace('"', '\\"')
            clean_sub = subtitle.replace('"', '\\"')
            clean_msg = message.replace('"', '\\"')
            script = f'display notification "{clean_msg}" with title "{clean_title}" subtitle "{clean_sub}" sound name "Glass"'
            subprocess.run(["osascript", "-e", script], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif sys.platform == "win32":
            # Native Windows Toast Notification via PowerShell
            ps_script = (
                "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null; "
                "$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02); "
                "$textNodes = $template.GetElementsByTagName('text'); "
                f"$textNodes.Item(0).AppendChild($template.CreateTextNode('{title}')) > $null; "
                f"$textNodes.Item(1).AppendChild($template.CreateTextNode('{message}')) > $null; "
                "$toast = [Windows.UI.Notifications.ToastNotification]::new($template); "
                "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('SoundCloud Downloader').Show($toast);"
            )
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

class DownloadTask:
    """Manages an active background download with progress monitoring."""
    def __init__(self, task_id: str, url: str, quality: str = "mp3_320",
                 as_zip: bool = True, output_dir: Optional[str] = None,
                 selected_tracks: Optional[List[int]] = None,
                 embed_artwork: bool = True, embed_metadata: bool = True,
                 normalize_quiet: bool = True):
        self.task_id = task_id
        self.url = url
        self.quality = quality if quality in QUALITY_CONFIGS else "mp3_320"
        self.as_zip = as_zip
        self.output_dir = os.path.expanduser(output_dir or "~/Downloads")
        self.selected_tracks = selected_tracks  # 1-based indices
        self.embed_artwork = embed_artwork
        self.embed_metadata = embed_metadata
        self.normalize_quiet = normalize_quiet

        self.cancelled = False
        self.status = "queued"  # queued, downloading, converting, zipping, completed, error, cancelled
        self.progress = 0.0     # 0 to 100
        self.speed_str = ""
        self.eta_str = ""
        self.current_track_idx = 0
        self.total_tracks = 1
        self.current_track_title = ""
        self.message = "Инициализация загрузки..."
        self.result_path = ""
        self.result_filename = ""
        self.result_filesize = ""
        self.error_message = ""
        self.thread: Optional[threading.Thread] = None

    def start(self):
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def cancel(self):
        self.cancelled = True
        self.status = "cancelled"
        self.message = "Загрузка отменена пользователем"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": self.status,
            "progress": round(self.progress, 1),
            "speed": self.speed_str,
            "eta": self.eta_str,
            "current_track_idx": self.current_track_idx,
            "total_tracks": self.total_tracks,
            "current_track_title": self.current_track_title,
            "message": self.message,
            "result_path": self.result_path,
            "result_filename": self.result_filename,
            "result_filesize": self.result_filesize,
            "error_message": self.error_message
        }

    def _run(self):
        try:
            os.makedirs(self.output_dir, exist_ok=True)
            info = extract_media_info(self.url)

            if info.get("is_playlist"):
                self._download_playlist(info)
            else:
                self._download_single(info)

        except Exception as e:
            if not self.cancelled:
                self.status = "error"
                self.error_message = str(e)
                self.message = f"Ошибка: {str(e)}"

    def _progress_hook(self, d: Dict[str, Any]):
        if self.cancelled:
            raise Exception("Download cancelled by user")

        status = d.get("status")
        if status == "downloading":
            downloaded = d.get("downloaded_bytes", 0)
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            if total > 0:
                track_pct = (downloaded / total) * 100.0
            else:
                # For HLS streams with fragment counts
                frag_index = d.get("fragment_index", 0)
                frag_count = d.get("fragment_count", 0)
                track_pct = (frag_index / frag_count * 100.0) if frag_count > 0 else 50.0

            if self.total_tracks > 1:
                completed_portion = ((max(0, self.current_track_idx - 1)) / self.total_tracks) * 100.0
                current_portion = (track_pct / self.total_tracks)
                self.progress = min(99.0, completed_portion + current_portion)
            else:
                self.progress = min(99.0, track_pct)

            speed = d.get("speed")
            if speed:
                self.speed_str = f"{format_size(speed)}/s"

            eta = d.get("eta")
            if eta:
                self.eta_str = f"{eta} сек."

            self.status = "downloading"
            self.message = f"Скачивание: {self.current_track_title or 'аудио'} ({self.progress:.0f}%)"

        elif status == "finished":
            self.message = "Обработка и вшивание метаданных..."

    def _download_single(self, info: Dict[str, Any]):
        self.status = "downloading"
        self.total_tracks = 1
        self.current_track_idx = 1
        self.current_track_title = info.get("title", "Трек")
        self.message = f"Подготовка к загрузке: {self.current_track_title}"

        cfg = QUALITY_CONFIGS[self.quality]
        ext = cfg["ext"]

        artist = sanitize_filename(info.get("uploader", "SoundCloud"))
        title = sanitize_filename(info.get("title", "Track"))
        safe_base = f"{artist} - {title}"
        target_file = os.path.join(self.output_dir, f"{safe_base}.{ext}")

        # Unique filename if exists
        counter = 1
        while os.path.exists(target_file):
            target_file = os.path.join(self.output_dir, f"{safe_base} ({counter}).{ext}")
            counter += 1

        ydl_opts: Dict[str, Any] = {
            "format": "bestaudio/best",
            "outtmpl": os.path.splitext(target_file)[0] + ".%(ext)s",
            "progress_hooks": [self._progress_hook],
            "quiet": True,
            "no_warnings": True,
        }

        if FFMPEG_PATH:
            ydl_opts["ffmpeg_location"] = FFMPEG_PATH

        pps = []
        if cfg["codec"] != "copy":
            pps.append({
                "key": "FFmpegExtractAudio",
                "preferredcodec": cfg["codec"],
                "preferredquality": cfg["quality"],
            })

        if self.embed_metadata:
            pps.append({
                "key": "FFmpegMetadata",
                "add_metadata": True,
            })

        # Only embed thumbnail for containers that support it (mp3, m4a, flac)
        if self.embed_artwork and FFMPEG_PATH and ext in SUPPORTED_THUMBNAIL_EXTS:
            ydl_opts["writethumbnail"] = True
            pps.append({
                "key": "EmbedThumbnail",
            })

        ydl_opts["postprocessors"] = pps

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([self.url])

        if self.cancelled:
            return

        # Find final file
        if not os.path.exists(target_file):
            candidates = [
                os.path.join(self.output_dir, f) for f in os.listdir(self.output_dir)
                if safe_base in f and not f.endswith(('.jpg', '.png', '.webp', '.part'))
            ]
            if candidates:
                target_file = candidates[0]

        # Smart volume boost for quiet tracks if enabled
        if self.normalize_quiet and os.path.exists(target_file):
            self.message = "Проверка громкости и выравнивание..."
            boost = smart_boost_quiet_audio(target_file)
            if boost > 0:
                print(f"Applied +{boost:.1f} dB boost to quiet track {target_file}")

        file_size = os.path.getsize(target_file) if os.path.exists(target_file) else 0

        self.progress = 100.0
        self.status = "completed"
        self.result_path = target_file
        self.result_filename = os.path.basename(target_file)
        self.result_filesize = format_size(file_size)
        self.message = f"Трек успешно сохранён ({self.result_filesize})"

        trigger_macos_notification(
            title="SoundCloud Downloader",
            subtitle="Трек загружен!",
            message=f"{self.result_filename} сохранён в Загрузки"
        )

    def _download_playlist(self, info: Dict[str, Any]):
        all_tracks = info.get("tracks", [])
        total_count = len(all_tracks)

        # Filter tracks if user picked specific indices
        if self.selected_tracks:
            selected_set = set(self.selected_tracks)
            tracks_to_download = [t for t in all_tracks if t["index"] in selected_set]
        else:
            tracks_to_download = all_tracks

        if not tracks_to_download:
            raise ValueError("Не выбрано ни одного трека для загрузки")

        self.total_tracks = len(tracks_to_download)
        playlist_title = sanitize_filename(info.get("title", "SoundCloud Playlist"))
        artist = sanitize_filename(info.get("uploader", "SoundCloud"))

        # Temporary staging folder for the tracks
        staging_dir = os.path.join(self.output_dir, f".sc_dl_temp_{self.task_id}")
        os.makedirs(staging_dir, exist_ok=True)

        cfg = QUALITY_CONFIGS[self.quality]
        ext = cfg["ext"]

        downloaded_files = []

        try:
            for idx, track in enumerate(tracks_to_download, start=1):
                if self.cancelled:
                    break

                self.current_track_idx = idx
                self.current_track_title = track.get("title", f"Track {idx}")
                self.message = f"Загрузка ({idx}/{self.total_tracks}): {self.current_track_title}"

                track_artist = sanitize_filename(track.get("uploader") or artist)
                track_title = sanitize_filename(track.get("title", f"Track {idx}"))
                clean_name = f"{idx:02d}. {track_artist} - {track_title}"
                track_dest = os.path.join(staging_dir, f"{clean_name}.{ext}")

                ydl_opts: Dict[str, Any] = {
                    "format": "bestaudio/best",
                    "outtmpl": os.path.splitext(track_dest)[0] + ".%(ext)s",
                    "progress_hooks": [self._progress_hook],
                    "quiet": True,
                    "no_warnings": True,
                }
                if FFMPEG_PATH:
                    ydl_opts["ffmpeg_location"] = FFMPEG_PATH

                pps = []
                if cfg["codec"] != "copy":
                    pps.append({
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": cfg["codec"],
                        "preferredquality": cfg["quality"],
                    })

                if self.embed_metadata:
                    pps.append({"key": "FFmpegMetadata", "add_metadata": True})

                if self.embed_artwork and FFMPEG_PATH and ext in SUPPORTED_THUMBNAIL_EXTS:
                    ydl_opts["writethumbnail"] = True
                    pps.append({"key": "EmbedThumbnail"})

                ydl_opts["postprocessors"] = pps

                track_url = track.get("url") or self.url
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([track_url])
                except Exception as track_err:
                    print(f"Warning: Failed to download track {track_title}: {track_err}")
                    continue

                if os.path.exists(track_dest):
                    downloaded_files.append(track_dest)
                else:
                    # Search for any audio file created with this track index prefix
                    for f in os.listdir(staging_dir):
                        if f.startswith(f"{idx:02d}.") and not f.endswith(('.jpg', '.png', '.webp', '.part')):
                            downloaded_files.append(os.path.join(staging_dir, f))
                            break

            if self.cancelled:
                shutil.rmtree(staging_dir, ignore_errors=True)
                return

            if not downloaded_files:
                raise ValueError("Не удалось скачать ни один трек из плейлиста")

            # Smart volume boost for quiet tracks in playlist
            if self.normalize_quiet:
                self.message = "Проверка громкости и выравнивание треков..."
                for fpath in downloaded_files:
                    smart_boost_quiet_audio(fpath)

            if self.as_zip:
                # Packaging all into .zip archive
                self.status = "zipping"
                self.message = f"Упаковка {len(downloaded_files)} треков в ZIP-архив..."
                self.progress = 98.0

                zip_base = f"{artist} - {playlist_title}"
                zip_path = os.path.join(self.output_dir, f"{zip_base}.zip")

                counter = 1
                while os.path.exists(zip_path):
                    zip_path = os.path.join(self.output_dir, f"{zip_base} ({counter}).zip")
                    counter += 1

                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    for fpath in downloaded_files:
                        arcname = os.path.basename(fpath)
                        zf.write(fpath, arcname=arcname)

                shutil.rmtree(staging_dir, ignore_errors=True)

                total_size = os.path.getsize(zip_path)
                self.progress = 100.0
                self.status = "completed"
                self.result_path = zip_path
                self.result_filename = os.path.basename(zip_path)
                self.result_filesize = format_size(total_size)
                self.message = f"ZIP-архив готов ({len(downloaded_files)} треков, {self.result_filesize})"

                trigger_macos_notification(
                    title="SoundCloud Downloader",
                    subtitle="Архив готов к прослушиванию!",
                    message=f"{self.result_filename} ({len(downloaded_files)} треков) сохранён в Загрузки"
                )
            else:
                # Save as a folder
                final_folder_base = f"{artist} - {playlist_title}"
                final_folder = os.path.join(self.output_dir, final_folder_base)

                counter = 1
                while os.path.exists(final_folder):
                    final_folder = os.path.join(self.output_dir, f"{final_folder_base} ({counter})")
                    counter += 1

                os.rename(staging_dir, final_folder)

                folder_size = sum(os.path.getsize(os.path.join(final_folder, f)) for f in os.listdir(final_folder))
                self.progress = 100.0
                self.status = "completed"
                self.result_path = final_folder
                self.result_filename = os.path.basename(final_folder)
                self.result_filesize = format_size(folder_size)
                self.message = f"Папка с треками готова ({len(downloaded_files)} треков, {self.result_filesize})"

                trigger_macos_notification(
                    title="SoundCloud Downloader",
                    subtitle="Плейлист загружен!",
                    message=f"Папка {self.result_filename} сохранена в Загрузки"
                )

        except Exception as e:
            shutil.rmtree(staging_dir, ignore_errors=True)
            raise e


# In-memory tasks store
active_tasks: Dict[str, DownloadTask] = {}
tasks_history: List[Dict[str, Any]] = []

def create_task(url: str, quality: str = "mp3_320", as_zip: bool = True,
                output_dir: Optional[str] = None,
                selected_tracks: Optional[List[int]] = None,
                embed_artwork: bool = True, embed_metadata: bool = True,
                normalize_quiet: bool = True) -> DownloadTask:
    task_id = f"task_{int(time.time()*1000)}"
    task = DownloadTask(
        task_id=task_id,
        url=url,
        quality=quality,
        as_zip=as_zip,
        output_dir=output_dir,
        selected_tracks=selected_tracks,
        embed_artwork=embed_artwork,
        embed_metadata=embed_metadata,
        normalize_quiet=normalize_quiet
    )
    active_tasks[task_id] = task
    task.start()
    return task

def get_task(task_id: str) -> Optional[DownloadTask]:
    return active_tasks.get(task_id)
