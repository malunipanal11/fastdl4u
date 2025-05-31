import requests
from io import BytesIO

# Replace with your Gofile API token or leave blank if public
API_TOKEN = None

# In-memory store for uploaded files by category
uploaded_files = {
    "images": [],
    "videos": [],
    "audios": [],
    "files": []
}

def upload_to_gofile(file_bytes: BytesIO, filename: str, category: str):
    response = requests.get("https://api.gofile.io/getServer")
    server = response.json()["data"]["server"]

    files = {
        "file": (filename, file_bytes)
    }

    data = {
        "token": API_TOKEN
    } if API_TOKEN else {}

    upload_url = f"https://{server}.gofile.io/uploadFile"
    r = requests.post(upload_url, files=files, data=data)
    result = r.json()

    if result["status"] == "ok":
        file_data = {
            "name": filename,
            "url": result["data"]["downloadPage"],
            "code": result["data"]["code"]
        }
        uploaded_files[category].append(file_data)
        return file_data["url"], file_data["code"]
    else:
        raise Exception("Upload failed")


def get_files_by_type(category: str):
    return uploaded_files.get(category, [])
