import flet as ft
import os

class DownloadControls(ft.Column):
    def __init__(self, on_download):
        super().__init__(expand=False)
        self.on_download = on_download
        
        self.file_picker = ft.FilePicker()
        
        self.out_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
        self.dir_label = ft.Text(f"Carpeta: {self.out_dir}", expand=True)
        
        self.dir_btn = ft.ElevatedButton(
            "Seleccionar Carpeta",
            icon=ft.icons.Icons.FOLDER,
            on_click=self.handle_select_dir
        )
        
        self.fmt_dropdown = ft.Dropdown(
            options=[ft.dropdown.Option("MP3"), ft.dropdown.Option("MP4")],
            value="MP3",
            width=100
        )
        
        self.download_btn = ft.ElevatedButton(
            "Descargar Seleccionados",
            icon=ft.icons.Icons.DOWNLOAD,
            on_click=self.handle_download,
            bgcolor="green",
            color="white"
        )
        
        self.log_view = ft.ListView(auto_scroll=True, height=150)
        
        self.controls = [
            ft.Row([self.dir_btn, self.dir_label], spacing=15),
            ft.Row([self.fmt_dropdown, self.download_btn], spacing=15, alignment=ft.MainAxisAlignment.START),
            ft.Text("Logs:", weight=ft.FontWeight.BOLD),
            ft.Container(
                content=self.log_view,
                bgcolor="#1E1E1E",
                border_radius=5,
                padding=10
            )
        ]

    async def handle_select_dir(self, e):
        path = await self.file_picker.get_directory_path()
        if path:
            self.out_dir = path
            self.dir_label.value = f"Carpeta: {self.out_dir}"
            
    def handle_download(self, e):
        self.download_btn.disabled = True
        fmt = self.fmt_dropdown.value
        self.on_download(self.out_dir, fmt)
        
    def append_log(self, text):
        self.log_view.controls.append(ft.Text(text))
        
    def set_loading(self, is_loading):
        self.download_btn.disabled = is_loading
