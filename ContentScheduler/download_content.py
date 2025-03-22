import os
import csv
import json
import pandas as pd
import requests
import argparse
import datetime
import sys
import re
import io
import platform
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from pyairtable import Api
from pyairtable.formulas import match
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from functools import partial


# Define the scopes required for Google Drive API
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def extract_file_id(drive_url):
    """Extract the file ID from a Google Drive URL."""
    patterns = [
        r'/open\?id=([a-zA-Z0-9_-]+)',
        r'/file/d/([a-zA-Z0-9_-]+)',
        r'id=([a-zA-Z0-9_-]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, drive_url)
        if match:
            return match.group(1)
    
    return None

def authenticate_google_drive():
    """Authenticate with Google Drive API."""
    print("Authenticating with Google Drive...")
    
    # Get the directory where this script is located
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define paths relative to the script location
    credentials_path = os.path.join(current_dir, 'credentials.json')
    token_path = os.path.join(current_dir, 'token.json')
    
    creds = None
    
    # Check if token.json exists (for saved credentials)
    if os.path.exists(token_path):
        try:
            with open(token_path, 'r') as token:
                creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        except Exception as e:
            print(f"Error reading token file: {e}")
            creds = None
    
    # If credentials don't exist or are invalid, go through auth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Error refreshing credentials: {e}")
                creds = None
        
        # If still no valid credentials, do the full auth flow
        if not creds:
            if not os.path.exists(credentials_path):
                raise FileNotFoundError(f"Google credentials file not found at: {credentials_path}")
            
            try:
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
                
                # Save the credentials for future runs
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
            except Exception as e:
                raise Exception(f"Failed to authenticate with Google Drive: {e}")
    
    return creds

def detect_file_extension(drive_service, file_id, url):
    """
    Detect file extension from Google Drive metadata.
    Falls back to URL parsing if metadata doesn't have the extension.
    """
    try:
        # First try to get the extension from Google Drive metadata
        file_metadata = drive_service.files().get(fileId=file_id, fields="name,mimeType").execute()
        
        # Extract extension from original filename
        original_name = file_metadata.get('name', '')
        if '.' in original_name:
            ext = original_name.split('.')[-1].lower()
            if ext in ['jpg', 'jpeg', 'png', 'gif', 'mp4', 'mov', 'mp3', 'wav']:
                return f'.{ext}'
        
        # If no extension in filename, try from MIME type
        mime_type = file_metadata.get('mimeType', '')
        mime_to_ext = {
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'video/mp4': '.mp4',
            'video/quicktime': '.mov',
            'video/x-msvideo': '.avi',
            'audio/mpeg': '.mp3',
            'audio/wav': '.wav'
        }
        
        if mime_type in mime_to_ext:
            return mime_to_ext[mime_type]
            
        # Try to extract from URL as a fallback
        url_parts = url.split('/')
        if url_parts and len(url_parts) > 0:
            filename = url_parts[-1]
            # Check if the filename in URL has an extension
            if '.' in filename:
                ext = filename.split('.')[-1].lower()
                if ext in ['jpg', 'jpeg', 'png', 'gif', 'mp4', 'mov']:
                    return f'.{ext}'
        
        # Default to .mp4 for video content
        return '.mp4'
        
    except Exception as e:
        print(f"Error detecting file extension: {e}")
        return '.mp4'

def download_file(drive_service, file_id, output_folder, filename=None):
    """Download a file from Google Drive."""
    try:
        # Get file metadata to determine the name and MIME type
        file_metadata = drive_service.files().get(fileId=file_id).execute()
        
        # Use the original filename from Drive if no custom name provided
        if not filename:
            filename = file_metadata['name']
        
        # Create output folder if it doesn't exist
        os.makedirs(output_folder, exist_ok=True)
        
        # Create a full output path
        output_path = os.path.join(output_folder, filename)
        
        # Download the file
        request = drive_service.files().get_media(fileId=file_id)
        with io.FileIO(output_path, 'wb') as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                print(f"Download {int(status.progress() * 100)}%")
        
        return output_path
    
    except Exception as e:
        print(f"Error downloading file {file_id}: {e}")
        return None

def ensure_dir_exists(directory):
    """Ensure a directory exists, creating it if necessary."""
    Path(directory).mkdir(parents=True, exist_ok=True)

def select_profile():
    """Interactive profile selection."""
    profiles = ['mia', 'maddison', 'alexis']
    print("\nChoose a profile:")
    for idx, profile in enumerate(profiles, 1):
        print(f"[{idx}] {profile.capitalize()}")
    
    while True:
        try:
            choice = input("Enter choice: ")
            if choice.isdigit() and 1 <= int(choice) <= len(profiles):
                return profiles[int(choice) - 1]
            print("Invalid choice. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")

def get_record_count():
    """Get the number of records to process."""
    while True:
        try:
            count = input("\nHow many records do you want to process? (default: all) ")
            if not count:
                return None
            count = int(count)
            if count > 0:
                return count
            print("Please enter a positive number.")
        except ValueError:
            print("Invalid input. Please enter a number.")

from concurrent.futures import ThreadPoolExecutor
from functools import partial
from tqdm import tqdm

def process_content_schedule(
    airtable_pat, base_id, table_id, view_id, output_folder, _, profile, device, record_limit=None, update_all=False
):
    print("Authenticating with Airtable...")
    api = Api(airtable_pat)
    base = api.base(base_id)
    table = base.table(table_id)

    # Build Airtable formula
    formula_parts = []
    if not update_all and profile:
        formula_parts.append(f"LOWER({{Username}}) = LOWER('{profile}')")
    if view_id:
        formula_parts.append("NOT(IS_AFTER(TODAY(), DATEADD({Schedule Date}, 1, 'days')))")
    formula = "AND(" + ",".join(formula_parts) + ")" if formula_parts else None
    fetch_limit = record_limit * 2 if record_limit else None

    print("\n🔍 Airtable Query Details:")
    print(f"→ Profile: {profile}")
    print(f"→ Update All: {update_all}")
    print(f"→ Formula: {formula if formula else 'No filtering'}")
    print(f"→ View ID: {view_id if view_id else 'No view specified'}")
    print(f"→ Record Limit: {fetch_limit if fetch_limit else 'No limit'}")

    try:
        records = table.all(formula=formula, max_records=fetch_limit)
    except Exception as e:
        print(f"❌ Error fetching records: {e}")
        import traceback
        print(traceback.format_exc())
        return None

    print("\n🔍 Analyzing Records:")
    data = []
    for record in records:
        fields = record.get("fields", {})
        fields['id'] = record['id']
        media_url = fields.get("media_file_path", "")
        if media_url and "drive.google.com" in media_url:
            data.append(fields)

    print(f"\n📊 Valid records with Drive URLs: {len(data)}")
    if not data:
        print("❌ No valid records found with Google Drive URLs")
        return None

    df = pd.DataFrame(data)
    if 'media_file_path' not in df.columns:
        print("❌ Missing media_file_path column.")
        return None

    print("\n🔐 Authenticating with Google Drive...")
    creds = authenticate_google_drive()
    drive_service = build('drive', 'v3', credentials=creds)

    print(f"\n📥 Downloading Content for {profile.capitalize()} (parallel)...")

    def download_row(index, row, creds, output_folder, pbar):
        try:
            # ✅ Build a drive_service inside each thread
            drive_service = build('drive', 'v3', credentials=creds)

            drive_url = row['media_file_path']
            if not isinstance(drive_url, str) or 'drive.google.com' not in drive_url:
                pbar.update(1)
                return None

            file_id = extract_file_id(drive_url)
            if not file_id:
                pbar.update(1)
                return None

            file_metadata = drive_service.files().get(fileId=file_id, fields="name,mimeType").execute()
            original_name = file_metadata.get('name', '')
            extension = '.mp4'

            if '.' in original_name:
                ext = original_name.split('.')[-1].lower()
                if ext in ['jpg', 'jpeg', 'png', 'gif']:
                    extension = f'.{ext}'
                    subfolder = 'images'
                elif ext in ['mp4', 'mov']:
                    extension = f'.{ext}'
                    subfolder = 'reels'
                else:
                    subfolder = 'reels'
            else:
                subfolder = 'reels'

            post_date = str(row.get('schedule_date', datetime.datetime.now().strftime('%Y-%m-%d')))
            post_date = post_date.replace('/', '-').replace('\\', '-')
            username = row.get('Username', 'unknown')
            caption = row.get('caption', '')

            safe_username = re.sub(r'[^\w\s-]', '', str(username))
            post_date_clean = re.sub(r'[^\w\s-]', '', str(post_date))
            caption_words = '-'.join(re.sub(r'[^\w\s-]', '', caption.lower()).split()[:3]) if caption else f'post-{index + 1}'
            filename = f"{post_date_clean}_{safe_username}_{caption_words}{extension}"

            output_dir = os.path.join(output_folder, subfolder)
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, filename)

            if os.path.exists(output_path):
                print(f"⏭️ Skipping existing: {output_path}")
                row['media_file_path'] = os.path.abspath(output_path)
                pbar.update(1)
                return row

            request = drive_service.files().get_media(fileId=file_id)
            with io.FileIO(output_path, 'wb') as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()

            print(f"✓ Success: {output_path}")
            row['media_file_path'] = os.path.abspath(output_path)
            pbar.update(1)
            return row

        except Exception as e:
            print(f"✗ Error processing record {index + 1}: {e}")
            pbar.update(1)
            return None


    successful_records = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        with tqdm(total=len(df), desc="📥 Downloading", unit="file") as pbar:
            download_fn = partial(download_row, creds=creds, output_folder=output_folder, pbar=pbar)
            futures = [executor.submit(download_fn, idx, row) for idx, row in df.iterrows()]
            for future in futures:
                result = future.result()
                if result is not None:
                    successful_records.append(result)

    if not successful_records:
        print("❌ No successful downloads.")
        return None

    output_df = pd.DataFrame(successful_records)
    output_df.columns = [col.lower().replace(' (24h)', '').replace(' ', '_') for col in output_df.columns]
    output_df.insert(0, 'device_id', device['id'])
    if 'username' not in output_df.columns:
        output_df['username'] = 'unknown'

    print(f"\n✅ {len(successful_records)} file(s) downloaded successfully.")
    return output_df

