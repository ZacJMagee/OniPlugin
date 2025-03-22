import os
import sqlite3
import uuid
import re
import json
from pyairtable import Api
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from .download_content import process_content_schedule, select_profile

BASE_DIR = "/home/zacm/onimator"
SHARED_CONTENT_DIR = "/home/zacm/shared_content_scheduler"

WINDOWS_SHARED_PREFIX = r'C:\Users\Fredrick\shared_content_scheduler'
LINUX_SHARED_PREFIX = '/home/zacm/shared_content_scheduler'

def convert_linux_to_windows_path(linux_path):
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

def get_connected_devices():
    try:
        device_pattern = re.compile(r'^[A-Z0-9]+$')  # Only capital letters and numbers
        devices = [
            folder for folder in os.listdir(BASE_DIR)
            if os.path.isdir(os.path.join(BASE_DIR, folder))
            and device_pattern.match(folder)
            and len(folder) >= 10
        ]
        if not devices:
            print("❌ No valid Android devices found.")
        return devices
    except Exception as e:
        print(f"❌ Error getting connected devices: {e}")
        return []

def select_device(devices):
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

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.json')
    try:
        with open(config_path, 'r') as f:
            return json.loads(f.read())
    except Exception as e:
        print(f"❌ Error loading config.json: {e}")
        return None

# Updated select_accounts function:
def select_accounts(device_accounts):
    """
    Allows selection of accounts using comma-separated numbers and ranges.
    If the user presses Enter (i.e., update all accounts), no extra confirmations are shown.
    Otherwise, a removal option is provided.
    Returns the final list of selected accounts.
    """
    sorted_accounts = sorted(device_accounts, key=lambda x: x.lower())
    
    print("\n📱 Available Device Accounts (sorted alphabetically):")
    for i, account in enumerate(sorted_accounts, 1):
        print(f"{i}. {account}")
    
    user_input = input(
        "\nEnter account numbers separated by commas or ranges (e.g., 1,3-5), "
        "or press Enter to select all accounts: "
    ).strip()
    
    if user_input == "":
        return sorted_accounts.copy()
    else:
        selected_indices = set()
        for token in user_input.split(","):
            token = token.strip()
            if "-" in token:
                try:
                    start_str, end_str = token.split("-")
                    start, end = int(start_str), int(end_str)
                    if start > end:
                        print(f"❌ Invalid range: {token}")
                        continue
                    for num in range(start, end + 1):
                        selected_indices.add(num - 1)
                except ValueError:
                    print(f"❌ Invalid range input: {token}")
            else:
                try:
                    num = int(token)
                    selected_indices.add(num - 1)
                except ValueError:
                    print(f"❌ Invalid number: {token}")
        selected_indices = {i for i in selected_indices if 0 <= i < len(sorted_accounts)}
        selected_accounts = [sorted_accounts[i] for i in sorted(selected_indices)]
        
        if not selected_accounts:
            print("❌ No valid accounts selected. Please try again.")
            return select_accounts(device_accounts)
        
        print("\nYou've selected the following accounts:")
        for idx, account in enumerate(selected_accounts, 1):
            print(f"{idx}. {account}")
        
        removal_input = input(
            "\nIf you want to remove any accounts, enter their numbers (e.g., 2,4 or 1-3), "
            "or press Enter to continue: "
        ).strip()
        if removal_input:
            removal_indices = set()
            for token in removal_input.split(","):
                token = token.strip()
                if "-" in token:
                    try:
                        start_str, end_str = token.split("-")
                        start, end = int(start_str), int(end_str)
                        if start > end:
                            print(f"❌ Invalid range: {token}")
                            continue
                        for num in range(start, end + 1):
                            removal_indices.add(num - 1)
                    except ValueError:
                        print(f"❌ Invalid range input: {token}")
                else:
                    try:
                        num = int(token)
                        removal_indices.add(num - 1)
                    except ValueError:
                        print(f"❌ Invalid number: {token}")
            removal_indices = {i for i in removal_indices if 0 <= i < len(selected_accounts)}
            if removal_indices:
                selected_accounts = [
                    account for idx, account in enumerate(selected_accounts) if idx not in removal_indices
                ]
                print("\nUpdated selection:")
                for idx, account in enumerate(selected_accounts, 1):
                    print(f"{idx}. {account}")
        return selected_accounts

# New helper function for fetching valid usernames from the Active Accounts table:
def get_valid_usernames_for_model(api_key, base_id, active_accounts_table_id, model_name):
    """
    Fetch the list of valid usernames for a given model from the 'Active Accounts' table.
    Since the table only contains a 'Username' field, this function fetches all records.
    Returns a set of usernames (strings).
    """
    from pyairtable import Api
    try:
        api = Api(api_key)
        base = api.base(base_id)
        table = base.table(active_accounts_table_id)
        records = table.all()
        valid_usernames = set()
        for rec in records:
            fields = rec.get("fields", {})
            username = fields.get("Username")
            if username:
                valid_usernames.add(username.strip().lower())
        return valid_usernames
    except Exception as e:
        print(f"❌ Error fetching valid usernames for model '{model_name}': {e}")
        return set()

def main():
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
        and folder.lower() not in ['.stm', '.trash', 'trash', 'temp', 'temporary', 'camera', 'crash_log', 'log']
    ]

    if not device_accounts:
        print("❌ No accounts found in device folder.")
        exit()

    # Fetch valid usernames from the Active Accounts table.
    active_accounts_table_id = model_config.get('active_accounts_table_id')
    if not active_accounts_table_id:
        print("❌ No 'active_accounts_table_id' found in config for this model.")
        exit()

    valid_usernames = get_valid_usernames_for_model(
        api_key=airtable_pat,
        base_id=model_config['base_id'],
        active_accounts_table_id=active_accounts_table_id,
        model_name=selected_model
    )

    # Filter device accounts to only those matching valid usernames (case-insensitive).
    filtered_device_accounts = [
        acc for acc in device_accounts
        if acc.strip().lower() in valid_usernames
    ]

    if not filtered_device_accounts:
        print("❌ No valid accounts found on the device for this model.")
        exit()

    selected_accounts = select_accounts(filtered_device_accounts)
    print(f"\n✅ Final selected accounts: {', '.join(selected_accounts)}")

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

if __name__ == "__main__":
    main()

