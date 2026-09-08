import flet as ft


class SearchBar(ft.Row):
    def __init__(self, on_search, on_notify=None):
        super().__init__()
        self.on_search = on_search
        self.on_notify = on_notify
        self.on_cancel = None   # inyectado desde app.py

        self.url_field = ft.TextField(
            hint_text="Pega el enlace de YouTube aquí...",
            expand=True,
            filled=True,
            bgcolor="#1E1E1E",
            border_radius=20,
            border_color="transparent",
            focused_border_color="blue",
            on_submit=self.handle_search,
            suffix=ft.IconButton(
                icon=ft.icons.Icons.CLOSE,
                tooltip="Limpiar",
                on_click=self.clear_url,
                mouse_cursor=ft.MouseCursor.CLICK,
            ),
        )

        self.search_btn = ft.ElevatedButton(
            "Buscar Videos",
            icon=ft.icons.Icons.SEARCH,
            on_click=self.handle_search,
            style=ft.ButtonStyle(mouse_cursor=ft.MouseCursor.CLICK),
        )

        self.cancel_btn = ft.ElevatedButton(
            "Cancelar",
            icon=ft.icons.Icons.CANCEL,
            on_click=self.handle_cancel,
            bgcolor="#b91c1c",
            color="white",
            visible=False,
            style=ft.ButtonStyle(mouse_cursor=ft.MouseCursor.CLICK),
        )

        self.progress = ft.ProgressRing(width=20, height=20, visible=False, color="blue")

        self.controls = [self.url_field, self.search_btn, self.cancel_btn, self.progress]
        self.alignment = ft.MainAxisAlignment.SPACE_BETWEEN
        self.vertical_alignment = ft.CrossAxisAlignment.CENTER

    def clear_url(self, e):
        self.url_field.value = ""

    def handle_search(self, e):
        url = self.url_field.value.strip()
        if not url:
            if self.on_notify:
                self.on_notify("Por favor ingresa una URL válida.", "error")
            else:
                self.page.show_dialog(ft.SnackBar(ft.Text("Por favor ingresa una URL válida."), bgcolor="#b91c1c"))
            return
        self.set_loading(True)
        self.on_search(url)

    def handle_cancel(self, e):
        if self.on_cancel:
            self.on_cancel()

    def set_loading(self, is_loading):
        self.search_btn.disabled = is_loading
        self.search_btn.visible = not is_loading
        self.cancel_btn.visible = is_loading
        self.progress.visible = is_loading
