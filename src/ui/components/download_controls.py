import flet as ft
import os


class DownloadControls(ft.Column):
    def __init__(self, on_download):
        super().__init__(expand=False)
        self.on_download = on_download

        self.file_picker = ft.FilePicker()

        self.out_dir = os.path.join(os.path.expanduser("~"), "Downloads")

        # Campo editable para escribir la ruta manualmente
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
        )

        self.log_view = ft.ListView(auto_scroll=True, height=150)

        self.controls = [
            ft.Row([self.dir_btn, self.dir_field], spacing=10),
            ft.Row(
                [self.fmt_dropdown, self.download_btn],
                spacing=15,
                alignment=ft.MainAxisAlignment.START,
            ),
            ft.Text("Logs:", weight=ft.FontWeight.BOLD),
            ft.Container(
                content=self.log_view,
                bgcolor="#1E1E1E",
                border_radius=5,
                padding=10,
            ),
        ]

    def _on_dir_field_change(self, e):
        """Actualiza la ruta cuando el usuario escribe manualmente."""
        typed = e.control.value.strip()
        if typed:
            self.out_dir = typed

    async def handle_select_dir(self, e):
        try:
            path = await self.file_picker.get_directory_path()
            if path:
                # Rechaza URIs MTP o no-locales (contienen "://" o empiezan con "mtp:")
                if "://" in path or path.startswith("mtp:"):
                    self._show_mtp_warning()
                    return
                self.out_dir = path
                self.dir_field.value = path
                self.page.update()
        except RuntimeError as exc:
            # "Cannot extract a file path from a mtp URI" u otros errores del picker
            self._show_mtp_warning()

    def _show_mtp_warning(self):
        self.page.open(ft.SnackBar(
            ft.Text(
                "⚠️ Esa ubicación no es compatible (MTP/red). "
                "Escribe la ruta local directamente en el campo de texto.",
                color="white",
            ),
            bgcolor="#b45309",
            duration=5000,
        ))
        self.page.update()

    def handle_download(self, e):
        self.download_btn.disabled = True
        fmt = self.fmt_dropdown.value
        # Sincroniza por si el usuario editó el campo a mano
        typed = self.dir_field.value.strip()
        if typed:
            self.out_dir = typed
        self.on_download(self.out_dir, fmt)

    def append_log(self, text):
        self.log_view.controls.append(ft.Text(text))

    def set_loading(self, is_loading):
        self.download_btn.disabled = is_loading
