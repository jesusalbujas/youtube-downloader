import sys
import os
import flet as ft

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.app import main_app

if __name__ == "__main__":
    ft.run(main_app, assets_dir="assets")
