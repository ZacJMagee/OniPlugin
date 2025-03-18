import os
import subprocess
import shutil
from pathlib import Path

def clean_build_dirs():
    """Clean up build and dist directories"""
    dirs_to_clean = ['build', 'dist']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"Cleaned {dir_name} directory")

def build_executable():
    """Build the executable using PyInstaller"""
    try:
        # Clean previous builds
        clean_build_dirs()
        
        # Check if icon exists, if not, build without it
        if os.path.exists('icon.ico'):
            build_command = ['pyinstaller', 'oniplugin.spec']
        else:
            print("Warning: icon.ico not found, building without icon")
            build_command = [
                'pyinstaller',
                '--name=OniPlugin',
                '--onefile',
                '--clean',
                '--add-data=version.py;.',
                '--hidden-import=packaging',
                '--hidden-import=packaging.version',
                '--hidden-import=packaging.specifiers',
                '--hidden-import=packaging.requirements',
                'main.py'
            ]
        
        # Run the build
        subprocess.run(build_command, check=True)
        
        print("\nBuild completed successfully!")
        print(f"Executable can be found in: {os.path.abspath('dist')}")
        
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    build_executable()

