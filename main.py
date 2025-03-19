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
    app_dir = get_app_data_dir()
    logs_dir = os.path.join(app_dir, 'logs')
    data_dir = os.path.join(app_dir, 'data')
    
    # Create necessary directories
    os.makedirs(logs_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)
    
    # Setup logging
    log_file = os.path.join(logs_dir, 'error_log.txt')
    logging.basicConfig(
        filename=log_file,
        level=logging.ERROR,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    return app_dir, data_dir
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
        print(f"Error checking for updates: {e}")
        return False

def update_codebase():
    try:
        print("Pulling the latest updates from the repository...")
        subprocess.check_call(['git', 'pull'])
        print("Code updated successfully!")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to update codebase: {e}")
        print(f"Failed to update codebase: {e}")
        sys.exit(1)

def update_tool():
    if check_for_updates():
        user_input = input("Would you like to update to the latest version? (yes/no): ").strip().lower()
        if user_input == "yes":
            update_codebase()
            print("Rebuilding executable...")
            try:
                # Run the build script
                subprocess.run([sys.executable, 'build.py'], check=True)
                print("Update and rebuild completed successfully!")
                print("Please close this window and run the new version from the dist folder.")
                input("Press Enter to exit...")
                sys.exit(0)
            except subprocess.CalledProcessError as e:
                logging.error(f"Failed to rebuild after update: {e}")
                print(f"Failed to rebuild after update: {e}")
                input("Press Enter to continue with current version...")
        else:
            print("Update skipped.")
    else:
        print("No updates found.")

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

    models = [folder for folder in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, folder))]
    if not models:
        print("Error: No models found in the selected device folder.")
        return None

    # Step 6: Ask if the user wants to update all models
    select_all = input("Do you want to update all models? (yes/no): ").strip().lower()
    if select_all == 'yes':
        return models

    # Step 7: If not all, manually select the models to update
    selected_models = []
    print("Available models:")
    for i, model in enumerate(models, start=1):
        print(f"{i}. {model}")

    while True:
        model_index = int(input("Enter the number of the model you want to select (0 to finish): ")) - 1
        if model_index == -1:
            break
        if 0 <= model_index < len(models):
            selected_models.append(models[model_index])
        else:
            print("Invalid model selected.")
    
    return selected_models

# Step 8: Write the selected usernames to the like-source-followers.txt file for each selected model
def write_usernames_to_likesource(device_folder, models, usernames):
    base_path = os.path.join(r"C:\Users\Fredrick\Desktop\full_igbot_13.1.3", device_folder)
    for model in models:
        model_folder = os.path.join(base_path, model)
        file_path = os.path.join(model_folder, 'like-source-followers.txt')
        
        if not os.path.exists(file_path):
            print(f"Error: {file_path} not found.")
            continue

        update_txt_file(file_path, usernames)
        print(f"Usernames have been written to {file_path}")

# Main function
def main():
    print("Welcome to the tool!")

    # Step 0: Check for updates before proceeding
    update_tool()

    # Step 1: Get connected devices
    devices = get_connected_devices()
    
    # Step 2: Let the user select a device
    selected_device = select_device(devices)
    if not selected_device:
        return
    
    # Step 3: Let the user select models to update
    selected_models = select_model_accounts(selected_device)
    if not selected_models:
        return

    # Step 4: Read usernames from file
    usernames_file = "path_to_your_usernames_file.txt"  # Change this to your source usernames file
    usernames = read_usernames_from_file(usernames_file)
    
    if not usernames:
        print("Error: No usernames found.")
        return

    # Step 5: Write selected usernames to the like-source-followers.txt file for each model
    write_usernames_to_likesource(selected_device, selected_models, usernames)

if __name__ == "__main__":
    main()

