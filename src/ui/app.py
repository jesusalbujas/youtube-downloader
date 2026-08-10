import flet as ft
import os
import base64
import asyncio
from ui.icon_data import ICON_B64
from ui.components.search_bar import SearchBar
from ui.components.video_list import VideoList
from ui.components.download_controls import DownloadControls
from downloader.yt_handler import fetch_playlist_sync, download_videos_sync


def main_app(page: ft.Page):
    page.title = "Youtube Downloader"
    page.window.width = 800
    page.window.height = 750
    page.theme_mode = ft.ThemeMode.DARK

    os.makedirs("assets", exist_ok=True)
    icon_path = os.path.join("assets", "icon.png")
    if not os.path.exists(icon_path):
        with open(icon_path, "wb") as f:
            f.write(base64.b64decode(ICON_B64))
    page.window.icon = icon_path

    # ── Instanciar componentes ──────────────────────────────────────────────
    search_bar  = SearchBar(on_search=lambda url: None)   # reemplazado abajo
    video_list  = VideoList()
    dl_controls = DownloadControls(on_download=lambda d, f: None)

    # ── Búsqueda ────────────────────────────────────────────────────────────
    def on_search(url):
        search_bar.set_loading(True)
        page.update()

        def _work():
            try:
                videos = fetch_playlist_sync(url)
            except Exception as exc:
                videos = None
                err = str(exc)
            else:
                err = None

            if err:
                search_bar.set_loading(False)
                dl_controls.append_log(f"Error buscando: {err}")
            else:
                video_list.add_videos(videos)
                search_bar.set_loading(False)
            page.update()

        page.run_thread(_work)

    search_bar.on_search = on_search

    # ── Descarga ────────────────────────────────────────────────────────────
    def on_download(out_dir, fmt):
        selected_ids = video_list.get_selected_video_ids()
        if not selected_ids:
            dl_controls.append_log("⚠ No hay videos seleccionados.")
            dl_controls.set_loading(False)
            page.update()
            return

        dl_controls.append_log(f"Iniciando descarga de {len(selected_ids)} videos...")
        page.update()

        def _work():
            def on_log(msg):
                dl_controls.append_log(msg)
                page.update()

            try:
                count, ext = download_videos_sync(selected_ids, out_dir, fmt, on_log)
                dl_controls.set_loading(False)
                dl_controls.append_log(f"✅ Se completaron {count} descargas en formato {ext}.")
            except Exception as exc:
                dl_controls.set_loading(False)
                dl_controls.append_log(f"Error descargando: {exc}")
            page.update()

        page.run_thread(_work)

    dl_controls.on_download = on_download

    # ── Botones de utilidad ─────────────────────────────────────────────────
    select_all_btn     = ft.TextButton("Marcar Todos",       icon=ft.icons.Icons.CHECK_BOX,              on_click=video_list.select_all)
    deselect_all_btn   = ft.TextButton("Desmarcar Todos",    icon=ft.icons.Icons.CHECK_BOX_OUTLINE_BLANK, on_click=video_list.deselect_all)
    clear_all_btn      = ft.TextButton("Limpiar Lista",      icon=ft.icons.Icons.DELETE_SWEEP,            icon_color="red",    on_click=video_list.clear_all)
    remove_selected_btn= ft.TextButton("Quitar Seleccionados", icon=ft.icons.Icons.DELETE_OUTLINE,        icon_color="orange", on_click=video_list.remove_selected)

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
