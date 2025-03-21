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

# Define the scopes required for Google Drive API
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def run_first_time_setup():
    """Run first-time setup and installation process."""
    print("\n=== Content Scheduler First-Time Setup ===")
    
    # Create config directory
    config_dir = Path.home() / '.content_scheduler'
    config_dir.mkdir(exist_ok=True)
    
    # Create installation marker file
    install_marker = config_dir / 'installed'
    
    if not install_marker.exists():
        print("\nWelcome to Content Scheduler!")
        print("This appears to be your first time running the tool.")
        print("Let's set up your environment...")
        
        # Create necessary directories
        downloads_dir = Path.cwd() / 'downloaded_media'
        downloads_dir.mkdir(exist_ok=True)

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
    # Get credentials file path from env or use default
    credentials_file = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
    token_file = os.getenv('GOOGLE_TOKEN_FILE', 'token.json')
    
    creds = None
    
    # Check if token.json exists (for saved credentials)
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_info(
            info=json.loads(open(token_file).read()), 
            scopes=SCOPES
        )
    
    # If credentials don't exist or are invalid, go through auth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for future runs
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
    
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

def get_system_info():
    """Get system information for debugging."""
    return {
        'system': platform.system(),
        'release': platform.release(),
        'version': platform.version(),
        'machine': platform.machine(),
        'processor': platform.processor()
    }

