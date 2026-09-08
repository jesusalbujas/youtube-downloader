import flet as ft
import os
import queue
import time


class DownloadControls(ft.Column):
    def __init__(self, on_download, on_notify=None):
        super().__init__(expand=False)
        self.on_download = on_download
        self.on_notify = on_notify

        # Cola thread-safe para logs
        self._log_queue = queue.Queue()
        self._progress_queue = queue.Queue()
        self._download_total = 0
        self._download_processed = 0
        self._download_created = 0
        self._download_started_at = None
        self._download_active = False
        self._last_elapsed_second = -1

        self.file_picker = ft.FilePicker()
        self.out_dir = os.path.join(os.path.expanduser("~"), "Downloads")

        self.dir_field = ft.TextField(
            value=self.out_dir,
            expand=True,
            hint_text="Ruta de descarga…",
            filled=True,
            bgcolor="#1E1E1E",
            border_radius=10,
            border_color="transparent",
            focused_border_color="blue",
            on_change=self._on_dir_field_change,
        )

        self.dir_btn = ft.ElevatedButton(
            "Seleccionar Carpeta",
            icon=ft.icons.Icons.FOLDER,
            on_click=self.handle_select_dir,
            style=ft.ButtonStyle(mouse_cursor=ft.MouseCursor.CLICK),
        )

        self.fmt_dropdown = ft.Dropdown(
            options=[ft.dropdown.Option("MP3"), ft.dropdown.Option("MP4")],
            value="MP3",
            width=100,
        )

        self.download_btn = ft.ElevatedButton(
            "Descargar Seleccionados",
            icon=ft.icons.Icons.DOWNLOAD,
            on_click=self.handle_download,
            bgcolor="green",
            color="white",
            style=ft.ButtonStyle(mouse_cursor=ft.MouseCursor.CLICK),
        )

        self.download_status = ft.Text("Listo para descargar.", color="#9ca3af", size=12)
        self.download_progress = ft.ProgressBar(value=0, color="#22c55e", bgcolor="#374151")

        self._log_height = 180
        self._log_lines = []
        # Un único Text permite seleccionar de forma continua varias líneas.
        # Con un Text por línea, Flutter limita la selección a cada control.
        self.log_text = ft.Text(
            "",
            selectable=True,
            enable_interactive_selection=True,
            show_selection_cursor=True,
            size=12,
        )
        self.log_view = ft.ListView([self.log_text], auto_scroll=True, expand=True)

        self._log_container = ft.Container(
            content=ft.SelectionArea(content=self.log_view),
            bgcolor="#0d1117",
            border_radius=5,
            padding=10,
            height=self._log_height,
        )

        # Barra de resize — mouse_cursor va en GestureDetector, no en Container
        self._resize_bar = ft.GestureDetector(
            mouse_cursor=ft.MouseCursor.RESIZE_UP_DOWN,
            content=ft.Container(
                content=ft.Row([
                    ft.Icon(ft.icons.Icons.DRAG_HANDLE, color="#555", size=16),
                    ft.Text(
                        "Logs — arrastra hacia arriba para ampliar  ·  selecciona para copiar",
                        color="#555", size=11,
                    ),
                ], alignment=ft.MainAxisAlignment.CENTER),
                bgcolor="#1a1a2e",
                border_radius=5,
                padding=5,
            ),
            on_pan_start=self._on_drag_start,
            on_pan_update=self._on_drag_update,
        )

        self.controls = [
            ft.Row([self.dir_btn, self.dir_field], spacing=10),
            ft.Row(
                [self.fmt_dropdown, self.download_btn],
                spacing=15,
                alignment=ft.MainAxisAlignment.START,
            ),
            self.download_status,
            self.download_progress,
            self._resize_bar,
            self._log_container,
        ]

    # ── Resize ──────────────────────────────────────────────────────────────
    def _on_drag_start(self, e: ft.DragStartEvent):
        # El asa está sobre el panel: al subir se amplía hacia arriba.
        pass

    def _on_drag_update(self, e: ft.DragUpdateEvent):
        # local_delta.y es incremental. Al estar el asa encima del panel,
        # su signo se invierte para que subir = ampliar y bajar = reducir.
        if e.local_delta is not None:
            self._log_height = max(80, self._log_height - e.local_delta.y)
            self._log_container.height = self._log_height
            self.page.update()

    # ── Dir picker ──────────────────────────────────────────────────────────
    def _on_dir_field_change(self, e):
        typed = e.control.value.strip()
        if typed:
            self.out_dir = typed

    async def handle_select_dir(self, e):
        try:
            path = await self.file_picker.get_directory_path()
            if path:
                if "://" in path or path.startswith("mtp:"):
                    self._show_mtp_warning()
                    return
                self.out_dir = path
                self.dir_field.value = path
                self.page.update()
        except RuntimeError:
            self._show_mtp_warning()

    def _show_mtp_warning(self):
        message = (
            "Esa ubicación no es compatible (MTP/red). "
            "Escribe una ruta local en el campo de texto."
        )
        if self.on_notify:
            self.on_notify(message, "warning")
        else:
            self.page.show_dialog(ft.SnackBar(ft.Text(message), bgcolor="#b45309", duration=5000))
            self.page.update()

    # ── Download ────────────────────────────────────────────────────────────
    def handle_download(self, e):
        self.download_btn.disabled = True
        fmt = self.fmt_dropdown.value
        typed = self.dir_field.value.strip()
        if typed:
            self.out_dir = typed
        self.on_download(self.out_dir, fmt)

    # ── Progreso de descarga (thread-safe) ──────────────────────────────────
    @staticmethod
    def _format_elapsed(seconds):
        seconds = max(0, int(seconds))
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}" if hours else f"{minutes:02}:{seconds:02}"

    def _render_download_progress(self, elapsed=None):
        if self._download_started_at is None:
            elapsed = 0
        elif elapsed is None:
            elapsed = time.monotonic() - self._download_started_at

        total = self._download_total
        processed = self._download_processed
        self.download_progress.value = processed / total if total else 0
        progress = f"{processed}/{total}"
        created = f" · {self._download_created} nueva(s)" if self._download_created else ""
        self.download_status.value = (
            f"Descargando {total} videos ({progress}) · {self._format_elapsed(elapsed)}{created}"
        )

    def start_download(self, total):
        self._download_total = total
        self._download_processed = 0
        self._download_created = 0
        self._download_started_at = time.monotonic()
        self._download_active = True
        self._last_elapsed_second = -1
        self._render_download_progress(0)

    def enqueue_download_progress(self, processed, total, created, elapsed):
        self._progress_queue.put(("progress", processed, total, created, elapsed))

    def enqueue_download_finished(self, created, cancelled=False):
        self._progress_queue.put(("finished", created, cancelled, time.monotonic()))

    # ── Log (thread-safe via queue) ──────────────────────────────────────────
    def enqueue_log(self, text):
        if text and text.strip():
            self._log_queue.put(text.strip())

    def flush_log(self):
        """Drena logs y progreso encolados desde los hilos de descarga."""
        changed = False
        while True:
            try:
                msg = self._log_queue.get_nowait()
                self._log_lines.append(msg)
                changed = True
            except queue.Empty:
                break
        if changed:
            # Evita que una sesión muy extensa acumule memoria sin límite.
            self._log_lines = self._log_lines[-1500:]
            self.log_text.value = "\n".join(self._log_lines)

        while True:
            try:
                event = self._progress_queue.get_nowait()
            except queue.Empty:
                break
            changed = True
            if event[0] == "progress":
                _, processed, total, created, elapsed = event
                self._download_processed = processed
                self._download_total = total
                self._download_created = created
                # Conserva el reloj continuo entre actualizaciones de los hilos.
                self._download_started_at = time.monotonic() - elapsed
                self._render_download_progress(elapsed)
            else:
                _, created, cancelled, finished_at = event
                elapsed = (finished_at - self._download_started_at) if self._download_started_at else 0
                self._download_active = False
                self._download_created = created
                self._download_processed = self._download_total
                self.download_progress.value = 1 if self._download_total else 0
                state = "Descarga detenida" if cancelled else "Descarga finalizada"
                self.download_status.value = (
                    f"{state}: {self._download_processed}/{self._download_total} · "
                    f"{created} nueva(s) · {self._format_elapsed(elapsed)}"
                )

        if self._download_active and self._download_started_at:
            elapsed_seconds = int(time.monotonic() - self._download_started_at)
            if elapsed_seconds != self._last_elapsed_second:
                self._last_elapsed_second = elapsed_seconds
                self._render_download_progress(elapsed_seconds)
                changed = True
        return changed

    def append_log(self, text):
        self.enqueue_log(text)

    def set_loading(self, is_loading):
        self.download_btn.disabled = is_loading
