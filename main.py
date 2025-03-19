import os
import subprocess
import sys
import logging
import site
import json
from pathlib import Path
import ctypes
import re
from packaging import version

# Function to read usernames from a file
def read_usernames_from_file(file_path):
    try:
        with open(file_path, 'r') as file:
            usernames = file.readlines()
        return [username.strip() for username in usernames]
    except Exception as e:
        logging.error(f"Error reading file {file_path}: {e}")
        print(f"Error reading file {file_path}: {e}")
        return []

# Function to get connected devices
def get_connected_devices():
    base_path = r"C:\Users\Fredrick\Desktop\full_igbot_13.1.3"
    try:
        # Pattern for Android device IDs: Only capital letters and numbers
        device_pattern = re.compile(r'^[A-Z0-9]+$')
        
        # Filter folders that match the device ID pattern and are at least 10 characters long
        devices = [
            folder for folder in os.listdir(base_path)
            if os.path.isdir(os.path.join(base_path, folder))
            and device_pattern.match(folder)
            and len(folder) >= 10  # Most Android device IDs are at least 10 characters
        ]
        
        if not devices:
            print("No valid Android devices found.")
            logging.warning("No valid Android devices found in the directory.")
        
        return devices
    except Exception as e:
        logging.error(f"Error getting connected devices: {e}")
        print(f"Error getting connected devices: {e}")
        return []

# Get the application data directory
def get_app_data_dir():
    if sys.platform == 'win32':
        return os.path.join(os.environ['LOCALAPPDATA'], 'OniPlugin')
    return os.path.expanduser('~/.oniplugin')

# Ensure we have admin rights on Windows
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def request_admin():
    if sys.platform == 'win32':
        if not is_admin():
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
            sys.exit(0)

# Setup application directories and environment
def setup_environment():
    # Create logs directory in the project root
    logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # Setup logging to both file and console
    log_file = os.path.join(logs_dir, 'app.log')
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logs_dir
def check_for_updates():
    try:
        from version import VERSION as current_version
        
        # Get the latest commit hash
        result = subprocess.run(['git', 'ls-remote', 'origin', 'HEAD'], 
                              capture_output=True, text=True)
        remote_hash = result.stdout.split()[0]
        
        # Get the current commit hash
        result = subprocess.run(['git', 'rev-parse', 'HEAD'], 
                              capture_output=True, text=True)
        local_hash = result.stdout.strip()
        
        if remote_hash != local_hash:
            print(f"Update available! Current version: {current_version}")
            print("New changes are available in the repository.")
            return True
        else:
            print(f"You are using the latest version: {current_version}")
            return False
    except Exception as e:
        logging.error(f"Error checking for updates: {e}")
def update_codebase():
    try:
        print("Pulling the latest updates from the repository...")
        # Fetch all changes first
        subprocess.check_call(['git', 'fetch', '--all'])
        # Reset to match remote main/master branch
        subprocess.check_call(['git', 'reset', '--hard', 'origin/main'])
        print("Code updated successfully!")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to update codebase: {e}")
        print(f"Failed to update codebase: {e}")
        sys.exit(1)

    user_input = input("Would you like to update to the latest version? (yes/no): ").strip().lower()
    if user_input != "yes":
        print("Update skipped.")
        return

    try:
        # First, stash any local changes
        subprocess.run(['git', 'stash'], check=True)
        
        # Update the codebase
        update_codebase()
        
        # Get the directory of the current executable
        if getattr(sys, 'frozen', False):
            app_path = os.path.dirname(sys.executable)
        else:
            app_path = os.path.dirname(os.path.abspath(__file__))
        
        print("Rebuilding executable...")
        
        build_success = False
        try:
            # Run the appropriate build script based on the platform
            if os.name == 'nt':  # Windows
                build_script = os.path.join(app_path, 'update_and_build.bat')
                if os.path.exists(build_script):
                    subprocess.run([build_script], check=True, shell=True)
                    build_success = True
                else:
                    print("update_and_build.bat not found, using build.py")
            
            # If Windows build script failed or we're on another platform
            if not build_success:
                subprocess.run([sys.executable, 'build.py'], check=True)
                build_success = True
            
            # If build was successful, exit
            if build_success:
                print("\nUpdate and rebuild completed successfully!")
                print("The new version has been built in the dist folder.")
                print("This window will close. Please run the new version from the dist folder.")
                input("Press Enter to exit...")
                os._exit(0)
            
        except subprocess.CalledProcessError as e:
            print(f"Failed to run build script: {e}")
            raise  # Re-raise to be caught by outer try block
            
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed during update process: {e}")
        print(f"\nError during update: {e}")
        print("Please try updating manually by running update_and_build.bat")
        input("Press Enter to continue with current version...")
    except Exception as e:
        logging.error(f"Unexpected error during update: {e}")
        print(f"\nUnexpected error: {e}")
        print("Please try updating manually by running update_and_build.bat")
        input("Press Enter to continue with current version...")

# Step 3: Update or replace the contents of a text file
def update_txt_file(file_path, content_list):
    try:
        with open(file_path, 'w') as file:
            for item in content_list:
                file.write(item + '\n')
        print(f"Updated file at {file_path}")
    except Exception as e:
        logging.error(f"Error updating file {file_path}: {e}")
        print(f"Error updating file {file_path}: {e}")