def process_content_schedule(airtable_pat, base_id, table_id, view_id, output_folder, output_csv, profile, device, record_limit=None):
    """
    Process the content schedule:
    1. Fetch records from Airtable
    2. Download media files from Google Drive
    3. Create a new CSV with local file paths
    
    Args:
        airtable_pat: Airtable Personal Access Token
        base_id: Airtable Base ID
        table_id: Airtable Table ID
        view_id: Optional Airtable View ID
        output_folder: Folder to save downloaded media
        output_csv: Output CSV file path
        test_mode: If True, process only the first 2 records
    """
    print("Authenticating with Airtable...")
    api = Api(airtable_pat)
    
    # Use the specified record limit
    max_records = record_limit if record_limit else None
    
    # Get the base and table
    print(f"Connecting to base: {base_id}")
    base = api.base(base_id)
    
    print(f"Connecting to table: {table_id}")
    table = base.table(table_id)
    
    # If we have a record limit, fetch more records initially to ensure we get enough valid ones
    fetch_limit = max_records * 2 if max_records else None
    
    print(f"Fetching records from Airtable{' (Limited records)' if max_records else ''}...")
    if view_id:
        records = table.all(view=view_id, max_records=fetch_limit)
    else:
        records = table.all(max_records=fetch_limit)
    
    # Extract fields from records and filter for records with media URLs
    data = []
    for record in records:
        fields = record['fields']
        if 'media_file_path' in fields and fields['media_file_path'] and 'drive.google.com' in fields['media_file_path']:
            data.append(fields)
            # Break if we have enough valid records
            if max_records and len(data) >= max_records:
                break
    
    # If we still don't have enough records, try fetching more
    if max_records and len(data) < max_records:
        print(f"Warning: Could only find {len(data)} valid records with media URLs out of {len(records)} records.")
        # Fetch more records if available
        while len(data) < max_records:
            more_records = table.all(max_records=fetch_limit, offset=len(records))
            if not more_records:  # No more records available
                break
            records.extend(more_records)
            for record in more_records:
                fields = record['fields']
                if 'media_file_path' in fields and fields['media_file_path'] and 'drive.google.com' in fields['media_file_path']:
                    data.append(fields)
                    if len(data) >= max_records:
                        break
    
    print(f"Found {len(data)} records with valid media URLs.")
    
    df = pd.DataFrame(data)
    
    # Create a copy of the dataframe for output
    output_df = pd.DataFrame(columns=df.columns)  # Empty DataFrame with same columns
    successful_records = []  # Track successful downloads
    
    # Identify the column with Google Drive links
    media_link_column = 'media_file_path'  # Adjust based on your actual column name
    
    # Check if the media link column exists
    if media_link_column not in df.columns:
        print(f"Warning: Media link column '{media_link_column}' not found in the data")
        print(f"Available columns: {', '.join(df.columns)}")
        return df
    
    # Authenticate with Google Drive
    print("Authenticating with Google Drive...")
    creds = authenticate_google_drive()
    drive_service = build('drive', 'v3', credentials=creds)
    
    # Count for progress tracking
    total_records = len(df)
    success_count = 0
    fail_count = 0
    
    # Track failed downloads for retry
    failed_downloads = []
    
    print(f"\nDownloading Content for {profile.capitalize()}...")
    for index, row in df.iterrows():
        try:
            record_num = index + 1
            print(f"\nProcessing record {record_num}/{total_records}")
            
            drive_url = row[media_link_column]
            
            if pd.notna(drive_url) and isinstance(drive_url, str) and 'drive.google.com' in drive_url:
                print(f"Found Google Drive URL: {drive_url}")
                
                # Extract file ID from the URL
                file_id = extract_file_id(drive_url)
                
                if file_id:
                    print(f"Extracted file ID: {file_id}")
                    
                    # Create a filename based on other row data
                    post_date = str(row.get('schedule_date', datetime.datetime.now().strftime('%Y-%m-%d')))
                    post_date = post_date.replace('/', '-').replace('\\', '-')
                    
                    username = row.get('Username', 'unknown')
                    caption = row.get('caption', '')
                    
                    # Generate a safe base filename (without extension)
                    safe_username = re.sub(r'[^\w\s-]', '', str(username))
                    post_date_clean = re.sub(r'[^\w\s-]', '', str(post_date))
                    
                    # Create a unique identifier from the first few words of the caption
                    if caption and isinstance(caption, str):
                        # Get first 3 words of caption or caption ID
                        caption_words = re.sub(r'[^\w\s-]', '', caption.lower())
                        caption_words = '-'.join(caption_words.split()[:3])
                    else:
                        caption_words = f"post-{record_num}"
                    
                    # Get file extension from Google Drive (use same approach as test script)
                    print("Getting file metadata for extension detection...")
                    file_metadata = drive_service.files().get(fileId=file_id, fields="name,mimeType").execute()
                    
                    # Extract extension from original filename
                    extension = '.mp4'  # Default
                    original_name = file_metadata.get('name', '')
                    if '.' in original_name:
                        ext = original_name.split('.')[-1].lower()
                        if ext in ['jpg', 'jpeg', 'png', 'gif', 'mp4', 'mov', 'mp3', 'wav']:
                            extension = f'.{ext}'
                            print(f"Extension detected from filename: {extension}")
                    
                    # Generate final filename
                    filename = f"{post_date_clean}_{safe_username}_{caption_words}{extension}"
                    
                    print(f"Downloading: {filename}")
                    
                    # Create output folder if it doesn't exist
                    os.makedirs(output_folder, exist_ok=True)
                    
                    # Create a full output path
                    output_path = os.path.join(output_folder, filename)
                    
                    # Download the file using similar approach to test script
                    print(f"Downloading file to: {output_path}")
                    request = drive_service.files().get_media(fileId=file_id)
                    with io.FileIO(output_path, 'wb') as fh:
                        downloader = MediaIoBaseDownload(fh, request)
                        done = False
                        while not done:
                            status, done = downloader.next_chunk()
                            print(f"Download {int(status.progress() * 100)}%")
                    
                    # Convert to absolute path
                    absolute_path = os.path.abspath(output_path)
                    # Add successful record to our tracking
                    row_data = df.iloc[index].copy()
                    row_data[media_link_column] = absolute_path
                    successful_records.append(row_data)
                    print(f"✓ Success: {absolute_path}")
                    success_count += 1
                    success_count += 1
                else:
                    print(f"❌ Could not extract file ID from: {drive_url}")
                    failed_downloads.append((index, row))
                    fail_count += 1
            else:
                print(f"✗ No valid Google Drive URL found in record")
                fail_count += 1
        except Exception as e:
            print(f"✗ Error processing row {index}: {e}")
            import traceback
    # Create final DataFrame from successful records only
    if successful_records:
        output_df = pd.DataFrame(successful_records)
        
        # Rename columns to lowercase
        output_df.columns = [col.lower().replace(' (24h)', '').replace(' ', '_') for col in output_df.columns]
        
        # Add device_id column
        output_df.insert(0, 'device_id', device['id'])
        
        # Ensure username column exists
        if 'username' not in output_df.columns:
            output_df['username'] = 'unknown'
        
        # Define the exact column order
        desired_columns = [
            'device_id',
            'username',
            'schedule_date',
            'schedule_time',
            'media_file_path',
            'caption',
            'song',
            'post_type',
            'post_location'
        ]
        
        # Ensure all required columns exist
        for col in desired_columns:
            if col not in output_df.columns:
                output_df[col] = ''
        
        # Reorder columns to match exact specification
        output_df = output_df[desired_columns]
        
        # Save the updated dataframe to CSV
        print("\nSaving updated data to CSV...")
        output_df.to_csv(output_csv, index=False)
        print(f"CSV created: {output_csv} with {len(successful_records)} successful records")
    else:
        print("\nNo successful downloads to save to CSV")
    
    # Print summary and handle retries
    print("\nDownload complete!")
    print(f"✔ Successfully downloaded {len(successful_records)} out of {len(df)} requested records")
    if len(successful_records) < len(df):
        print(f"✖ {fail_count} file(s) failed")
        retry = input("Would you like to retry failed downloads? (Y/N) ").lower()
        if retry == 'y':
            print("\nRetrying failed downloads...")
            for index, row in failed_downloads:
                try:
                    drive_url = row[media_link_column]
                    if pd.notna(drive_url) and isinstance(drive_url, str) and 'drive.google.com' in drive_url:
                        file_id = extract_file_id(drive_url)
                        if file_id:
                            # Use the same filename generation logic as before
                            post_date = str(row.get('schedule_date', datetime.datetime.now().strftime('%Y-%m-%d')))
                            post_date = post_date.replace('/', '-').replace('\\', '-')
                            username = row.get('Username', 'unknown')
                            caption = row.get('caption', '')
                            
                            safe_username = re.sub(r'[^\w\s-]', '', str(username))
                            post_date_clean = re.sub(r'[^\w\s-]', '', str(post_date))
                            
                            if caption and isinstance(caption, str):
                                caption_words = re.sub(r'[^\w\s-]', '', caption.lower())
                                caption_words = '-'.join(caption_words.split()[:3])
                            else:
                                caption_words = f"post-{index + 1}"
                            
                            # Get file extension
                            file_metadata = drive_service.files().get(fileId=file_id, fields="name,mimeType").execute()
                            extension = detect_file_extension(drive_service, file_id, drive_url)
                            
                            filename = f"{post_date_clean}_{safe_username}_{caption_words}{extension}"
                            output_path = os.path.join(output_folder, filename)
                            
                            # Retry the download
                            request = drive_service.files().get_media(fileId=file_id)
                            with io.FileIO(output_path, 'wb') as fh:
                                downloader = MediaIoBaseDownload(fh, request)
                                done = False
                                while not done:
                                    status, done = downloader.next_chunk()
                                    print(f"Download {int(status.progress() * 100)}%")
                            
                            absolute_path = os.path.abspath(output_path)
                            # Add retry success to our tracking
                            row_data = df.iloc[index].copy()
                            row_data[media_link_column] = absolute_path
                            successful_records.append(row_data)
                            print(f"✅ Successfully retried download for record {index + 1}")
                            success_count += 1
                            fail_count -= 1
                except Exception as e:
                    print(f"❌ Retry failed for record {index + 1}: {str(e)}")

    # Save the final version of the CSV after retries
    output_df.to_csv(output_csv, index=False)
    print(f"\nAll files processed. CSV created: {output_csv}")
    return output_df


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

