import requests
from io import BytesIO
import uuid

API_TOKEN = None

# In-memory store
uploaded_files = {
    "images": [],
    "videos": [],
    "audios": [],
    "files": [],
    "secret": [],
    "links": []
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
            "id": str(uuid.uuid4()),
            "name": filename,
            "url": result["data"]["downloadPage"],
            "code": result["data"]["code"]
        }
        uploaded_files[category].append(file_data)
        return file_data["url"], file_data["code"]
    else:
        raise Exception("Upload failed")

def add_secret(text: str):
    code = str(uuid.uuid4())[:8]
    item = {
        "id": str(uuid.uuid4()),
        "type": "secret",
        "text": text,
        "code": code,
        "url": f"🔒 Secret: {text}",
    }
    uploaded_files["secret"].append(item)
    return item["url"], code

def add_link(link: str):
    code = str(uuid.uuid4())[:8]
    item = {
        "id": str(uuid.uuid4()),
        "type": "link",
        "url": link,
        "code": code
    }
    uploaded_files["links"].append(item)
    return item["url"], code

def get_random_file(category: str):
    from random import choice
    return choice(uploaded_files.get(category, [])) if uploaded_files.get(category) else None

def get_file_by_code(code: str):
    for cat_files in uploaded_files.values():
        for file in cat_files:
            if file.get("code") == code:
                return file
    return None

def get_all_files_by_type(category: str):
    return uploaded_files.get(category, [])

def delete_file(file_id: str):
    for category in uploaded_files:
        uploaded_files[category] = [f for f in uploaded_files[category] if f["id"] != file_id]
