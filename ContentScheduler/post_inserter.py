import os
import sqlite3
import uuid
import re
import json
from pyairtable import Api
from pyairtable.formulas import match
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from download_content import process_content_schedule, select_profile

# ✅ Base directories
BASE_DIR = "/home/zacm/onimator"
SHARED_CONTENT_DIR = "/home/zacm/shared_content_scheduler"

WINDOWS_SHARED_PREFIX = r'C:\Users\Fredrick\shared_content_scheduler'
LINUX_SHARED_PREFIX = '/home/zacm/shared_content_scheduler'

def convert_linux_to_windows_path(linux_path):
    """Convert a Linux path to a full Windows path based on shared sync folder."""
    relative = os.path.relpath(linux_path, LINUX_SHARED_PREFIX)
    windows_path = os.path.join(WINDOWS_SHARED_PREFIX, relative)
    return windows_path.replace('/', '\\')

def generate_unique_post_id():
    return str(uuid.uuid4())

def insert_post(
    db_path,
    file_location,
    caption,
    post_music,
    post_type,
    post_location,
    scheduled_date,
    is_published=0,
    skip_all_duplicates=False
):
    """Insert a post into the scheduled_post database, checking for duplicate captions."""
    try:
        if skip_all_duplicates:
            print("⏭️ Skipping due to 'skip all duplicates for this account' setting.")
            return None

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check for duplicate caption
        cursor.execute("SELECT post_id, scheduled_date, file_location FROM scheduled_post WHERE caption = ?", (caption,))
        existing = cursor.fetchone()

        if existing:
            existing_id, existing_date, existing_path = existing
            print(f"\n⚠️ Duplicate caption detected:")
            print(f"→ Existing Post ID: {existing_id}")
            print(f"→ Scheduled for: {existing_date}")
            print(f"→ File: {existing_path}")
            print(f"→ Caption: {caption}")
            print("Options: [y] replace  [s] skip  [n] keep both  [a] skip all for this account")

            choice = input("Your choice: ").strip().lower()
            if choice == 's':
                print("⏭️ Skipping post.")
                conn.close()
                return None
            elif choice == 'y':
                print("♻️ Replacing existing post...")
                cursor.execute("DELETE FROM scheduled_post WHERE post_id = ?", (existing_id,))
            elif choice == 'a':
                print("🚫 Skipping all future duplicates for this account.")
                conn.close()
                return 'SKIP_ALL_DUPES'
            else:
                print("📌 Keeping both posts...")

        # Parse scheduled date
        parsed_date = None
        for fmt in ("%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M"):
            try:
                parsed_date = datetime.strptime(scheduled_date, fmt)
                break
            except ValueError:
                continue
        if not parsed_date:
            print(f"❌ Invalid date/time format: '{scheduled_date}'")
            conn.close()
            return None

        formatted_scheduled_date = parsed_date.strftime("%Y-%m-%d %H:%M")
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Generate post ID
        post_id = generate_unique_post_id()

        query = """
        INSERT INTO scheduled_post (
            post_id, file_location, caption, post_music, 
            post_type, post_location, scheduled_date, date, is_published
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        cursor.execute(query, (
            post_id, file_location, caption, post_music, 
            post_type, post_location, formatted_scheduled_date, current_date, is_published
        ))

        conn.commit()
        conn.close()
        print(f"✅ Inserted post: {post_id} at {formatted_scheduled_date}")
        return post_id

    except Exception as e:
        print(f"❌ Error inserting post: {e}")
        return None

# 🔧 Device Detection - Matches Your Other Script Logic
def get_connected_devices():
    """Retrieve connected Android devices (folders matching device ID format)."""
    try:
        device_pattern = re.compile(r'^[A-Z0-9]+$')  # Only capital letters and numbers

        devices = [
            folder for folder in os.listdir(BASE_DIR)
            if os.path.isdir(os.path.join(BASE_DIR, folder))
            and device_pattern.match(folder)
            and len(folder) >= 10  # Android device IDs are usually 10+ characters
        ]

        if not devices:
            print("❌ No valid Android devices found.")
        
        return devices
    except Exception as e:
        print(f"❌ Error getting connected devices: {e}")
        return []

def select_device(devices):
    """Let the user select a device from the available list."""
    if not devices:
        print("❌ No connected devices found.")
        return None

    print("📱 Available Devices:")
    for i, device in enumerate(devices, 1):
        print(f"{i}. {device}")
    
    try:
        idx = int(input("Select a device: ")) - 1
        if 0 <= idx < len(devices):
            return devices[idx]
    except ValueError:
        pass

    print("❌ Invalid selection.")
    return None

# 🔧 Account (Model) Selection - Follows Your Script Flow
def load_config():
    """Load the configuration from config.json"""
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    try:
        with open(config_path, 'r') as f:
            return json.loads(f.read())
    except Exception as e:
        print(f"❌ Error loading config.json: {e}")
        return None

def select_models(device_folder):
    """Let the user select one or more accounts (models) from device folder."""
    path = os.path.join(BASE_DIR, device_folder)
    
    # Filter out system folders and hidden folders
    models = [
        folder for folder in os.listdir(path)
        if os.path.isdir(os.path.join(path, folder))
        and not folder.startswith('.')  # Exclude hidden folders
        and not folder.lower() in ['.stm', '.trash', 'trash', 'temp', 'temporary', 'camera', 'crash_log', 'snapshot']  # Exclude system folders
    ]

    if not models:
        print("❌ No valid models found in the selected device folder.")
        return None

    # Ask if user wants to update all models (default is yes)
    select_all = input("\nDo you want to update all models? (Press Enter for yes, or type 'no'): ").strip().lower()

    if select_all == '' or select_all == 'yes':
        selected_accounts = device_accounts
        update_all = True
    else:
        selected_accounts = []
        update_all = True

        print(f"\n✅ Selected all models: {', '.join(models)}")
        return models

    # Manual selection mode
    selected_models = []
    print("\n👤 Available models:")
    for i, model in enumerate(models, 1):
        print(f"{i}. {model}")
    print("\nEnter model numbers one at a time. Enter 0 when done.")

    while True:
        try:
            model_index = int(input("\nSelect model number (0 to finish): ")) - 1
            
            # Check if user wants to finish selection
            if model_index == -1:  # User entered 0
                if selected_models:  # If we have selections
                    print(f"\n✅ Final selected models: {', '.join(selected_models)}")
                    return selected_models
                else:  # If no selections yet, confirm exit
                    confirm = input("❌ No models selected. Are you sure you want to exit? (Press Enter for yes, or type 'no'): ").lower()
                    if confirm == '' or confirm == 'yes':
                        return []
                    continue

            # Validate selection
            if 0 <= model_index < len(models):
                model = models[model_index]
                if model in selected_models:
                    print(f"⚠️ Model '{model}' is already selected.")
                else:
                    selected_models.append(model)
                    print(f"✅ Added '{model}'. Currently selected models: {', '.join(selected_models)}")
            else:
                print(f"❌ Invalid selection. Please enter a number between 1 and {len(models)}")
        except ValueError:
            print("❌ Please enter a valid number.")
if __name__ == "__main__":
    load_dotenv()
    print("\n📱 Instagram Post Scheduler")
    print("=" * 50)

    devices = get_connected_devices()
    if not devices:
        print("❌ No devices found.")
        exit()

    selected_device = select_device(devices)
    if not selected_device:
        print("❌ No device selected.")
        exit()

    airtable_pat = os.getenv('AIRTABLE_PAT')
    if not airtable_pat:
        print("❌ Missing AIRTABLE_PAT in .env file")
        exit()

    config_data = load_config()
    if not config_data:
        print("❌ Failed to load config.json")
        exit()

    available_models = list(config_data.get('creators', {}).keys())
    if not available_models:
        print("❌ No models found in config.json")
        exit()

    print("\n📱 Available Models:")
    for i, model in enumerate(available_models, 1):
        print(f"{i}. {model}")

    try:
        model_idx = int(input("\nSelect model number: ")) - 1
        if not (0 <= model_idx < len(available_models)):
            print("❌ Invalid model selection")
            exit()
    except ValueError:
        print("❌ Invalid input")
        exit()

    selected_model = available_models[model_idx]
    model_config = config_data['creators'][selected_model]
    print(f"\n→ Selected model: {selected_model}")

    device_path = os.path.join(BASE_DIR, selected_device)
    print(f"→ Checking accounts in device: {selected_device}")

    device_accounts = [
        folder for folder in os.listdir(device_path)
        if os.path.isdir(os.path.join(device_path, folder))
        and not folder.startswith('.')
        and not folder.lower() in ['.stm', '.trash', 'trash', 'temp', 'temporary', 'camera', 'crash_log', 'log']
    ]

    if not device_accounts:
        print("❌ No accounts found in device folder.")
        exit()

    print("\n📱 Available Device Accounts:")
    for i, account in enumerate(device_accounts, 1):
        print(f"{i}. {account}")

    select_all = input("\nDo you want to update all accounts? (Press Enter for yes, or type 'no'): ").strip().lower()

    update_all = False
    if select_all == '' or select_all == 'yes':
        update_all = True
        selected_accounts = device_accounts
        print(f"\n✅ Selected all accounts: {', '.join(selected_accounts)}")
    else:
        selected_accounts = []
        print("\nEnter account numbers one at a time. Enter 0 when done.")
        while True:
            try:
                idx = int(input("\nSelect account number (0 to finish): ")) - 1
                if idx == -1:
                    if selected_accounts:
                        print(f"\n✅ Final selected accounts: {', '.join(selected_accounts)}")
                        break
                    else:
                        confirm = input("❌ No accounts selected. Exit? (Enter = yes, type 'no' to stay): ").lower()
                        if confirm == '' or confirm == 'yes':
                            exit()
                        continue
                if 0 <= idx < len(device_accounts):
                    account = device_accounts[idx]
                    if account in selected_accounts:
                        print(f"⚠️ Account '{account}' is already selected.")
                    else:
                        selected_accounts.append(account)
                        print(f"✅ Added '{account}'. Currently selected: {', '.join(selected_accounts)}")
                else:
                    print(f"❌ Invalid selection. Enter a number between 1 and {len(device_accounts)}")
            except ValueError:
                print("❌ Please enter a valid number.")

    success_accounts = []
    failed_accounts = []

    for account in selected_accounts:
        print(f"\n📂 Processing account: {account}")
        skip_all_for_this_account = False

        config = {
            'airtable_pat': airtable_pat,
            'base_id': model_config.get('base_id'),
            'table_id': model_config.get('table_id'),
            'view_id': model_config.get('view_id'),
            'output_folder': os.path.join(SHARED_CONTENT_DIR, selected_model, "media"),
        }

        db_path = os.path.join(BASE_DIR, selected_device, account, "scheduled_post.db")
        if not os.path.exists(db_path):
            print(f"❌ Database not found for {account}: {db_path}")
            failed_accounts.append(account)
            continue

        content_data = process_content_schedule(
            airtable_pat=config['airtable_pat'],
            base_id=config['base_id'],
            table_id=config['table_id'],
            view_id=config['view_id'],
            output_folder=config['output_folder'],
            _=None,
            profile=account,
            device={'id': selected_device},
            record_limit=None,
            update_all=False
        )

        if content_data is None or content_data.empty:
            print(f"⚠️ No content found for account: {account}")
            failed_accounts.append(account)
            continue

        inserted_records = []
        for _, post in content_data.iterrows():
            windows_file_path = convert_linux_to_windows_path(post['media_file_path'])
            try:
                combined_dt = datetime.strptime(f"{post['schedule_date']} {post['schedule_time']}", "%d/%m/%Y %H:%M")
                scheduled_datetime = combined_dt.strftime("%Y-%m-%d %H:%M")
                airtable_scheduled_datetime = combined_dt.isoformat()
            except ValueError:
                print(f"❌ Invalid datetime: {post['schedule_date']} {post['schedule_time']}")
                continue

            post_id = insert_post(
                db_path=db_path,
                file_location=windows_file_path,
                caption=post.get('caption', ''),
                post_music=post.get('song', ''),
                post_type=post.get('post_type', 'reels'),
                post_location=post.get('post_location', ''),
                scheduled_date=scheduled_datetime,
                is_published=0,
                skip_all_duplicates=skip_all_for_this_account
            )

            if post_id == 'SKIP_ALL_DUPES':
                skip_all_for_this_account = True
                continue
            if post_id:
                inserted_records.append({
                    "id": post.get('id'),
                    "fields": {
                        "post_id": post_id,
                        "scheduled_date": airtable_scheduled_datetime
                    }
                })

        if inserted_records:
            table = Api(airtable_pat).base(model_config['base_id']).table(model_config['table_id'])
            print(f"🔄 Updating Airtable for {len(inserted_records)} posts...")
            for i in range(0, len(inserted_records), 10):
                batch = inserted_records[i:i+10]
                try:
                    table.batch_update(batch)
                    print(f"✅ Updated batch of {len(batch)} records")
                except Exception as e:
                    print(f"❌ Batch update failed: {e}")
            success_accounts.append(account)
        else:
            print(f"ℹ️ No new posts inserted for {account}, skipping Airtable update.")
            failed_accounts.append(account)

        print(f"✅ Done with account: {account}")

    print("\n✨ Processing complete!")
    print("\n📊 Update Summary:")
    print(f"✅ Successful accounts: {len(success_accounts)}")
    if success_accounts:
        print("   → " + ", ".join(success_accounts))
    print(f"❌ Failed accounts: {len(failed_accounts)}")
    if failed_accounts:
        print("   → " + ", ".join(failed_accounts))

