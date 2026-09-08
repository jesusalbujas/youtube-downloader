import flet as ft
import os
import base64
import json
import threading
import queue
from ui.icon_data import ICON_B64
from ui.components.search_bar import SearchBar
from ui.components.video_list import VideoList
from ui.components.download_controls import DownloadControls
from downloader.yt_handler import fetch_playlist_sync, download_videos_sync

SESSION_FILE = os.path.join(os.path.expanduser("~"), ".yt_downloader_session.json")


def save_session(video_list: VideoList):
    try:
        data = [{"id": item.vid_id, "title": item.title} for item in video_list.items]
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def load_session() -> list:
    try:
        if os.path.exists(SESSION_FILE):
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [(item["id"], item["title"]) for item in data]
    except Exception:
        pass
    return []


def main_app(page: ft.Page):
    page.title = "Youtube Downloader"
    page.window.width = 800
    page.window.height = 750
    page.theme_mode = ft.ThemeMode.DARK

    def show_toast(message: str, level: str = "info", action=None, on_action=None, duration=3500):
        """Muestra un aviso breve y consistente para acciones de la interfaz."""
        colors = {
            "success": "#15803d",
            "error": "#b91c1c",
            "warning": "#b45309",
            "info": "#1d4ed8",
        }
        icons = {
            "success": "✅",
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️",
        }
        toast = ft.SnackBar(
            content=ft.Text(f"{icons.get(level, 'ℹ️')} {message}", color="white"),
            bgcolor=colors.get(level, colors["info"]),
            behavior=ft.SnackBarBehavior.FLOATING,
            duration=duration,
            show_close_icon=True,
            action=action,
            on_action=on_action,
        )
        page.show_dialog(toast)
        return toast

    def dismiss_toast(toast):
        if toast and toast.open:
            toast.open = False
            toast.update()

    os.makedirs("assets", exist_ok=True)
    icon_path = os.path.join("assets", "icon.png")
    if not os.path.exists(icon_path):
        with open(icon_path, "wb") as f:
            f.write(base64.b64decode(ICON_B64))
    page.window.icon = icon_path

    # ── Instanciar componentes ──────────────────────────────────────────────
    search_bar  = SearchBar(on_search=lambda url: None, on_notify=show_toast)
    video_list  = VideoList()
    dl_controls = DownloadControls(on_download=lambda d, f: None, on_notify=show_toast)
    _downloaded_video_ids = queue.Queue()

    # ── Timer que drena la cola de logs desde el hilo principal ─────────────
    # Esto evita por completo el IndexError: ningún hilo de fondo
    # toca los controls de Flet directamente.
    def _flush_logs_tick():
        changed = dl_controls.flush_log()
        session_changed = False
        while True:
            try:
                video_id = _downloaded_video_ids.get_nowait()
            except queue.Empty:
                break
            if video_list.remove_by_video_id(video_id):
                changed = True
                session_changed = True
        if session_changed:
            save_session(video_list)
        if changed:
            page.update()

    page.on_idle = _flush_logs_tick   # se llama cada vez que la UI está libre

    # Además, un timer de 200ms garantiza la actualización aunque no haya eventos
    _stop_timer = threading.Event()
    def _log_timer():
        while not _stop_timer.wait(0.2):
            try:
                _flush_logs_tick()
            except Exception:
                pass
    threading.Thread(target=_log_timer, daemon=True).start()

    # ── Restaurar sesión anterior ───────────────────────────────────────────
    saved = load_session()
    if saved:
        video_list.add_videos(saved)
        dl_controls.append_log(f"♻️ Se restauraron {len(saved)} videos de la sesión anterior.")

    # ── Búsqueda con cancelación ────────────────────────────────────────────
    _cancel_search = threading.Event()

    def on_search(url):
        _cancel_search.clear()
        search_bar.set_loading(True)
        page.update()

        def _work():
            search_error = None
            try:
                videos = fetch_playlist_sync(url, cancel_event=_cancel_search)
            except Exception as exc:
                videos = []
                search_error = exc

            if _cancel_search.is_set():
                dl_controls.append_log("⏹ Búsqueda cancelada.")
                show_toast("Búsqueda cancelada.", "info")
            elif search_error:
                dl_controls.append_log(f"Error buscando: {search_error}")
                show_toast(f"No se pudo consultar el enlace: {search_error}", "error")
            elif videos:
                video_list.add_videos(videos)
                save_session(video_list)
                dl_controls.append_log(f"✅ Se encontraron {len(videos)} videos.")
                show_toast(f"Se encontraron {len(videos)} videos.", "success")
            else:
                dl_controls.append_log("⚠ No se encontraron videos.")
                show_toast("No se encontraron videos para ese enlace.", "warning")

            search_bar.set_loading(False)
            page.update()

        page.run_thread(_work)

    def on_cancel_search():
        _cancel_search.set()

    search_bar.on_search = on_search
    search_bar.on_cancel = on_cancel_search

    # ── Descarga ────────────────────────────────────────────────────────────
    _cancel_download = threading.Event()
    active_download_toast = None

    def on_cancel_download():
        nonlocal active_download_toast
        if not _cancel_download.is_set():
            _cancel_download.set()
            dismiss_toast(active_download_toast)
            active_download_toast = None
            dl_controls.append_log("⏹ Solicitando detener las descargas...")
            show_toast("Deteniendo las descargas activas...", "warning")

    def on_download(out_dir, fmt):
        nonlocal active_download_toast
        selected_ids = video_list.get_selected_video_ids()
        if not selected_ids:
            dl_controls.append_log("⚠ No hay videos seleccionados.")
            dl_controls.set_loading(False)
            show_toast("Selecciona al menos un video antes de descargar.", "warning")
            page.update()
            return

        _cancel_download.clear()
        dl_controls.start_download(len(selected_ids))
        dl_controls.append_log(f"Iniciando descarga de {len(selected_ids)} videos...")
        active_download_toast = show_toast(
            f"Descargando {len(selected_ids)} video(s)...",
            "info",
            action="Detener",
            on_action=lambda _: on_cancel_download(),
            duration=1_800_000,
        )
        page.update()

        def _work():
            nonlocal active_download_toast
            # on_log solo encola — el timer se encarga de pintar
            def on_log(msg):
                dl_controls.enqueue_log(msg)

            def on_progress(processed, total, created, elapsed):
                dl_controls.enqueue_download_progress(processed, total, created, elapsed)

            def on_item_downloaded(video_id):
                _downloaded_video_ids.put(video_id)

            try:
                count, ext = download_videos_sync(
                    selected_ids,
                    out_dir,
                    fmt,
                    on_log,
                    cancel_event=_cancel_download,
                    on_progress=on_progress,
                    on_item_downloaded=on_item_downloaded,
                )
                dl_controls.set_loading(False)
                dl_controls.enqueue_download_finished(count, _cancel_download.is_set())
                dismiss_toast(active_download_toast)
                active_download_toast = None
                if _cancel_download.is_set():
                    dl_controls.enqueue_log(f"⏹ Descarga detenida. Se guardaron {count} archivo(s) {ext}.")
                    show_toast(f"Descarga detenida. Se guardaron {count} archivo(s).", "warning")
                else:
                    dl_controls.enqueue_log(f"✅ Se completaron {count} descargas en formato {ext}.")
                if count and not _cancel_download.is_set():
                    show_toast(f"Se descargaron {count} archivo(s) {ext.upper()}.", "success")
                elif not _cancel_download.is_set():
                    show_toast("No se creó un archivo nuevo; revisa el log.", "warning")
            except Exception as exc:
                dl_controls.set_loading(False)
                dl_controls.enqueue_log(f"Error descargando: {exc}")
                show_toast(f"No se pudo completar la descarga: {exc}", "error")
            page.update()

        page.run_thread(_work)

    dl_controls.on_download = on_download

    # ── Botones de utilidad ─────────────────────────────────────────────────
    def _clear_all_and_save(e):
        video_list.clear_all(e)
        save_session(video_list)

    def _remove_selected_and_save(e):
        video_list.remove_selected(e)
        save_session(video_list)

    clickable = ft.ButtonStyle(mouse_cursor=ft.MouseCursor.CLICK)
    select_all_btn      = ft.TextButton("Marcar Todos",         icon=ft.icons.Icons.CHECK_BOX,              on_click=video_list.select_all,       style=clickable)
    deselect_all_btn    = ft.TextButton("Desmarcar Todos",      icon=ft.icons.Icons.CHECK_BOX_OUTLINE_BLANK, on_click=video_list.deselect_all,     style=clickable)
    clear_all_btn       = ft.TextButton("Limpiar Lista",        icon=ft.icons.Icons.DELETE_SWEEP,            icon_color="red",    on_click=_clear_all_and_save,       style=clickable)
    remove_selected_btn = ft.TextButton("Quitar Seleccionados", icon=ft.icons.Icons.DELETE_OUTLINE,          icon_color="orange", on_click=_remove_selected_and_save, style=clickable)

    def on_range_change(e):
        video_list.range_mode = e.control.value

    range_checkbox = ft.Checkbox(label="Modo Rango (Clickea inicio y fin)", value=False, on_change=on_range_change)
    actions_row    = ft.Row([select_all_btn, deselect_all_btn, remove_selected_btn, clear_all_btn, range_checkbox], wrap=True)

    # ── Layout ──────────────────────────────────────────────────────────────
    layout = ft.Column([
        search_bar,
        ft.Divider(),
        ft.Text("Videos Encontrados (Usa Shift + Clic para seleccionar múltiples):", weight=ft.FontWeight.BOLD),
        actions_row,
        ft.Container(
            content=video_list,
            bgcolor="#1E1E1E",
            border_radius=5,
            padding=10,
            expand=True,
        ),
        ft.Divider(),
        dl_controls,
    ], expand=True)

    page.add(layout)

    def page_on_keyboard(e: ft.KeyboardEvent):
        video_list.shift_pressed = e.shift

    page.on_keyboard_event = page_on_keyboard
    page.update()