def select_device():
    """Interactive device selection."""
    devices = [
        {'id': 'SSKVB20812003091', 'name': 'Huawei Y9s'},
        {'id': 'A7FYD22711011986', 'name': 'Huawei Nova Y90'},
        {'id': 'R3CR40DFCDH', 'name': 'Samsung S21 5G'}
    ]
    print("\nChoose a device:")
    for idx, device in enumerate(devices, 1):
        print(f"[{idx}] {device['name']} ({device['id']})")
    
    while True:
        try:
            choice = input("Enter choice: ")
            if choice.isdigit() and 1 <= int(choice) <= len(devices):
                return devices[int(choice) - 1]
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

def main():
    """Main function to run the Instagram Content Manager."""
    # Check system and print info
    system_info = get_system_info()
    print("System Information:")
    for key, value in system_info.items():
        print(f"  {key}: {value}")
    print()

    # Ensure we're running with the correct Python version
    if sys.version_info < (3, 7):
        print("Error: This script requires Python 3.7 or higher")
        sys.exit(1)

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Instagram Content Manager')
    parser.add_argument('--profile', '-p', type=str, help='Profile to use (mia, maddison, alexis)')
    parser.add_argument('--test', '-t', action='store_true', 
                       help='Run in test mode (process only first 2 records)')
    parser.add_argument('--no-test', action='store_true',
                      help='Run in full mode (process all records)')
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Determine which profile to use
    if args.profile:
        profile = args.profile.lower()
    else:
        profile = select_profile()
    
    print(f"Using profile: {profile.upper()}")
    
    # Select device
    device = select_device()
    print(f"Using device: {device['name']} ({device['id']})")
    
    # Load configuration for the selected profile
    profile_upper = profile.upper()
    # Determine base directory for outputs
    base_dir = Path.cwd()
    downloads_dir = base_dir / 'downloaded_media' / profile
    
    config = {
        'airtable_pat': os.getenv('AIRTABLE_PAT'),
        'base_id': os.getenv(f'{profile_upper}_BASE_ID'),
        'table_id': os.getenv(f'{profile_upper}_TABLE_ID'),
        'view_id': os.getenv(f'{profile_upper}_VIEW_ID'),
        'output_folder': os.getenv(f'{profile_upper}_OUTPUT_FOLDER', str(downloads_dir)),
        'output_csv': os.getenv(f'{profile_upper}_OUTPUT_CSV', f'{profile}_instagram_schedule_{device["id"]}.csv')
    }
    
    # Ensure output directory exists
    ensure_dir_exists(config['output_folder'])
    
    # Check if required config is present
    required_fields = ['airtable_pat', 'base_id', 'table_id']
    missing_fields = [field for field in required_fields if not config[field]]
    if missing_fields:
        print(f"Error: Missing required configuration for profile '{profile}': {', '.join(missing_fields)}")
        print(f"Please update your .env file with the required {profile_upper}_* values.")
        return
    
    print("\nConfiguration:")
    print(f"  Base ID: {config['base_id']}")
    print(f"  Table ID: {config['table_id']}")
    print(f"  Output folder: {config['output_folder']}")
    print(f"  Output CSV: {config['output_csv']}")
    
    # Determine record limit
    if args.test:
        record_limit = 2
    elif args.no_test:
        record_limit = None
    else:
        record_limit = get_record_count()
    
    # Process the content schedule
    print("\nStarting process...")
    process_content_schedule(
        config['airtable_pat'],
        config['base_id'],
        config['table_id'],
        config['view_id'],
        config['output_folder'],
        config['output_csv'],
        profile=profile,
        device=device,
        record_limit=record_limit
    )
    
    print("\nProcessing complete!")
    print("=" * 50)

def check_windows_setup():
    """Check if the Windows environment is properly set up."""
    if platform.system() != 'Windows':
        return True

    requirements = [
        ('credentials.json', 'Google credentials file'),
        ('.env', 'Environment configuration file')
    ]
    
    missing = []
    for file, description in requirements:
        if not Path(file).exists():
            missing.append(f"- {description} ({file})")
    
    if missing:
        print("\nMissing required files:")
        print('\n'.join(missing))
        print("\nPlease ensure these files are in the same directory as the script.")
        print("\nSetup instructions:")
        print("1. Create a .env file with your configuration:")
        print("   AIRTABLE_PAT=your_pat_here")
        print("   MIA_BASE_ID=your_base_id")
        print("   MIA_TABLE_ID=your_table_id")
        print("   etc...")
        print("\n2. Place your Google credentials.json file in the same directory")
        return False
    
    return True

if __name__ == "__main__":
    if check_windows_setup():
        main()
    else:
        print("\nSetup incomplete. Please fix the issues above and try again.")
        sys.exit(1)
