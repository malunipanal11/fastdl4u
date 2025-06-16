import os
import io
import json
import random
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from pydrive2.settings import InvalidConfigError
from oauth2client.service_account import ServiceAccountCredentials

# Load credentials from Render environment variable
credentials_json = json.loads(os.getenv("GOOGLE_CREDENTIALS_JSON"))

# Authenticate using service account
gauth = GoogleAuth()
gauth.auth_method = 'service'
gauth.credentials = ServiceAccountCredentials.from_json_keyfile_dict(
    credentials_json,
    scopes=["https://www.googleapis.com/auth/drive"]
)
drive = GoogleDrive(gauth)


def get_folder_id(folder_name):
    query = f"title='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    folder_list = drive.ListFile({'q': query}).GetList()
    if folder_list:
        return folder_list[0]['id']
    else:
        # Create folder if it doesn't exist
        folder_metadata = {
            'title': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        folder = drive.CreateFile(folder_metadata)
        folder.Upload()
        return folder['id']


def upload_to_drive(file_content, filename, folder_name):
    folder_id = get_folder_id(folder_name)

    file_metadata = {
        'title': filename,
        'parents': [{'id': folder_id}]
    }

    file_drive = drive.CreateFile(file_metadata)
    if isinstance(file_content, io.BytesIO):
        file_drive.content = file_content
    else:
        raise ValueError("file_content must be a BytesIO object.")
    
    file_drive.Upload()
    return file_drive['id']


def list_files_in_folder(folder_name):
    folder_id = get_folder_id(folder_name)
    query = f"'{folder_id}' in parents and trashed=false"
    file_list = drive.ListFile({'q': query}).GetList()
    return [{'title': file['title'], 'id': file['id']} for file in file_list]


def get_random_file(folder_name):
    files = list_files_in_folder(folder_name)
    return random.choice(files) if files else None
