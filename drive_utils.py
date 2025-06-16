from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import os

# Authenticate using service_account.json
gauth = GoogleAuth()
gauth.LoadServiceConfigFile("service_account.json")  # 👈 This must match your uploaded file
drive = GoogleDrive(gauth)

def upload_to_drive(file_path, title, parent_id):
    file = drive.CreateFile({'title': title, 'parents': [{'id': parent_id}]})
    file.SetContentFile(file_path)
    file.Upload()
    return file['id']

def get_random_file(category):
    # Placeholder logic: replace this with actual category-based retrieval
    return {"file_id": "FAKE_FILE_ID"}
