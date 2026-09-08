import subprocess
import threading
import os
import sys
import shutil
import select
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


def _run_strategies_fetch(url, cancel_event=None):
    """Fetch playlist/video entries. Returns list of (vid_id, title).
    cancel_event: threading.Event — si se activa, cancela y retorna lo obtenido."""
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
        if cancel_event and cancel_event.is_set():
            return []

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

        # Vigilar cancelación mientras el proceso corre
        if cancel_event:
            while p.poll() is None:
                if cancel_event.is_set():
                    p.terminate()
                    p.wait()
                    return []
                cancel_event.wait(timeout=0.3)

        stdout, _ = p.communicate() if p.poll() is None else (p.stdout.read(), "")

        videos = []
        for line in stdout.strip().splitlines():
            if "|||" in line:
                vid_id, title = line.split("|||", 1)
                videos.append((vid_id.strip(), title.strip()))

        if videos:
            return videos

    return []


def fetch_playlist_sync(url, cancel_event=None):
    """Synchronous fetch — call from a background thread."""
    return _run_strategies_fetch(url, cancel_event)


def fetch_playlist_async(url, on_success, on_error):
    """Legacy async wrapper kept for compatibility."""
    def _run():
        try:
            on_success(_run_strategies_fetch(url))
        except Exception as e:
            on_error(str(e))
    threading.Thread(target=_run, daemon=True).start()


