import sys
import os

# Asegurar que el directorio 'src' esté en el PYTHONPATH 
# por si se ejecuta desde el directorio padre
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.app_window import YoutubeDownloaderApp

def main():
    app = YoutubeDownloaderApp()
    app.mainloop()

if __name__ == "__main__":
    main()
