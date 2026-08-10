import re

with open("src/downloader/yt_handler.py", "r") as f:
    content = f.read()

# Refactor fetch_playlist_async
new_fetch = """def fetch_playlist_async(url, on_success, on_error):
    def _run():
        try:
            videos = []
            browsers = ["chrome", "firefox", "edge", "brave", "opera", ""]
            
            for browser in browsers:
                cmd = [
                    "yt-dlp",
                    "--flat-playlist",
                    "--print", "%(id)s|||%(title)s",
                    "--no-warnings",
                    "--no-interactive"
                ]
                if browser:
                    cmd.extend(["--cookies-from-browser", browser])
                cmd.append(url)
                
                p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                stdout, stderr = p.communicate()
                
                for line in stdout.strip().splitlines():
                    if "|||" in line:
                        vid_id, title = line.split("|||", 1)
                        videos.append((vid_id.strip(), title.strip()))
                        
                if videos:
                    break
                    
            on_success(videos)
        except Exception as e:
            on_error(str(e))
            
    threading.Thread(target=_run, daemon=True).start()"""

content = re.sub(r'def fetch_playlist_async\(.*?(?=\ndef download_videos_async)', new_fetch + '\n\n', content, flags=re.DOTALL)

# Refactor download_videos_async
new_dl = """def download_videos_async(video_ids, out_dir, fmt, on_log, on_done, on_error):
    def _run():
        is_mp3 = "MP3" in fmt
        urls = [f"https://www.youtube.com/watch?v={vid}" for vid in video_ids]
        browsers = ["chrome", "firefox", "edge", "brave", "opera", "vivaldi", ""]

        try:
            for browser in browsers:
                if is_mp3:
                    cmd = [
                        "yt-dlp",
                        "-f", "bestaudio[ext=m4a]/bestaudio/best",
                        "--extract-audio",
                        "--audio-format", "mp3",
                        "--audio-quality", "0",
                        "--extractor-args", "youtube:player_client=android_vr",
                        "--ignore-errors",
                        "--no-warnings",
                        "--no-overwrites",
                        "--no-interactive",
                        "--sleep-interval", "2",
                        "--max-sleep-interval", "5",
                    ]
                else:
                    cmd = [
                        "yt-dlp",
                        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
                        "--merge-output-format", "mp4",
                        "--extractor-args", "youtube:player_client=android_vr",
                        "--ignore-errors",
                        "--no-warnings",
                        "--no-overwrites",
                        "--no-interactive",
                        "--sleep-interval", "2",
                        "--max-sleep-interval", "5",
                    ]
                
                if browser:
                    cmd.extend(["--cookies-from-browser", browser])
                
                cmd.extend(["-o", os.path.join(out_dir, "%(title)s.%(ext)s")])
                cmd.extend(urls)
                
                b_name = browser if browser else 'Sin cookies'
                on_log(f"\\nIniciando descarga (Navegador: {b_name})...")
                
                p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
                for line in p.stdout:
                    on_log(line.strip())
                p.wait()
                
                if p.returncode == 0:
                    on_log(f"\\n✅ ¡Descarga completada exitosamente!")
                    break
                else:
                    on_log(f"\\n⚠ Hubo errores con {b_name}. Intentando alternativa...")

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
                    on_log(f"🧹 Se eliminaron {cleaned} archivo(s) temporales incompletos.")

            mp3_count = sum(1 for f in os.listdir(out_dir) if f.endswith('.mp3')) if is_mp3 else 0
            mp4_count = sum(1 for f in os.listdir(out_dir) if f.endswith('.mp4')) if not is_mp3 else 0
            ext = 'mp3' if is_mp3 else 'mp4'
            count = mp3_count if is_mp3 else mp4_count
            
            on_done(count, ext)

        except Exception as e:
            on_error(str(e))

    threading.Thread(target=_run, daemon=True).start()"""

content = re.sub(r'def download_videos_async\(.*', new_dl, content, flags=re.DOTALL)

with open("src/downloader/yt_handler.py", "w") as f:
    f.write(content)

