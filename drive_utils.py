import os
import json
import base64
import random
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Load credentials from base64-encoded env var
b64_creds = os.getenv("GOOGLE_CREDENTIALS_B64")
if not b64_creds:
    raise RuntimeError("Missing GOOGLE_CREDENTIALS_B64 environment variable")

try:
    credentials_json = json.loads(base64.b64decode(b64_creds).decode())
except Exception as e:
    raise RuntimeError("Invalid GOOGLE_CREDENTIALS_B64 format") from e

SCOPES = ["https://www.googleapis.com/auth/drive"]
credentials = service_account.Credentials.from_service_account_info(credentials_json, scopes=SCOPES)
service = build("drive", "v3", credentials=credentials)

def get_folder_id(folder_name):
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
    results = service.files().list(q=query, spaces='drive', fields='files(id)').execute()
    files = results.get("files", [])
    if files:
        return files[0]["id"]
    # Create folder if not found
    file_metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder"
    }
    folder = service.files().create(body=file_metadata, fields="id").execute()
    return folder.get("id")

def upload_to_drive(file_path, filename, folder_name):
    folder_id = get_folder_id(folder_name)
    file_metadata = {
        "name": filename,
        "parents": [folder_id]
    }
    media = MediaFileUpload(file_path, resumable=True)
    file = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    return file.get("id")

def list_files_in_folder(folder_name):
    folder_id = get_folder_id(folder_name)
    query = f"'{folder_id}' in parents"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    return results.get("files", [])

def get_random_file(folder_name):
    files = list_files_in_folder(folder_name)
    if not files:
        return None
    return random.choice(files)
