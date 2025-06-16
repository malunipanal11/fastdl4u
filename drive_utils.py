import os
import json
import random
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

# Load credentials from environment variable
service_account_info = json.loads(os.environ["GOOGLE_CREDENTIALS_JSON"])

gauth = GoogleAuth()
gauth.settings['client_config_backend'] = 'service'
gauth.settings['service_config'] = {
    "client_service_email": service_account_info["client_email"],
    "client_user_email": service_account_info["client_email"],
    "private_key_file": None,
    "private_key": service_account_info["private_key"],
    "client_id": service_account_info["client_id"],
    "client_secret": "unused"
}

gauth.ServiceAuth()
drive = GoogleDrive(gauth)

def upload_to_drive(filename: str, content: str) -> str:
    """Uploads content to Google Drive with a given filename and returns file ID."""
    file = drive.CreateFile({'title': filename})
    file.SetContentString(content)
    file.Upload()
    return file['id']

def get_random_file() -> str:
    """Returns the title of a random file from Google Drive."""
    file_list = drive.ListFile({'q': "'root' in parents and trashed=false"}).GetList()
    if not file_list:
        return "No files found."
    file = random.choice(file_list)
    return f"{file['title']} (ID: {file['id']})"
