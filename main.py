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
        print("\nChecking for updates...")
        
        # Fetch the latest changes
        subprocess.run(['git', 'fetch', 'origin'], check=True, capture_output=True)
        
        # Get number of commits behind origin
        result = subprocess.run(
            ['git', 'rev-list', 'HEAD..origin/main', '--count'],
            capture_output=True,
            text=True,
            check=True
        )
        commits_behind = int(result.stdout.strip())
        
        if commits_behind > 0:
            print(f"\nUpdate available! Current version: {current_version}")
            print(f"Your version is {commits_behind} commits behind the latest version.")
            
            # Ask user if they want to update (default is yes)
            user_input = input("\nWould you like to update to the latest version? (Press Enter for yes, or type 'no'): ").strip().lower()
            if user_input == '' or user_input == 'yes':
                return True
        else:
            print(f"\nYou are using the latest version: {current_version}")
        
        return False
    except Exception as e:
        logging.error(f"Error checking for updates: {e}")
        print(f"Error checking for updates: {e}")
        return False

def update_codebase():
    try:
        print("\nStarting update process...")
        
        # Get the directory of the current script/executable
        if getattr(sys, 'frozen', False):
            app_path = os.path.dirname(sys.executable)
        else:
            app_path = os.path.dirname(os.path.abspath(__file__))
        
        # Stash any local changes
        subprocess.run(['git', 'stash'], check=True, capture_output=True)
        
        # Pull the latest changes
        print("Pulling latest updates...")
        subprocess.run(['git', 'pull', 'origin', 'main'], check=True)
        
        # Run the update and build script
        print("\nRunning update and build script...")
        if os.name == 'nt':  # Windows
            build_script = os.path.join(app_path, 'update_and_build.bat')
            if os.path.exists(build_script):
                subprocess.run([build_script], check=True, shell=True)
                print("\nUpdate and build completed successfully!")
                print("The application will now close. Please run the new version.")
                input("Press Enter to exit...")
                os._exit(0)
            else:
                print("Error: update_and_build.bat not found!")
                return False
        else:
            # For non-Windows systems
            subprocess.run([sys.executable, 'build.py'], check=True)
            print("\nUpdate and build completed successfully!")
            print("The application will now close. Please run the new version.")
            input("Press Enter to exit...")
            os._exit(0)
            
        return True
        
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed during update process: {e}")
        print(f"\nError during update: {e}")
        print("Please try updating manually by running update_and_build.bat")
        return False
    except Exception as e:
        logging.error(f"Unexpected error during update: {e}")
        print(f"\nUnexpected error: {e}")
        print("Please try updating manually by running update_and_build.bat")
        return False

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
        return []  # Return empty list instead of None

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

    # Step 6: Ask if the user wants to update all models (default is yes)
    select_all = input("Do you want to update all models? (Press Enter for yes, or type 'no'): ").strip().lower()
    if select_all == '' or select_all == 'yes':
        print(f"\nSelected all models: {', '.join(models)}")
        logging.info(f"Selected all {len(models)} models")
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
                    if selected_models:  # If we have selections
                        print(f"\nFinal selected models: {', '.join(selected_models)}")
                        logging.info(f"Manually selected {len(selected_models)} models: {', '.join(selected_models)}")
                        return selected_models  # Return the selected models
                    else:  # If no selections yet, confirm exit
                        confirm = input("No models selected. Are you sure you want to exit? (Press Enter for yes, or type 'no'): ").lower()
                        if confirm == '' or confirm == 'yes':
                            logging.warning("User confirmed exit without selecting any models")
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
        logging.info(f"Starting to write usernames for {len(models)} models in device {device_folder}")
        base_path = os.path.join(r"C:\Users\Fredrick\Desktop\full_igbot_13.1.3", device_folder)
        if not os.path.exists(base_path):
            error_msg = f"Device folder not found: {base_path}"
            logging.error(error_msg)
            print(f"Error: {error_msg}")
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
        # Setup environment and logging first thing
        logs_dir = setup_environment()
        logging.info("Application started")
        print(f"Log file location: {os.path.join(logs_dir, 'app.log')}")

        # Check for updates first
        if check_for_updates():
            if update_codebase():
                return  # Exit after successful update
            else:
                print("\nContinuing with current version...")

        # Step 1: Get connected devices
        devices = get_connected_devices()
        if not devices:
            logging.error("No devices found")
            print("No devices found. Exiting...")
            input("Press Enter to exit...")
            return

        # Step 2: Let user select a device
        selected_device = select_device(devices)
        if not selected_device:
            logging.error("No device selected by user")
            print("No device selected. Exiting...")
            input("Press Enter to exit...")
            return

        # Step 3: Let user select models
        selected_models = select_model_accounts(selected_device)
        if not selected_models:
            logging.error("No models selected by user")
            print("No models selected. Exiting...")
            input("Press Enter to exit...")

        # Step 4: Read usernames from the random_usernames file in project directory
        # Get the application directory whether running as script or frozen executable
        if getattr(sys, 'frozen', False):
            # If the application is run as a bundle (frozen)
            base_dir = os.path.dirname(sys.executable)
        else:
            # If the application is run from a Python interpreter
            base_dir = os.path.dirname(os.path.abspath(__file__))

        possible_filenames = ['random_usernames', 'random_usernames.txt']
        
        # Define possible directory locations to search
        search_dirs = [
            base_dir,  # Current directory
            os.path.dirname(base_dir),  # One directory up
            os.path.join(base_dir, 'data'),  # data subdirectory
        ]

        print("Searching for username files in the following locations:")
        for directory in search_dirs:
            print(f"- {directory}")
        
        # Try both possible filenames in all possible directories
        usernames_file = None
        for directory in search_dirs:
            for filename in possible_filenames:
                temp_path = os.path.join(directory, filename)
                if os.path.exists(temp_path):
                    usernames_file = temp_path
                    print(f"\nFound username file at: {temp_path}")
                    break
            if usernames_file:
                break

        
        if not usernames_file:
            print("\nError: Username file not found!")
            print("Looked for files in:", project_dir)
            print("Expected filenames:", possible_filenames)
            print("\nPlease ensure one of these files exists in the project directory.")
            logging.error(f"Username file not found. Searched for: {possible_filenames}")
            input("Press Enter to exit...")
            return

        print(f"Reading usernames from: {usernames_file}")
        usernames = read_usernames_from_file(usernames_file)
        if not usernames:
            logging.error("No usernames found in random_usernames file")
            print("No usernames found in random_usernames file. Exiting...")
            input("Press Enter to exit...")
            return
        
        print(f"Found {len(usernames)} usernames to process")
        logging.info(f"Processing {len(usernames)} usernames for {len(selected_models)} models")

        # Step 6: Write usernames to selected models
        success = write_usernames_to_likesource(selected_device, selected_models, usernames)
        
        if success:
            logging.info("Successfully completed all operations")
            print("\nAll operations completed successfully!")
        else:
            logging.error("Failed to complete all operations")
            print("\nSome operations failed. Check the log file for details.")
        
        input("\nPress Enter to exit...")

    except Exception as e:
        logging.error(f"An error occurred: {str(e)}", exc_info=True)
        print(f"\nAn error occurred: {str(e)}")
        print(f"Check the log file for details: {os.path.join(logs_dir, 'app.log')}")
        input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
