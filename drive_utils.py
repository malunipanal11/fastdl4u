from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

# Configure PyDrive to use a service account
gauth = GoogleAuth()
gauth.settings['client_config_backend'] = 'service'
gauth.settings['service_config'] = {
    "client_service_email": "fastdl4u@steel-league-463017-t4.iam.gserviceaccount.com",
    "private_key_file": "service_account.json"
}

gauth.ServiceAuth()
drive = GoogleDrive(gauth)

def upload_to_drive(file_path, title, parent_id):
    file = drive.CreateFile({'title': title, 'parents': [{'id': parent_id}]})
    file.SetContentFile(file_path)
    file.Upload()
    return file['id']

def get_random_file(category):
    # Simulated random file selection
    return {"file_id": "FAKE_FILE_ID"}
