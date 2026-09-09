"""
Build script for YoutubeDownloader.
Uses `flet pack` (built on PyInstaller) to create standalone executables.
"""
import os
import subprocess
import sys


def main():
    artifact_name = os.environ.get("ARTIFACT_NAME", "YoutubeDownloader")
    version = os.environ.get("VERSION", "latest")
    exe_name = f"{artifact_name}-{version}"

    print(f"Building: {exe_name}")
    print(f"Python:   {sys.version}")

    # Instalar dependencias
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    subprocess.check_call([sys.executable, "-m", "pip", "install", "flet-cli"])

    # Ruta al icono (opcional, solo si existe)
    icon_args = []
    icon_png = os.path.join("assets", "icon.png")
    if os.path.exists(icon_png):
        icon_args = ["--icon", icon_png]

    # flet pack genera el ejecutable en dist/
    cmd = [
        sys.executable, "-m", "flet.cli", "pack",
        "src/main.py",
        "--name", exe_name,
        "--distpath", "dist",
        "-y",                  # sobrescribir sin preguntar
        *icon_args,
    ]

    print("Running:", " ".join(cmd))
    subprocess.check_call(cmd)
    print(f"\n✅ Build completado: dist/{exe_name}")


if __name__ == "__main__":
    main()