# Step 4: Let the user select a connected device
def select_device(devices):
    if not devices:
        print("Error: No connected devices found.")
        return None
    print("Available devices:")
    for i, device in enumerate(devices, start=1):
        print(f"{i}. {device}")
    device_index = int(input("Enter the number of the device you want to select: ")) - 1
    if 0 <= device_index < len(devices):
        return devices[device_index]
    else:
        print("Invalid device selected.")
        return None

# Step 5: Let the user select models (folders) under the selected device
def select_model_accounts(device_folder):
    base_path = os.path.join(r"C:\Users\Fredrick\Desktop\full_igbot_13.1.3", device_folder)
    if not os.path.exists(base_path):
        print(f"Error: Device folder not found: {base_path}")
        return None

    # Filter out system folders and hidden folders (starting with .)
    models = [
        folder for folder in os.listdir(base_path)
        if os.path.isdir(os.path.join(base_path, folder))
        and not folder.startswith('.')  # Exclude hidden folders
        and not folder.lower() in ['.stm', '.trash', 'trash', 'temp', 'temporary']  # Exclude specific system folders
    ]
    
    if not models:
        print("Error: No valid models found in the selected device folder.")
        return None

    # Step 6: Ask if the user wants to update all models
    select_all = input("Do you want to update all models? (yes/no): ").strip().lower()
    if select_all == 'yes':
        return models

    # Step 7: If not all, manually select the models to update
    selected_models = []
    print("\nAvailable models:")
    for i, model in enumerate(models, start=1):
        print(f"{i}. {model}")
    print("\nEnter model numbers one at a time. Enter 0 when done.")

    while True:
        try:
            model_index = int(input("\nSelect model number (0 to finish): ")) - 1
            if model_index == -1:  # User entered 0
                if selected_models:  # If we have selections, break the loop
                    break
                else:  # If no selections yet, confirm exit
                    confirm = input("No models selected. Are you sure you want to exit? (yes/no): ").lower()
                    if confirm == 'yes':
                        return []
                    continue
            
            if 0 <= model_index < len(models):
                model = models[model_index]
                if model in selected_models:
                    print(f"Model '{model}' is already selected.")
                else:
                    selected_models.append(model)
                    print(f"Added '{model}'. Currently selected models: {', '.join(selected_models)}")
            else:
                print(f"Invalid selection. Please enter a number between 1 and {len(models)}")
        except ValueError:
            print("Please enter a valid number.")
            continue

def write_usernames_to_likesource(device_folder, models, usernames):
    try:
        base_path = os.path.join(r"C:\Users\Fredrick\Desktop\full_igbot_13.1.3", device_folder)
        if not os.path.exists(base_path):
            logging.error(f"Device folder not found: {base_path}")
            print(f"Error: Device folder not found: {base_path}")
            return False

        success_count = 0
        for model in models:
            try:
                model_folder = os.path.join(base_path, model)
                if not os.path.exists(model_folder):
                    logging.error(f"Model folder not found: {model_folder}")
                    print(f"Error: Model folder not found for {model}")
                    continue

                file_path = os.path.join(model_folder, 'like-source-followers.txt')
                
                # Create the file if it doesn't exist
                if not os.path.exists(file_path):
                    logging.info(f"Creating new file: {file_path}")
                    open(file_path, 'w').close()

                update_txt_file(file_path, usernames)
                print(f"✓ Successfully updated {file_path}")
                success_count += 1
                
            except Exception as e:
                logging.error(f"Error processing model {model}: {str(e)}")
                print(f"Error processing model {model}: {str(e)}")

        print(f"\nCompleted: Successfully updated {success_count} out of {len(models)} models")
        return success_count > 0

    except Exception as e:
        logging.error(f"Error in write_usernames_to_likesource: {str(e)}")
        print(f"Error updating usernames: {str(e)}")
        return False

def main():
    try:
        # Setup environment and logging
        logs_dir = setup_environment()
        logging.info("Application started")

        # Step 1: Get connected devices
        devices = get_connected_devices()
        if not devices:
            print("No devices found. Exiting...")
            return

        # Step 2: Let user select a device
        selected_device = select_device(devices)
        if not selected_device:
            print("No device selected. Exiting...")
            return

        # Step 3: Let user select models
        selected_models = select_model_accounts(selected_device)
        if not selected_models:
            print("No models selected. Exiting...")
            return

        # Step 4: Read usernames from the random_usernames file in project directory
        usernames_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'random_usernames')
        if not os.path.exists(usernames_file):
            logging.error("random_usernames file not found in project directory")
            print("Error: random_usernames file not found in project directory")
            return

        print(f"Reading usernames from: {usernames_file}")
        usernames = read_usernames_from_file(usernames_file)
        if not usernames:
            print("No usernames found in random_usernames file. Exiting...")
            return
        
        print(f"Found {len(usernames)} usernames to process")

        # Step 6: Write usernames to selected models
        write_usernames_to_likesource(selected_device, selected_models, usernames)

    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
