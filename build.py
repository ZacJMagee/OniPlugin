import os
import subprocess
import shutil
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('build.log')
    ]
)

def install_requirements():
    """Install required packages for building"""
    requirements = [
        'pyinstaller>=5.13.0',
        'requests>=2.31.0',
        'packaging>=23.2',

        'ctypes-windows-sdk>=0.0.3;platform_system=="Windows"',
        'setuptools',
        'wheel',
        'pip>=21.0'
    ]
    
    print("Installing build requirements...")
    try:
        # Upgrade pip first
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        
        # Install all requirements at once
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + requirements)
        logging.info("Successfully installed all requirements")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to install requirements: {e}")
        sys.exit(1)

def clean_build_dirs():
    """Clean up build and dist directories"""
    # Backup previous build if it exists
    if os.path.exists('dist'):
        try:
            backup_dir = 'dist_backup'
            if os.path.exists(backup_dir):
                shutil.rmtree(backup_dir)
            shutil.copytree('dist', backup_dir)
            logging.info("Created backup of previous build")
        except Exception as e:
            logging.warning(f"Could not backup previous build: {e}")

    dirs_to_clean = ['build', 'dist']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            try:
                shutil.rmtree(dir_name)
                logging.info(f"Cleaned {dir_name} directory")
            except Exception as e:
                logging.error(f"Failed to clean {dir_name}: {e}")
                sys.exit(1)

def check_git_updates():
    """Check if there are any pending git updates"""
    try:
        # Fetch the latest changes
        subprocess.run(['git', 'fetch'], check=True)
        
        # Check if we're behind the remote
        result = subprocess.run(['git', 'status', '-uno'], 
                              capture_output=True, text=True, check=True)
        
        if "Your branch is behind" in result.stdout:
            return True
        return False
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to check git updates: {e}")
        return False

def check_version():
    """Check if version.py exists and has valid version"""
    if not os.path.exists('version.py'):
        logging.error("version.py not found!")
        sys.exit(1)
    try:
        from version import VERSION
        if not VERSION:
            logging.error("VERSION not defined in version.py")
            sys.exit(1)
        logging.info(f"Building version: {VERSION}")
    except Exception as e:
        logging.error(f"Error reading version: {e}")
        sys.exit(1)

def build_executable():
    """Build the executable using PyInstaller"""
    try:
        # Check version first
        check_version()

        # Check for updates
        if check_git_updates():
            logging.info("Updates available in repository.")
            user_input = input("Would you like to pull latest changes before building? (yes/no): ").strip().lower()
            if user_input == 'yes':
                subprocess.run(['git', 'pull'], check=True)
                logging.info("Successfully pulled latest changes.")
        
        # Install requirements
        install_requirements()
        
        # Clean previous builds
        clean_build_dirs()
        
        # Prepare build command
        if os.path.exists('oniplugin.spec'):
            logging.info("Using existing spec file")
            build_command = [sys.executable, '-m', 'PyInstaller', 'oniplugin.spec', '--noconfirm']
        else:
            logging.info("Using default configuration")
            build_command = [
                sys.executable, '-m', 'PyInstaller',
                '--name=OniPlugin',
                '--onefile',
                '--clean',
                '--add-data=version.py;.',
                '--hidden-import=packaging',
                '--hidden-import=packaging.version',
                '--hidden-import=packaging.specifiers',
                '--hidden-import=packaging.requirements',
                '--hidden-import=pathlib',
                '--hidden-import=ctypes',
                '--hidden-import=json',
                '--hidden-import=logging',
                '--hidden-import=shutil',
                'main.py'
            ]
            
            # Add icon if it exists
            if os.path.exists('icon.ico'):
                build_command.extend(['--icon=icon.ico'])
        
        # Run the build with direct output
        print("Running PyInstaller build command:")
        print(" ".join(build_command))
        logging.info("Running PyInstaller build command: %s", " ".join(build_command))
        
        result = subprocess.run(
            build_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False  # Don't raise exception immediately
        )
        
        # Print output
        if result.stdout:
            print(result.stdout)
            logging.info(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
            logging.error(result.stderr)
            
        # Check return code
        if result.returncode != 0:
            raise subprocess.CalledProcessError(result.returncode, build_command)
                
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, build_command)
            
        logging.info("Build completed successfully!")
        logging.info(f"Executable can be found in: {os.path.abspath('dist')}")
        
    except subprocess.CalledProcessError as e:
        logging.error(f"Build failed with exit code {e.returncode}")
        logging.error("Check the build log for detailed error messages")
        sys.exit(1)
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        build_executable()
    except KeyboardInterrupt:
        logging.info("Build process interrupted by user")
        sys.exit(1)

