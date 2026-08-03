import os
import subprocess
import sys

def main():
    print("Checking dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller", "customtkinter"])

    import customtkinter
    ctk_path = os.path.dirname(customtkinter.__file__)
    print(f"Found customtkinter at: {ctk_path}")

    artifact_name = os.environ.get("ARTIFACT_NAME", "YoutubeDownloader")
    version = os.environ.get("VERSION", "latest")
    
    sep = os.pathsep
    
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--onefile', '--windowed',
        '--name', f'{artifact_name}-{version}',
        '--add-data', f'{ctk_path}{sep}customtkinter',
        '--hidden-import', 'customtkinter',
        'src/main.py'
    ]
    
    print('Running:', ' '.join(cmd))
    subprocess.run(cmd, check=True)

if __name__ == "__main__":
    main()
