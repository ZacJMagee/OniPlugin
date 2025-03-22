#!/usr/bin/env python3
import os
import sys
import logging
import re

# Define the base directory where your devices are stored on Linux
BASE_DIR = "/home/zacm/onimator"  # adjust as necessary

def read_usernames_from_file(file_path):
    try:
        with open(file_path, 'r') as file:
            usernames = file.readlines()
        return [username.strip() for username in usernames]
    except Exception as e:
        logging.error(f"Error reading file {file_path}: {e}")
        print(f"Error reading file {file_path}: {e}")
        return []

def setup_environment():
    # Calculate project root assuming this file is in onimator_plugin/update_sources/
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    # Place logs in the centralized logs folder (inside your onimator_plugin directory)
    logs_dir = os.path.join(project_root, 'onimator_plugin', 'logs')
    os.makedirs(logs_dir, exist_ok=True)
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

def get_connected_devices():
    try:
        # Pattern: device IDs contain only uppercase letters and numbers
        device_pattern = re.compile(r'^[A-Z0-9]+$')
        devices = [
            folder for folder in os.listdir(BASE_DIR)
            if os.path.isdir(os.path.join(BASE_DIR, folder))
            and device_pattern.match(folder)
            and len(folder) >= 10  # typical device IDs are at least 10 characters
        ]
        if not devices:
            print("No valid Android devices found.")
            logging.warning("No valid Android devices found in the directory.")
        return devices
    except Exception as e:
        logging.error(f"Error getting connected devices: {e}")
        print(f"Error getting connected devices: {e}")
        return []

def update_txt_file(file_path, content_list):
    try:
        # Read existing content if file exists
        existing_content = set()
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            with open(file_path, 'r') as file:
                existing_content = {line.strip() for line in file if line.strip()}
        new_content = set(content_list)
        combined_content = existing_content.union(new_content)
        with open(file_path, 'w') as file:
            for item in sorted(combined_content):
                file.write(item + '\n')
        new_entries = len(combined_content) - len(existing_content)
        print(f"Updated file at {file_path}")
        print(f"- Previous entries: {len(existing_content)}")
        print(f"- New entries added: {new_entries}")
        print(f"- Total entries now: {len(combined_content)}")
        logging.info(f"File update: {file_path} - Previous: {len(existing_content)}, Added: {new_entries}, Total: {len(combined_content)}")
    except Exception as e:
        logging.error(f"Error updating file {file_path}: {e}")
        print(f"Error updating file {file_path}: {e}")

def select_device(devices):
    if not devices:
        print("Error: No connected devices found.")
        return None
    print("Available devices:")
    for i, device in enumerate(devices, start=1):
        print(f"{i}. {device}")
    try:
        device_index = int(input("Enter the number of the device you want to select: ")) - 1
        if 0 <= device_index < len(devices):
            return devices[device_index]
        else:
            print("Invalid device selected.")
            return None
    except ValueError:
        print("Please enter a valid number.")
        return None

def select_model_accounts(device_folder):
    # Build the path based on the Linux BASE_DIR
    base_path = os.path.join(BASE_DIR, device_folder)
    if not os.path.exists(base_path):
        print(f"Error: Device folder not found: {base_path}")
        return []  # return empty list if not found

    models = [
        folder for folder in os.listdir(base_path)
        if os.path.isdir(os.path.join(base_path, folder))
        and not folder.startswith('.')  # skip hidden folders
        and folder.lower() not in ['.stm', '.trash', 'trash', 'temp', 'temporary']
    ]
    if not models:
        print("Error: No valid models found in the selected device folder.")
        return None

    select_all = input("Do you want to update all models? (Press Enter for yes, or type 'no'): ").strip().lower()
    if select_all == '' or select_all == 'yes':
        print(f"\nSelected all models: {', '.join(models)}")
        logging.info(f"Selected all {len(models)} models")
        return models

    selected_models = []
    print("\nAvailable models:")
    for i, model in enumerate(models, start=1):
        print(f"{i}. {model}")
    print("\nEnter model numbers one at a time. Enter 0 when done.")
    while True:
        try:
            model_index = int(input("\nSelect model number (0 to finish): ")) - 1
            if model_index == -1:  # user entered 0
                if selected_models:
                    print(f"\nFinal selected models: {', '.join(selected_models)}")
                    logging.info(f"Manually selected {len(selected_models)} models: {', '.join(selected_models)}")
                    return selected_models
                else:
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