def download_videos_sync(
    video_ids, out_dir, fmt, on_log, cancel_event=None,
    on_progress=None, on_item_downloaded=None,
):
    """
    Synchronous download — call from a background thread.
    Calls on_log(msg) for each output line.
    Returns (count, ext).
    """
    if not shutil.which("ffmpeg"):
        raise RuntimeError("No se encontró FFmpeg. Instálalo para convertir audio e incrustar carátulas/metadatos.")

    os.makedirs(out_dir, exist_ok=True)
    if not os.path.isdir(out_dir):
        raise RuntimeError("La ruta de descarga no es una carpeta válida.")

    is_mp3 = "MP3" in fmt
    ext = "mp3" if is_mp3 else "mp4"
    if not video_ids:
        return 0, ext

    existing_files = {
        name for name in os.listdir(out_dir)
        if name.lower().endswith(f".{ext}")
    }
    started_at = time.monotonic()

    # meta_artist fuerza el autor visible incluso cuando YouTube no expone un
    # campo musical de artista; no reemplaza uno existente si está disponible.
    media_metadata_args = [
        "--embed-metadata",
        "--parse-metadata", "%(artist,uploader,channel,creator|)s:%(meta_artist)s",
        # Elimina etiquetas promocionales comunes del título, tanto del nombre
        # de archivo como de los metadatos. Se restringe a paréntesis/corchetes
        # o a un sufijo separado por guion para no alterar nombres reales.
        # La expresión siempre coincide y conserva el título si no tiene una
        # etiqueta promocional; así yt-dlp no llena el log con falsos avisos
        # de "Did not find ..." para cada canción.
        "--replace-in-metadata", "title",
        r"(?is)^(.*?)(?:\s*(?:[\(\[]\s*(?:official\s+(?:music\s+)?video|video\s+oficial|official\s+audio|audio\s+oficial|official\s+lyrics?(?:\s+video)?|lyrics?\s+oficial(?:\s+video)?|official\s+visuali[sz]er|visuali[sz]er\s+oficial|visuali[sz]er)\s*[\)\]]|[-–—|]\s*(?:official\s+(?:music\s+)?video|video\s+oficial|official\s+audio|audio\s+oficial|official\s+lyrics?(?:\s+video)?|lyrics?\s+oficial(?:\s+video)?|official\s+visuali[sz]er|visuali[sz]er\s+oficial|visuali[sz]er)))?\s*$",
        r"\1",
    ]

    # Android VR sin cookies es la estrategia que históricamente ha sido más
    # estable para esta aplicación. Se conserva el orden original de clientes.
    strategies = [
        # (player_client,  browser,  fmt_audio,                     fmt_video)
        ("android_vr", None,      "140/bestaudio[ext=m4a]/bestaudio", "18/best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best"),
        ("android_vr", None,      "bestaudio/best",                   "bestvideo+bestaudio/best"),
        ("android",    None,      "140/bestaudio[ext=m4a]/bestaudio", "18/best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best"),
        ("android",    None,      "bestaudio/best",                   "bestvideo+bestaudio/best"),
        (None,         "chrome",  "bestaudio/best",                   "bestvideo+bestaudio/best"),
        (None,         "firefox", "bestaudio/best",                   "bestvideo+bestaudio/best"),
        (None,         None,       "bestaudio/best",                   "bestvideo+bestaudio/best"),
    ]
    def download_one(video_id):
        """Descarga un video usando fallbacks sin volver a procesar el lote."""
        url = f"https://www.youtube.com/watch?v={video_id}"
        for player, browser, audio_fmt, video_fmt in strategies:
            if cancel_event and cancel_event.is_set():
                on_log(f"[{video_id}] ⏹ Descarga cancelada.")
                return "cancelled"

            b_name = (player or "default") + (f"+{browser}" if browser else "")
            on_log(f"[{video_id}] Estrategia: {b_name}...")

            if is_mp3:
                cmd = [
                    sys.executable, "-m", "yt_dlp",
                    "-f", audio_fmt,
                    "--extract-audio",
                    "--audio-format", "mp3",
                    "--audio-quality", "0",
                    *media_metadata_args,
                ]
            else:
                cmd = [
                    sys.executable, "-m", "yt_dlp",
                    "-f", video_fmt,
                    "--merge-output-format", "mp4",
                    *media_metadata_args,
                ]

            # Mantener una sola conexión/fragmento reduce la probabilidad de
            # que YouTube invalide los enlaces temporales con HTTP 403.
            cmd.extend([
                "--concurrent-fragments", "1",
                "--retries", "3",
                "--fragment-retries", "3",
                "--extractor-retries", "1",
                "--socket-timeout", "20",
                "--no-playlist",
                "--no-warnings",
                "--no-overwrites",
            ])
            if player:
                cmd.extend(["--extractor-args", f"youtube:player_client={player}"])
            if browser:
                cmd.extend(["--cookies-from-browser", browser])
            cmd.extend(["-o", os.path.join(out_dir, "%(title)s.%(ext)s"), url])

            files_before = {
                name for name in os.listdir(out_dir)
                if name.lower().endswith(f".{ext}")
            }
            p = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                bufsize=1,
            )
            error_count = 0
            cancelled = False

            def record_line(line):
                nonlocal error_count
                stripped = line.strip()
                if "[MetadataParser]" in stripped:
                    return
                if stripped:
                    on_log(f"[{video_id}] {stripped}")
                if "HTTP Error 403" in stripped or "Forbidden" in stripped or "Sign in" in stripped:
                    error_count += 1

            while p.poll() is None:
                if cancel_event and cancel_event.is_set():
                    cancelled = True
                    p.terminate()
                    break
                ready, _, _ = select.select([p.stdout], [], [], 0.2)
                if not ready:
                    continue
                record_line(p.stdout.readline())
            p.wait()
            if not cancelled:
                for line in p.stdout:
                    record_line(line)
            if cancelled:
                on_log(f"[{video_id}] ⏹ Descarga detenida.")
                return "cancelled"
            if p.returncode == 0 and error_count == 0:
                files_after = {
                    name for name in os.listdir(out_dir)
                    if name.lower().endswith(f".{ext}")
                }
                if files_after - files_before:
                    on_log(f"[{video_id}] ✅ Descarga completada.")
                    return "downloaded"
                on_log(f"[{video_id}] ℹ️ Ya existía; no se creó un archivo nuevo.")
                return "skipped"

            reason = f"403 ({error_count})" if error_count else f"código {p.returncode}"
            on_log(f"[{video_id}] ↳ Falló ({reason}); probando alternativa...")
        on_log(f"[{video_id}] ❌ No se pudo descargar con las alternativas disponibles.")
        return "failed"

    worker_count = 1
    on_log(f"Descargando {len(video_ids)} video(s) de forma estable, uno a la vez.")
    successful_jobs = 0
    processed_jobs = 0
    created_jobs = 0
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = {executor.submit(download_one, video_id): video_id for video_id in video_ids}
        for future in as_completed(futures):
            # Propaga fallos inesperados en lugar de ocultarlos tras el resumen.
            outcome = future.result()
            video_id = futures[future]
            processed_jobs += 1
            if outcome in {"downloaded", "skipped"}:
                successful_jobs += 1
            if outcome == "downloaded":
                created_jobs += 1
                if on_item_downloaded:
                    on_item_downloaded(video_id)
            elapsed = time.monotonic() - started_at
            on_log(
                f"⏱ Progreso: {processed_jobs}/{len(video_ids)} · "
                f"{created_jobs} nueva(s) · {int(elapsed // 60):02}:{int(elapsed % 60):02}"
            )
            if on_progress:
                on_progress(processed_jobs, len(video_ids), created_jobs, elapsed)

    if cancel_event and cancel_event.is_set():
        on_log("⏹ Se detuvieron las descargas pendientes.")
    elif successful_jobs == 0:
        on_log(
            "⚠ YouTube rechazó las solicitudes. Abre YouTube en Chrome o Firefox, "
            "inicia sesión y vuelve a intentar; la app usará esa sesión como alternativa."
        )

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

    downloaded_files = {
        name for name in os.listdir(out_dir)
        if name.lower().endswith(f".{ext}") and name not in existing_files
    }
    count = len(downloaded_files)
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
