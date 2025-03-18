import os
import subprocess
import sys
import logging

# Attempt to install missing packages automatically
def install_package(package_name):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])

# Try importing the required packages, and install them if they are missing
try:
    import requests
except ImportError:
    print("requests module not found. Installing...")
    install_package("requests")
    import requests  # After installation, import it again

# Setup logging to a file
logging.basicConfig(filename='error_log.txt', level=logging.ERROR)

# Function to check for updates
def check_for_updates():
    try:
        # Current version of the tool (could be read from a version file or hardcoded)
        current_version = "1.0.0"  # You can replace this with actual logic to fetch current version if needed.

        # URL to check for the latest release (GitHub API)
        repo_url = "https://api.github.com/repos/ZacJMagee/OniPlugin/releases/latest"

        # Request the latest release information from GitHub
        response = requests.get(repo_url)
        latest_release = response.json()

        # Extract the latest version tag
        latest_version = latest_release["tag_name"]

        # Check if the current version is outdated
        if current_version != latest_version:
            print(f"Update available! Current version: {current_version}, Latest version: {latest_version}")
            return True
        else:
            print(f"You are using the latest version: {current_version}")
            return False
    except Exception as e:
        logging.error(f"Error checking for updates: {e}")
        print(f"Error checking for updates: {e}")
        return False

# Function to pull the latest code from the repository
def update_codebase():
    try:
        print("Pulling the latest updates from the repository...")
        subprocess.check_call(['git', 'pull'])
        print("Code updated successfully!")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to update codebase: {e}")
        print(f"Failed to update codebase: {e}")
        sys.exit(1)

# Function to execute the update process
def update_tool():
    if check_for_updates():
        user_input = input("Would you like to update to the latest version? (yes/no): ").strip().lower()
        if user_input == "yes":
            update_codebase()
            print("Please restart the tool to apply the update.")
        else:
            print("Update skipped.")
    else:
        print("No updates found.")

# Step 1: Detect connected devices using adb
def get_connected_devices():
    try:
        # Run adb devices command to get connected devices
        output = subprocess.check_output(['adb', 'devices'], stderr=subprocess.STDOUT)
        output = output.decode('utf-8').strip().splitlines()
        devices = [line.split()[0] for line in output if line and line != "List of devices attached"]
        return devices
    except subprocess.CalledProcessError as e:
        logging.error(f"Error getting devices: {e.output}")
        print(f"Error getting devices: {e.output}")
        return []

# Step 2: Read usernames from a file
def read_usernames_from_file(file_path):
    try:
        with open(file_path, 'r') as file:
            usernames = file.readlines()
        return [username.strip() for username in usernames]
    except Exception as e:
        logging.error(f"Error reading file {file_path}: {e}")
        print(f"Error reading file {file_path}: {e}")
        return []

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

