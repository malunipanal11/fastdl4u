from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import os
import json

# Load service account JSON
SERVICE_ACCOUNT_FILE = "service_account.json"

gauth = GoogleAuth()
gauth.LoadServiceConfigSettings()
gauth.ServiceAuth()  # Assumes service_account.json is in root

drive = GoogleDrive(gauth)

def upload_to_drive(local_file, drive_file_name, folder_name=None):
    file = drive.CreateFile({'title': drive_file_name})
    if folder_name:
        folder_id = get_folder_id(folder_name)
        if folder_id:
            file['parents'] = [{'id': folder_id}]
    file.SetContentFile(local_file)
    file.Upload()
    return file['id']

def get_folder_id(folder_name):
    file_list = drive.ListFile({
        'q': f"title='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    }).GetList()
    if file_list:
        return file_list[0]['id']
    return None

def list_files_in_folder(folder_name):
    folder_id = get_folder_id(folder_name)
    if not folder_id:
        return []
    file_list = drive.ListFile({
        'q': f"'{folder_id}' in parents and trashed=false"
    }).GetList()
    return [{'title': f['title'], 'id': f['id']} for f in file_list]

def get_random_file(folder_name):
    import random
    files = list_files_in_folder(folder_name)
    return random.choice(files) if files else None
