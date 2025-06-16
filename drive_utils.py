from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import random

# Authenticate using service account
gauth = GoogleAuth()
gauth.LoadServiceConfigFile("service_account.json")
gauth.ServiceAuth()

drive = GoogleDrive(gauth)

# ✅ Create a folder if it doesn't exist
def get_or_create_folder(folder_name, parent_id=None):
    query = f"title = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    if parent_id:
        query += f" and '{parent_id}' in parents"

    file_list = drive.ListFile({'q': query}).GetList()
    if file_list:
        return file_list[0]['id']

    # Folder not found, create it
    folder_metadata = {
        'title': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if parent_id:
        folder_metadata['parents'] = [{'id': parent_id}]

    folder = drive.CreateFile(folder_metadata)
    folder.Upload()
    return folder['id']

# ✅ Upload file to folder by name
def upload_to_drive(file_path, title, folder_name):
    folder_id = get_or_create_folder(folder_name)
    file = drive.CreateFile({'title': title, 'parents': [{'id': folder_id}]})
    file.SetContentFile(file_path)
    file.Upload()
    return file['id']

# ✅ List files in a specific folder
def list_files_in_folder(folder_name):
    folder_id = get_or_create_folder(folder_name)
    query = f"'{folder_id}' in parents and trashed = false"
    files = drive.ListFile({'q': query}).GetList()
    return [{'id': f['id'], 'title': f['title']} for f in files]

# ✅ Random file (example usage)
def get_random_file(folder_name):
    files = list_files_in_folder(folder_name)
    return random.choice(files) if files else None
