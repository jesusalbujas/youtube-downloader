import flet as ft

class VideoItem(ft.Row):
    def __init__(self, vid_id, title, on_toggle, on_delete):
        super().__init__()
        self.vid_id = vid_id
        self.title = title
        
        self.checkbox = ft.Checkbox(
            label=f"{title} ({vid_id})",
            value=True,
            on_change=lambda e: on_toggle(self, e),
            expand=True
        )
        self.delete_btn = ft.IconButton(
            icon=ft.icons.Icons.CLOSE,
            icon_color="red",
            tooltip="Quitar de la lista",
            on_click=lambda e: on_delete(self)
        )
        
        self.controls = [self.checkbox, self.delete_btn]
        self.alignment = ft.MainAxisAlignment.SPACE_BETWEEN
        self.vertical_alignment = ft.CrossAxisAlignment.CENTER
        
    @property
    def selected(self):
        return self.checkbox.value

    @selected.setter
    def selected(self, value):
        self.checkbox.value = value
        self.checkbox.update()

class VideoList(ft.Column):
    def __init__(self):
        super().__init__(scroll=ft.ScrollMode.AUTO, expand=True)
        self.items = []
        self.shift_pressed = False
        self.range_mode = False
        self.last_toggled_index = None
        
    def add_videos(self, videos):
        for vid_id, title in videos:
            # Evitar duplicados exactos si el usuario busca de nuevo lo mismo
            if any(i.vid_id == vid_id for i in self.items):
                continue
            item = VideoItem(
                vid_id=vid_id, 
                title=title, 
                on_toggle=self.handle_toggle, 
                on_delete=self.handle_delete
            )
            self.items.append(item)
            self.controls.append(item)
        pass  # page.update() in app.py handles repaint

    def handle_toggle(self, toggled_item, e):
        try:
            current_index = self.items.index(toggled_item)
        except ValueError:
            return
            
        if (self.shift_pressed or self.range_mode) and self.last_toggled_index is not None:
            start = min(self.last_toggled_index, current_index)
            end = max(self.last_toggled_index, current_index)
            
            target_value = toggled_item.selected
            for i in range(start, end + 1):
                self.items[i].selected = target_value
        
        self.last_toggled_index = current_index

    def handle_delete(self, item):
        if item in self.items:
            self.items.remove(item)
            self.controls.remove(item)
            self.last_toggled_index = None
            self.update()
            
    def select_all(self, e=None):
        for item in self.items:
            item.selected = True
            
    def deselect_all(self, e):
        for item in self.items:
            item.selected = False
            
    def clear_all(self, e=None):
        self.items.clear()
        self.controls.clear()
        self.last_toggled_index = None
        self.update()
        
    def remove_selected(self, e=None):
        to_remove = [item for item in self.items if item.selected]
        for item in to_remove:
            self.items.remove(item)
            self.controls.remove(item)
        self.last_toggled_index = None
        self.update()
            
    def get_selected_video_ids(self):
        return [item.vid_id for item in self.items if item.selected]
