import subprocess
import threading
import os

def fetch_playlist_async(url, on_success, on_error):
    def _run():
        cmd = [
            "yt-dlp",
            "--flat-playlist",
            "--print", "%(id)s|||%(title)s",
            "--no-warnings",
            "--cookies-from-browser", "firefox",
            url
        ]
        try:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True)
            stdout, stderr = p.communicate()
            videos = []
            for line in stdout.strip().splitlines():
                if "|||" in line:
                    vid_id, title = line.split("|||", 1)
                    videos.append((vid_id.strip(), title.strip()))

            if not videos:
                # Intento sin cookies de navegador
                cmd2 = [
                    "yt-dlp", "--flat-playlist",
                    "--print", "%(id)s|||%(title)s",
                    "--no-warnings",
                    url
                ]
                p2 = subprocess.Popen(cmd2, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, text=True)
                stdout2, _ = p2.communicate()
                for line in stdout2.strip().splitlines():
                    if "|||" in line:
                        vid_id, title = line.split("|||", 1)
                        videos.append((vid_id.strip(), title.strip()))

            on_success(videos)
        except Exception as e:
            on_error(str(e))
            
    threading.Thread(target=_run, daemon=True).start()


def download_videos_async(video_ids, out_dir, fmt, on_log, on_done, on_error):
    def _run():
        is_mp3 = "MP3" in fmt
        urls = [f"https://www.youtube.com/watch?v={vid}" for vid in video_ids]

        if is_mp3:
            cmd = [
                "yt-dlp",
                "-f", "bestaudio[ext=m4a]/bestaudio/best",
                "--extract-audio",
                "--audio-format", "mp3",
                "--audio-quality", "0",
                "--extractor-args", "youtube:player_client=android_vr",
                "--cookies-from-browser", "firefox",
                "--ignore-errors",
                "--no-warnings",
                "--no-overwrites",
                "--sleep-interval", "2",
                "--max-sleep-interval", "5",
                "-o", os.path.join(out_dir, "%(title)s.%(ext)s"),
            ] + urls
        else:
            cmd = [
                "yt-dlp",
                "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
                "--merge-output-format", "mp4",
                "--extractor-args", "youtube:player_client=android_vr",
                "--cookies-from-browser", "firefox",
                "--ignore-errors",
                "--no-warnings",
                "--no-overwrites",
                "--sleep-interval", "2",
                "--max-sleep-interval", "5",
                "-o", os.path.join(out_dir, "%(title)s.%(ext)s"),
            ] + urls

        try:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, text=True, bufsize=1)
            for line in p.stdout:
                on_log(line.strip())
            p.wait()
            
            if p.returncode == 0:
                on_log("\n✅ ¡Descarga completada exitosamente!")
            else:
                on_log(f"⚠ Terminó con código {p.returncode}. Algunos videos pueden haber fallado.")

            # Limpiar archivos temporales de audio si se convirtió a MP3
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
                    on_log(f"🧹 Se eliminaron {cleaned} archivo(s) temporales incompletos (.m4a/.webm).")

            mp3_count = sum(1 for f in os.listdir(out_dir) if f.endswith('.mp3')) if is_mp3 else 0
            mp4_count = sum(1 for f in os.listdir(out_dir) if f.endswith('.mp4')) if not is_mp3 else 0
            ext = 'mp3' if is_mp3 else 'mp4'
            count = mp3_count if is_mp3 else mp4_count
            
            on_done(count, ext)

        except Exception as e:
            on_error(str(e))

    threading.Thread(target=_run, daemon=True).start()