def select_file_type():
    print("\nWhich file would you like to update?")
    print("1. like-source-followers.txt (default)")
    print("2. follow-specific-sources.txt")
    print("3. follow-source-followers.txt")
    print("4. follow users likers")
    print("5. like posts of specific accs")
    print("6. exclude names - followers")
    print("7. exclude names - likes")
    while True:
        response = input("\nEnter your choice (Press Enter for option 1, or type '2', '3', '4', '5', '6', or '7'): ").strip()
        if response == '':
            return 'like-source-followers.txt'
        elif response == '2':
            return 'follow-specific-sources.txt'
        elif response == '3':
            return 'sources.txt'
        elif response == '4':
            return 'follow-likers-sources.txt'
        elif response == '5':
            return 'like_posts_specific.txt'
        elif response == '6':
            return 'name_must_not_include.txt'
        elif response == '7':
            return 'name_must_not_include_likes.txt'
        else:
            print("Invalid selection. Please try again.")

def write_usernames_to_file(device_folder, models, usernames, target_file):
    try:
        print(f"\nPreparing to update {target_file} for {len(models)} models in device {device_folder}")
        print(f"Will add {len(usernames)} usernames to each model's file")
        response = input("\nDo you want to proceed? (Press Enter for yes, or type 'no'): ").strip().lower()
        if response == 'no':
            print("Operation cancelled by user")
            logging.info("File update operation cancelled by user")
            return False

        logging.info(f"Starting to write usernames for {len(models)} models in device {device_folder} to {target_file}")
        base_path = os.path.join(BASE_DIR, device_folder)
        if not os.path.exists(base_path):
            error_msg = f"Device folder not found: {base_path}"
            logging.error(error_msg)
            print(f"\nError: {error_msg}")
            return False

        success_count = 0
        print("\nUpdating files...")
        for model in models:
            try:
                model_folder = os.path.join(base_path, model)
                if not os.path.exists(model_folder):
                    logging.error(f"Model folder not found: {model_folder}")
                    print(f"⨯ Error: Model folder not found for {model}")
                    continue

                file_path = os.path.join(model_folder, target_file)
                display_path = os.path.relpath(file_path, base_path)
                if not os.path.exists(file_path):
                    logging.info(f"Creating new file: {file_path}")
                    open(file_path, 'w').close()
                update_txt_file(file_path, usernames)
                print(f"✓ Successfully updated {display_path}")
                success_count += 1
            except Exception as e:
                logging.error(f"Error processing model {model}: {str(e)}")
                print(f"⨯ Error processing {model}: {str(e)}")

        print("\nOperation Summary:")
        print(f"✓ Successfully updated: {success_count} models")
        if success_count < len(models):
            print(f"⨯ Failed to update: {len(models) - success_count} models")
        if success_count == len(models):
            print("\nAll files were updated successfully!")
        elif success_count > 0:
            print("\nSome files were updated, but there were errors.")
            print("Check the log file for details.")
        else:
            print("\nNo files were updated successfully.")
            print("Check the log file for details.")
        return success_count > 0
    except Exception as e:
        logging.error(f"Error in write_usernames_to_file: {str(e)}")
        print(f"\nError updating usernames: {str(e)}")
        print("Check the log file for details.")
        return False

