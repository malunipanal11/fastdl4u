from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import os

gauth = GoogleAuth()
gauth.LoadCredentialsFile("credentials.json")
if not gauth.credentials:
    gauth.LocalWebserverAuth()
elif gauth.access_token_expired:
    gauth.Refresh()
else:
    gauth.Authorize()
gauth.SaveCredentialsFile("credentials.json")

drive = GoogleDrive(gauth)

def upload_to_drive(file_path, title, parent_id):
    file = drive.CreateFile({'title': title, 'parents': [{'id': parent_id}]})
    file.SetContentFile(file_path)
    file.Upload()
    return file['id']

def get_random_file(category):
    # Simulated random file selection
    return {"file_id": "FAKE_FILE_ID"}
