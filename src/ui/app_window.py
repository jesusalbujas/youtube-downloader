import customtkinter as ctk
from tkinter import messagebox
import subprocess
import threading
import os
from downloader.yt_handler import fetch_playlist_async, download_videos_async

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class YoutubeDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("YouTube Downloader")
        self.geometry("820x750")
        self.resizable(True, True)
        self.grid_columnconfigure(0, weight=1)
        # row 2 (video list) can expand if window is resized
        self.grid_rowconfigure(2, weight=1)

        self.video_vars = {}  # {video_id: (BooleanVar, title)}

        self._build_ui()

    def _build_ui(self):
        # ── Title ──────────────────────────────────────────────────────────
        ctk.CTkLabel(self, text="YouTube Video & Playlist Downloader",
                     font=ctk.CTkFont(size=22, weight="bold")).grid(
            row=0, column=0, padx=20, pady=(20, 10), sticky="ew")

        # ── URL + Buscar ───────────────────────────────────────────────────
        url_frame = ctk.CTkFrame(self, fg_color="transparent")
        url_frame.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        url_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(url_frame, text="URL del Video / Lista de Reproducción:").grid(
            row=0, column=0, columnspan=2, sticky="w")

        self.url_entry = ctk.CTkEntry(url_frame,
                                      placeholder_text="https://www.youtube.com/watch?v=...",
                                      height=35)
        self.url_entry.grid(row=1, column=0, padx=(0, 10), pady=5, sticky="ew")

        self.fetch_btn = ctk.CTkButton(url_frame, text="🔍 Buscar Videos",
                                       command=self.start_fetch,
                                       height=35, width=150,
                                       fg_color="#1565C0", hover_color="#0D47A1")
        self.fetch_btn.grid(row=1, column=1)

        # ── Video List ─────────────────────────────────────────────────────
        list_frame = ctk.CTkFrame(self)
        list_frame.grid(row=2, column=0, padx=20, pady=5, sticky="ew")
        list_frame.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(list_frame, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        header.grid_columnconfigure(0, weight=1)

        self.list_label = ctk.CTkLabel(header, text="Videos encontrados:",
                                       font=ctk.CTkFont(size=13))
        self.list_label.grid(row=0, column=0, sticky="w")

        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.grid(row=0, column=1, sticky="e")
        ctk.CTkButton(btn_frame, text="✅ Todos", command=self.select_all,
                      width=80, height=28, fg_color="#37474F",
                      hover_color="#263238").pack(side="left", padx=2)
        ctk.CTkButton(btn_frame, text="❌ Ninguno", command=self.deselect_all,
                      width=80, height=28, fg_color="#37474F",
                      hover_color="#263238").pack(side="left", padx=2)

        self.scroll = ctk.CTkScrollableFrame(list_frame, height=160)
        self.scroll.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.scroll.grid_columnconfigure(0, weight=1)

        self.no_videos_label = ctk.CTkLabel(
            self.scroll,
            text="Ingresa una URL y haz clic en 🔍 Buscar Videos",
            text_color="gray")
        self.no_videos_label.grid(row=0, column=0, padx=10, pady=20)

        # ── Carpeta destino ────────────────────────────────────────────────
        dest_frame = ctk.CTkFrame(self, fg_color="transparent")
        dest_frame.grid(row=3, column=0, padx=20, pady=5, sticky="ew")
        dest_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(dest_frame, text="Guardar en:").grid(
            row=0, column=0, padx=(0, 10), sticky="w")

        self.download_dir = ctk.StringVar(
            value=os.path.join(os.path.expanduser("~"), "Downloads"))

        self.dir_entry = ctk.CTkEntry(dest_frame,
                                      textvariable=self.download_dir,
                                      state="readonly", height=35)
        self.dir_entry.grid(row=0, column=1, padx=(0, 10), sticky="ew")

        ctk.CTkButton(dest_frame, text="📂 Cambiar carpeta",
                      command=self.choose_directory,
                      fg_color="#455A64", hover_color="#263238",
                      height=35, width=150).grid(row=0, column=2)

        # ── Formato ─────────────────────────────────────────────────────────
        fmt_frame = ctk.CTkFrame(self, fg_color="transparent")
        fmt_frame.grid(row=4, column=0, padx=20, pady=(0, 5), sticky="ew")
        fmt_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(fmt_frame, text="Formato:").grid(
            row=0, column=0, padx=(0, 15), sticky="w")

        self.format_var = ctk.StringVar(value="MP4")
        ctk.CTkSegmentedButton(
            fmt_frame,
            values=["MP4 🎥", "MP3 🎵"],
            variable=self.format_var,
            width=200
        ).grid(row=0, column=1, sticky="w")

        # ── Descargar ──────────────────────────────────────────────────
        self.download_btn = ctk.CTkButton(
            self, text="⬇  Descargar seleccionados",
            command=self.start_download,
            font=ctk.CTkFont(size=16, weight="bold"),
            height=45, fg_color="#2E7D32", hover_color="#1B5E20",
            state="disabled")
        self.download_btn.grid(row=5, column=0, padx=20, pady=10, sticky="ew")

        # ── Log ──────────────────────────────────────────────────────
        ctk.CTkLabel(self, text="Progreso:", anchor="w").grid(
            row=6, column=0, padx=20, sticky="w")
        self.log_area = ctk.CTkTextbox(self, height=130,
                                       font=ctk.CTkFont(family="monospace", size=11))
        self.log_area.grid(row=7, column=0, padx=20, pady=(0, 15), sticky="ew")
        self.log_area.configure(state="disabled")

    # ── Directory picker ────────────────────────────────────────────────────
    def choose_directory(self):
        def _run():
            try:
                p = subprocess.Popen(
                    ["zenity", "--file-selection", "--directory",
                     f"--filename={self.download_dir.get()}/"],
                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
                out, _ = p.communicate()
                out = out.strip()
                if p.returncode == 0 and out:
                    self.after(0, self._apply_directory, out)
            except Exception as e:
                print("Error zenity:", e)
        threading.Thread(target=_run, daemon=True).start()

    def _apply_directory(self, path):
        self.download_dir.set(path)
        self.dir_entry.configure(state="normal")
        self.dir_entry.delete(0, "end")
        self.dir_entry.insert(0, path)
        self.dir_entry.configure(state="readonly")

    # ── Fetch playlist ──────────────────────────────────────────────────────
    def start_fetch(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Advertencia", "Por favor ingresa una URL.")
            return
        
        self.fetch_btn.configure(state="disabled", text="Buscando...")
        self.download_btn.configure(state="disabled")
        self._clear_video_list()
        self.log("🔍 Buscando videos en la lista...")
        
        # Llama a la lógica en yt_handler
        fetch_playlist_async(
            url, 
            on_success=lambda videos: self.after(0, self._populate_video_list, videos),
            on_error=lambda err: self.after(0, self._on_fetch_error, err)
        )

    def _on_fetch_error(self, err_msg):
        self.log(f"❌ Error al buscar: {err_msg}")
        self.fetch_btn.configure(state="normal", text="🔍 Buscar Videos")

    def _populate_video_list(self, videos):
        self._clear_video_list()
        self.video_vars = {}

        # Separate available vs unavailable
        available = [(vid_id, title) for vid_id, title in videos if title != "NA"]
        unavailable_count = len(videos) - len(available)

        if not available:
            self.no_videos_label = ctk.CTkLabel(
                self.scroll,
                text="⚠ No se encontraron videos disponibles. Intenta con otra URL.",
                text_color="orange")
            self.no_videos_label.grid(row=0, column=0, padx=10, pady=10)
            self.log("⚠ No se encontraron videos disponibles.")
        else:
            msg = f"✅ Se encontraron {len(available)} videos disponibles."
            if unavailable_count > 0:
                msg += f" ({unavailable_count} eliminados de YouTube, se ignoraron)"
            self.log(msg)
            
            for i, (vid_id, title) in enumerate(available):
                var = ctk.BooleanVar(value=True)
                self.video_vars[vid_id] = (var, title)
                cb = ctk.CTkCheckBox(self.scroll,
                                     text=f"{i+1}. {title}",
                                     variable=var,
                                     onvalue=True, offvalue=False)
                cb.grid(row=i, column=0, sticky="w", padx=10, pady=2)

            self.download_btn.configure(state="normal")

        self.list_label.configure(
            text=f"Videos disponibles: {len(available)} / {len(videos)}")
        self.fetch_btn.configure(state="normal", text="🔍 Buscar Videos")

    def _clear_video_list(self):
        for widget in self.scroll.winfo_children():
            widget.destroy()
        self.video_vars = {}

    def select_all(self):
        for var, _ in self.video_vars.values():
            var.set(True)

    def deselect_all(self):
        for var, _ in self.video_vars.values():
            var.set(False)

    # ── Download ─────────────────────────────────────────────────────────────
    def start_download(self):
        selected = [vid_id for vid_id, (var, _) in self.video_vars.items() if var.get()]
        if not selected:
            messagebox.showwarning("Advertencia", "Selecciona al menos un video.")
            return
        out_dir = self.download_dir.get()
        if not os.path.exists(out_dir):
            messagebox.showerror("Error", "La carpeta destino no existe.")
            return

        self.download_btn.configure(state="disabled")
        self.fetch_btn.configure(state="disabled")
        self.log_area.configure(state="normal")
        self.log_area.delete("1.0", "end")
        self.log_area.configure(state="disabled")
        self.log(f"🚀 Descargando {len(selected)} videos...")

        fmt = self.format_var.get()
        
        download_videos_async(
            video_ids=selected,
            out_dir=out_dir,
            fmt=fmt,
            on_log=lambda msg: self.after(0, self.log, msg),
            on_done=lambda count, ext: self.after(0, self._on_download_done, count, ext),
            on_error=lambda err: self.after(0, self._on_download_error, err)
        )

    def _on_download_done(self, count, ext):
        self.log(f"📁 Total de archivos .{ext} en la carpeta: {count}")
        messagebox.showinfo("Listo", f"Proceso terminado.\n{count} archivos .{ext} en la carpeta.")
        self._reset_buttons()

    def _on_download_error(self, err_msg):
        self.log(f"❌ Error: {err_msg}")
        self._reset_buttons()

    def _reset_buttons(self):
        self.download_btn.configure(state="normal")
        self.fetch_btn.configure(state="normal")

    # ── Log helper ────────────────────────────────────────────────────────────
    def log(self, message):
        self.log_area.configure(state="normal")
        self.log_area.insert("end", message + "\n")
        self.log_area.see("end")
        self.log_area.configure(state="disabled")
