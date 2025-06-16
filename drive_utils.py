import os
import io
import json
import base64
import random
from dotenv import load_dotenv

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Load .env file if available (for local development)
load_dotenv()

# Get and decode service account credentials from environment
b64_credentials = os.getenv("GOOGLE_CREDENTIALS_B64")
if not b64_credentials:
    raise RuntimeError("Missing GOOGLE_CREDENTIALS_B64 environment variable")

try:
    credentials_json = json.loads(base64.b64decode(b64_credentials).decode("utf-8"))
except Exception as e:
    raise RuntimeError("Failed to decode GOOGLE_CREDENTIALS_B64: " + str(e))

# Authenticate with Google Drive
SCOPES = ["https://www.googleapis.com/auth/drive"]
credentials = service_account.Credentials.from_service_account_info(
    credentials_json, scopes=SCOPES
)
drive_service = build("drive", "v3", credentials=credentials)

# Folder name to ID map (replace with actual folder IDs if needed)
FOLDER_MAP = {
    "BotFiles": "YOUR_FOLDER_ID_HERE"  # Replace with actual folder ID
}

def upload_to_drive(file_path, drive_filename, folder_name="BotFiles"):
    folder_id = FOLDER_MAP.get(folder_name)
    if not folder_id:
        raise ValueError(f"Unknown folder name: {folder_name}")

    file_metadata = {
        "name": drive_filename,
        "parents": [folder_id]
    }
    media = MediaFileUpload(file_path, resumable=True)
    file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()
    return file.get("id")

def list_files_in_folder(folder_name="BotFiles"):
    folder_id = FOLDER_MAP.get(folder_name)
    if not folder_id:
        raise ValueError(f"Unknown folder name: {folder_name}")

    query = f"'{folder_id}' in parents and trashed = false"
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    return results.get("files", [])

def get_random_file(folder_name="BotFiles"):
    files = list_files_in_folder(folder_name)
    return random.choice(files) if files else None
