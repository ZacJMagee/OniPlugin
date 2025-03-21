import os
import sqlite3
import uuid
import re
from datetime import datetime

# ✅ Base directory where Android devices are stored
BASE_DIR = "/home/zacm/onimator"

def generate_unique_post_id():
    return str(uuid.uuid4())

def insert_post(db_path, file_location, caption, post_music, post_type, post_location, scheduled_date, is_published=0):
    """Insert a test post into the scheduled_post database."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        post_id = generate_unique_post_id()

        # Ensure scheduled_date follows "YYYY-MM-DD HH:MM" format
        try:
            parsed_date = datetime.strptime(scheduled_date, "%Y-%m-%d %H:%M")
            formatted_scheduled_date = parsed_date.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            print(f"❌ Invalid date/time format: '{scheduled_date}'")
            return

        # Generate current timestamp for "date" column
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M")

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
        print(f"✅ Inserted test post: {post_id} -> {formatted_scheduled_date} (Created on: {current_date})")

    except Exception as e:
        print(f"❌ Error inserting post: {e}")

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
def select_models(device_folder):
    """Let the user select one or more accounts (models) inside the device folder."""
    path = os.path.join(BASE_DIR, device_folder)
    models = [
        folder for folder in os.listdir(path)
        if os.path.isdir(os.path.join(path, folder)) and not folder.startswith('.')
    ]

    if not models:
        print("❌ No valid models found in the selected device folder.")
        return None

    print("\n👤 Available Models:")
    for i, model in enumerate(models, 1):
        print(f"{i}. {model}")

    selected = input("Select model numbers (comma-separated, or press Enter for all): ")
    if not selected:
        return models

    try:
        indices = [int(x.strip()) - 1 for x in selected.split(',')]
        return [models[i] for i in indices if 0 <= i < len(models)]
    except ValueError:
        print("❌ Invalid selection format.")
        return None

# 🔥 Run selection + Insert test data
if __name__ == "__main__":
    devices = get_connected_devices()
    if not devices:
        print("❌ No devices found.")
        exit()

    selected_device = select_device(devices)
    if not selected_device:
        print("❌ No device selected.")
        exit()

    selected_models = select_models(selected_device)
    if not selected_models:
        print("❌ No models selected.")
        exit()

    # Sample test data
    test_data = [
        {
            "file_location": "/home/zacm/media/test1.jpg",
            "caption": "Test post 1",
            "post_music": "Test Song 1",
            "post_type": "image",
            "post_location": "New York",
            "scheduled_date": "2025-03-21 14:30",
            "is_published": 0
        },
        {
            "file_location": "/home/zacm/media/test2.mp4",
            "caption": "Test post 2",
            "post_music": "Test Song 2",
            "post_type": "video",
            "post_location": "Los Angeles",
            "scheduled_date": "2025-03-22 10:00",
            "is_published": 0
        }
    ]

    for model in selected_models:
        db_path = os.path.join(BASE_DIR, selected_device, model, "scheduled_post.db")
        print(f"\n📂 Processing model: {model}")
        print(f"→ Using DB: {db_path}")

        if os.path.exists(db_path):
            for post in test_data:
                insert_post(
                    db_path=db_path,
                    file_location=post["file_location"],
                    caption=post["caption"],
                    post_music=post["post_music"],
                    post_type=post["post_type"],
                    post_location=post["post_location"],
                    scheduled_date=post["scheduled_date"],
                    is_published=post["is_published"]
                )
        else:
            print(f"❌ Database not found for model: {model}")

