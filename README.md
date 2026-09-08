# YouTube Downloader

Una aplicación de escritorio para descargar videos y listas de reproducción de YouTube, construida con Python, Flet y `yt-dlp`.

## Requisitos Previos

- **Python:** 3.11 o superior.
- **pip:** 26.0 o superior (recomendado).
- **FFmpeg:** necesario para convertir a MP3, unir flujos de MP4 e incrustar metadatos. En Debian/Ubuntu: `sudo apt install ffmpeg`.

## Instalación

1. Clona o descarga el repositorio y navega hasta su directorio:
   ```bash
   cd /opt/development/github/youtube-downloader
   ```

2. Instala las dependencias necesarias. Se recomienda asegurarse de usar la misma versión de `pip` que tu ejecutable de Python (por ejemplo `python3.11`):
   ```bash
   python3.11 -m pip install -r requirements.txt
   ```

## Estructura del Proyecto

El código está modularizado para una mejor mantenibilidad:
- `src/main.py`: Punto de entrada de la aplicación.
- `src/ui/`: Componentes de la interfaz de usuario.
- `src/downloader/`: Lógica para procesar y descargar los videos mediante `yt-dlp`.

## Uso

Para iniciar la aplicación, ejecuta el siguiente comando:

```bash
python3.11 src/main.py
```

### Funcionalidades
- **Búsqueda de Listas:** Pega el enlace de un video o una lista de reproducción. La aplicación listará los videos disponibles y descartará automáticamente aquellos que hayan sido eliminados.
- **Descargas Individuales o por Lotes:** Permite seleccionar/deseleccionar qué videos específicos de la lista quieres bajar.
- **Formatos Soportados:** Video (MP4) y Audio (MP3).
- **Destino Personalizable:** Elige la carpeta donde quieres que se guarden tus archivos.
- **Archivos etiquetados:** las descargas incorporan los metadatos disponibles (título, artista/canal y álbum/lista), sin descargar carátulas para mantener mayor velocidad.
