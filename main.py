import os
import subprocess

# Step 1: Detect connected devices using adb
def get_connected_devices():
    try:
        # Run adb devices command to get connected devices
        output = subprocess.check_output(['adb', 'devices'], stderr=subprocess.STDOUT)
        output = output.decode('utf-8').strip().splitlines()
        devices = [line.split()[0] for line in output if line and line != "List of devices attached"]
        return devices
    except subprocess.CalledProcessError as e:
        print(f"Error getting devices: {e.output}")
        return []

# Step 2: Read usernames from a file
def read_usernames_from_file(file_path):
    try:
        with open(file_path, 'r') as file:
            usernames = file.readlines()
        return [username.strip() for username in usernames]
    except Exception as e:
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

