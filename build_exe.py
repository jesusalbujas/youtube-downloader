"""
Build script for YoutubeDownloader.
Uses `flet pack` (built on PyInstaller) to create standalone executables.
"""
import os
import subprocess
import sys
import platform


def main():
    artifact_name = os.environ.get("ARTIFACT_NAME", "YoutubeDownloader")
    version = os.environ.get("VERSION", "latest")
    exe_name = f"{artifact_name}-{version}"

    print(f"Building: {exe_name}")
    print(f"Python:   {sys.version}")
    print(f"Platform: {platform.system()}")

    # Instalar dependencias
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    subprocess.check_call([sys.executable, "-m", "pip", "install", "flet-cli", "pyinstaller", "pillow"])

    # Seleccionar icono según plataforma
    icon_args = []
    icon_png = os.path.join("assets", "icon.png")

    if os.path.exists(icon_png):
        if platform.system() == "Windows":
            # Convertir PNG -> ICO con Pillow
            ico_path = os.path.join("assets", "icon.ico")
            from PIL import Image
            img = Image.open(icon_png)
            img.save(ico_path, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
            icon_args = ["--icon", ico_path]
            print(f"Icono convertido: {ico_path}")
        else:
            # Linux/macOS aceptan PNG directamente
            icon_args = ["--icon", icon_png]
            print(f"Usando icono: {icon_png}")

    cmd = [
        sys.executable, "-m", "flet.cli", "pack",
        "src/main.py",
        "--name", exe_name,
        "--distpath", "dist",
        "-y",
        *icon_args,
    ]

    print("Running:", " ".join(cmd))
    subprocess.check_call(cmd)
    print(f"\nBuild completado: dist/{exe_name}")


if __name__ == "__main__":
    main()
