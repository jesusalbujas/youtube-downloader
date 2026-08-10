import flet as ft

class SearchBar(ft.Row):
    def __init__(self, on_search):
        super().__init__()
        self.on_search = on_search
        
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
                on_click=self.clear_url
            )
        )
        
        self.search_btn = ft.ElevatedButton(
            "Buscar Videos",
            icon=ft.icons.Icons.SEARCH,
            on_click=self.handle_search
        )
        
        self.progress = ft.ProgressRing(width=20, height=20, visible=False, color="blue")
        
        self.controls = [self.url_field, self.search_btn, self.progress]
        self.alignment = ft.MainAxisAlignment.SPACE_BETWEEN
        self.vertical_alignment = ft.CrossAxisAlignment.CENTER

    def clear_url(self, e):
        self.url_field.value = ""

    def handle_search(self, e):
        url = self.url_field.value.strip()
        if not url:
            self.page.open(ft.SnackBar(ft.Text("⚠️ Por favor ingresa una URL válida", color="white"), bgcolor="red"))
            return
            
        self.set_loading(True)
        self.on_search(url)
            
    def set_loading(self, is_loading):
        self.search_btn.disabled = is_loading
        self.progress.visible = is_loading
        if is_loading:
            self.search_btn.text = "Buscando..."
            self.search_btn.icon = ft.icons.Icons.HOURGLASS_EMPTY
        else:
            self.search_btn.text = "Buscar Videos"
            self.search_btn.icon = ft.icons.Icons.SEARCH
        
        
