import os
import json
import base64
import random
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Decode the service account credentials from base64
credentials_b64 = os.getenv("GOOGLE_CREDENTIALS_B64")
if not credentials_b64:
    raise RuntimeError("Missing GOOGLE_CREDENTIALS_B64 environment variable")

credentials_json = json.loads(base64.b64decode(credentials_b64).decode("utf-8"))

# Create credentials object
credentials = service_account.Credentials.from_service_account_info(
    credentials_json,
    scopes=["https://www.googleapis.com/auth/drive"]
)

drive_service = build("drive", "v3", credentials=credentials)

def upload_to_drive(local_file_path, file_name, folder_name):
    # Search for the folder
    response = drive_service.files().list(
        q=f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false",
        spaces="drive",
        fields="files(id, name)"
    ).execute()

    folder_id = None
    if response["files"]:
        folder_id = response["files"][0]["id"]
    else:
        # Create folder if it doesn't exist
        file_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder"
        }
        file = drive_service.files().create(body=file_metadata, fields="id").execute()
        folder_id = file.get("id")

    file_metadata = {
        "name": file_name,
        "parents": [folder_id]
    }
    media = MediaFileUpload(local_file_path)
    uploaded_file = drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    return uploaded_file.get("id")

def list_files_in_folder(folder_name):
    folder_response = drive_service.files().list(
        q=f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false",
        spaces="drive",
        fields="files(id, name)"
    ).execute()

    if not folder_response["files"]:
        return []

    folder_id = folder_response["files"][0]["id"]

    files_response = drive_service.files().list(
        q=f"'{folder_id}' in parents and trashed=false",
        spaces="drive",
        fields="files(id, name)"
    ).execute()

    return files_response.get("files", [])

def get_random_file(folder_name):
    files = list_files_in_folder(folder_name)
    if not files:
        return None
    return random.choice(files)