def main():
    try:
        logs_dir = setup_environment()
        logging.info("Application started")
        print(f"Log file location: {os.path.join(logs_dir, 'app.log')}")
        while True:
            devices = get_connected_devices()
            if not devices:
                logging.error("No devices found")
                print("No devices found.")
                retry = input("\nWould you like to try again? (Press Enter for yes, or type 'no' to exit): ").strip().lower()
                if retry == 'no':
                    print("\nThank you for using the application!")
                    break
                else:
                    continue

            selected_device = select_device(devices)
            if not selected_device:
                logging.error("No device selected by user")
                print("No device selected.")
                retry = input("\nWould you like to try again? (Press Enter for yes, or type 'no' to exit): ").strip().lower()
                if retry == 'no':
                    print("\nThank you for using the application!")
                    break
                else:
                    continue

            target_file = select_file_type()
            logging.info(f"Selected file type: {target_file}")

            selected_models = select_model_accounts(selected_device)
            if not selected_models:
                logging.error("No models selected by user")
                print("No models selected.")
                retry = input("\nWould you like to try again? (Press Enter for yes, or type 'no' to exit): ").strip().lower()
                if retry == 'no':
                    print("\nThank you for using the application!")
                    break
                else:
                    continue

            # Determine which usernames file to use based on target file type
            if target_file in ['name_must_not_include.txt', 'name_must_not_include_likes.txt']:
                possible_filenames = ['exclude_names.txt']
            else:
                possible_filenames = ['follow_sources', 'follow_sources.txt']

            # Search for the usernames file in a few potential directories
            base_dir = os.path.dirname(os.path.abspath(__file__))
            search_dirs = [
                base_dir,
                os.path.dirname(base_dir),
                os.path.join(base_dir, 'data'),
            ]
            usernames_file = None
            for directory in search_dirs:
                for filename in possible_filenames:
                    temp_path = os.path.join(directory, filename)
                    if os.path.exists(temp_path):
                        usernames_file = temp_path
            if not usernames_file:
                if target_file in ['name_must_not_include.txt', 'name_must_not_include_likes.txt']:
                    print("\nError: exclude_names.txt file not found!")
                    print("Please ensure exclude_names.txt exists in the project directory.")
                    logging.error("exclude_names.txt file not found")
                else:
                    print("\nError: Username file not found!")
                    print("Expected filenames:", possible_filenames)
                    print("\nPlease ensure one of these files exists in the project directory.")
                    logging.error(f"Username file not found. Searched for: {possible_filenames}")
                retry = input("\nWould you like to try again? (Press Enter for yes, or type 'no' to exit): ").strip().lower()
                if retry == 'no':
                    print("\nThank you for using the application!")
                    break
                else:
                    continue

            print(f"Reading usernames from: {usernames_file}")
            usernames = read_usernames_from_file(usernames_file)
            if not usernames:
                logging.error("No usernames found in the usernames file")
                print("No usernames found in the usernames file.")
                retry = input("\nWould you like to try again? (Press Enter for yes, or type 'no' to exit): ").strip().lower()
                if retry == 'no':
                    print("\nThank you for using the application!")
                    break
                else:
                    continue

            print(f"Found {len(usernames)} usernames to process")
            logging.info(f"Processing {len(usernames)} usernames for {len(selected_models)} models")
            success = write_usernames_to_file(selected_device, selected_models, usernames, target_file)
            if success:
                logging.info("Successfully completed all operations")
                print("\nAll operations completed successfully!")
            else:
                logging.error("Failed to complete all operations")
                print("\nSome operations failed. Check the log file for details.")

            continue_response = input("\nWould you like to perform another operation? (Press Enter for yes, or type 'no' to exit): ").strip().lower()
            if continue_response == 'no':
                print("\nThank you for using the application!")
                break
            else:
                print("\n" + "="*50)
                print("Starting new operation...")
                print("="*50 + "\n")
                continue
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}", exc_info=True)
        print(f"\nAn error occurred: {str(e)}")
        print(f"Check the log file for details: {os.path.join(logs_dir, 'app.log')}")
        retry = input("\nWould you like to try again? (Press Enter for yes, or type 'no' to exit): ").strip().lower()
        if retry == 'no':
            print("\nThank you for using the application!")
        else:
            print("\n" + "="*50)
            print("Starting new operation...")
            print("="*50 + "\n")
            main()

if __name__ == "__main__":
    main()

