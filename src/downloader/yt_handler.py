import subprocess
import threading
import os
import sys


def _run_strategies_fetch(url):
    """Fetch playlist/video entries. Returns list of (vid_id, title)."""
    strategies = [
        {"player": "android_vr", "browser": None},
        {"player": None, "browser": "chrome"},
        {"player": None, "browser": "firefox"},
        {"player": None, "browser": "edge"},
        {"player": None, "browser": "brave"},
        {"player": None, "browser": "opera"},
        {"player": None, "browser": "vivaldi"},
        {"player": None, "browser": None},
    ]
    for strat in strategies:
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--flat-playlist",
            "--print", "%(id)s|||%(title)s",
            "--no-warnings",
            "--yes-playlist",
        ]
        if strat["player"]:
            cmd.extend(["--extractor-args", f"youtube:player_client={strat['player']}"])
        if strat["browser"]:
            cmd.extend(["--cookies-from-browser", strat["browser"]])
        cmd.append(url)

        p = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            text=True,
        )
        stdout, _ = p.communicate()

        videos = []
        for line in stdout.strip().splitlines():
            if "|||" in line:
                vid_id, title = line.split("|||", 1)
                videos.append((vid_id.strip(), title.strip()))

        if videos:
            return videos

    return []


def fetch_playlist_sync(url):
    """Synchronous fetch — call from a background thread."""
    return _run_strategies_fetch(url)


def fetch_playlist_async(url, on_success, on_error):
    """Legacy async wrapper kept for compatibility."""
    def _run():
        try:
            on_success(_run_strategies_fetch(url))
        except Exception as e:
            on_error(str(e))
    threading.Thread(target=_run, daemon=True).start()


def download_videos_sync(video_ids, out_dir, fmt, on_log):
    """
    Synchronous download — call from a background thread.
    Calls on_log(msg) for each output line.
    Returns (count, ext).
    """
    is_mp3 = "MP3" in fmt
    urls = [f"https://www.youtube.com/watch?v={vid}" for vid in video_ids]

    strategies = [
        {"player": "android_vr", "browser": None},
        {"player": None, "browser": "chrome"},
        {"player": None, "browser": "firefox"},
        {"player": None, "browser": "edge"},
        {"player": None, "browser": "brave"},
        {"player": None, "browser": "opera"},
        {"player": None, "browser": "vivaldi"},
        {"player": None, "browser": None},
    ]

    for strat in strategies:
        b_name = strat["player"] or strat["browser"] or "sin cookies"
        on_log(f"\nIniciando descarga (Estrategia: {b_name})...")

        if is_mp3:
            cmd = [
                sys.executable, "-m", "yt_dlp",
                "-f", "bestaudio/best",
                "--extract-audio",
                "--audio-format", "mp3",
                "--audio-quality", "0",
                "--ignore-errors",
                "--no-warnings",
                "--no-overwrites",
                "--sleep-interval", "1",
                "--max-sleep-interval", "3",
            ]
        else:
            cmd = [
                sys.executable, "-m", "yt_dlp",
                "-f", "bestvideo+bestaudio/best",
                "--merge-output-format", "mp4",
                "--ignore-errors",
                "--no-warnings",
                "--no-overwrites",
                "--sleep-interval", "1",
                "--max-sleep-interval", "3",
            ]

        if strat["player"]:
            cmd.extend(["--extractor-args", f"youtube:player_client={strat['player']}"])
        if strat["browser"]:
            cmd.extend(["--cookies-from-browser", strat["browser"]])

        cmd.extend(["-o", os.path.join(out_dir, "%(title)s.%(ext)s")])
        cmd.extend(urls)

        p = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
        for line in p.stdout:
            on_log(line.strip())
        p.wait()

        if p.returncode == 0:
            on_log("\n✅ ¡Descarga completada exitosamente!")
            break
        else:
            on_log(f"\n⚠ Falló con '{b_name}'. Intentando siguiente estrategia...")

    # Limpiar archivos temporales
    if is_mp3:
        cleaned = 0
        for fname in os.listdir(out_dir):
            if fname.endswith(('.m4a', '.webm', '.part')):
                try:
                    os.remove(os.path.join(out_dir, fname))
                    cleaned += 1
                except Exception:
                    pass
        if cleaned > 0:
            on_log(f"🧹 Se eliminaron {cleaned} archivo(s) temporales.")

    mp3_count = sum(1 for f in os.listdir(out_dir) if f.endswith('.mp3')) if is_mp3 else 0
    mp4_count = sum(1 for f in os.listdir(out_dir) if f.endswith('.mp4')) if not is_mp3 else 0
    ext   = 'mp3' if is_mp3 else 'mp4'
    count = mp3_count if is_mp3 else mp4_count
    return count, ext


def download_videos_async(video_ids, out_dir, fmt, on_log, on_done, on_error):
    """Legacy async wrapper kept for compatibility."""
    def _run():
        try:
            count, ext = download_videos_sync(video_ids, out_dir, fmt, on_log)
            on_done(count, ext)
        except Exception as e:
            on_error(str(e))
    threading.Thread(target=_run, daemon=True).start()
