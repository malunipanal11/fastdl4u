import requests
import os
import random
import string
import json

GOFILE_API = "https://api.gofile.io"
UPLOAD_FOLDER = "storage"  # Local temp storage before upload

# Mock database
FILE_DB = {}

# Create upload folder if not exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def generate_code(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def upload_to_gofile(filepath, category="images"):
    """Uploads file to Gofile under the appropriate folder and returns (url, file_id)"""
    with open(filepath, 'rb') as f:
        response = requests.post(f"{GOFILE_API}/uploadFile", files={"file": f})
    data = response.json()
    if not data["status"] == "ok":
        raise Exception("Failed to upload to Gofile")
    file_url = data["data"]["downloadPage"]
    file_id = data["data"]["fileId"]

    # Store metadata
    FILE_DB[file_id] = {
        "id": file_id,
        "url": file_url,
        "category": category,
        "code": generate_code() if category == "secret" else None
    }

    return file_url, file_id

def get_random_file(category="images"):
    """Returns a random file dict from a specific category"""
    files = [f for f in FILE_DB.values() if f["category"] == category]
    return random.choice(files) if files else None

def get_file_by_code(code):
    """Return file by secret code"""
    for f in FILE_DB.values():
        if f.get("code") == code:
            return f
    return None

def delete_file(file_id):
    """Delete file from local and Gofile (placeholder)"""
    # Gofile does not offer public delete API without account tokens
    if file_id in FILE_DB:
        del FILE_DB[file_id]

def list_files():
    """Returns all stored file metadata"""
    return FILE_DB

def get_all_files_by_type(category="images"):
    return [f for f in FILE_DB.values() if f["category"] == category]
