import requests
from io import BytesIO
import uuid
import logging
import json
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

API_TOKEN = None
DATA_FILE = "files.json"

# In-memory file storage
uploaded_files = {
    "images": [],
    "videos": [],
    "audios": [],
    "files": [],
    "secret": [],
    "links": []
}


def is_valid_url(url: str) -> bool:
    parsed = urlparse(url)
    return all([parsed.scheme, parsed.netloc])


def upload_to_gofile(file_url: str, category: str = "files"):
    if category not in uploaded_files:
        raise ValueError(f"Unknown category: {category}")

    if not is_valid_url(file_url):
        raise ValueError(f"Invalid file URL: {file_url}")

    logging.info("Fetching GoFile server...")
    server_resp = requests.get("https://api.gofile.io/getServer")
    if server_resp.status_code != 200:
        raise Exception("Failed to get GoFile server.")

    server = server_resp.json()["data"]["server"]

    logging.info(f"Downloading file from Telegram: {file_url}")
    tg_file = requests.get(file_url)
    if tg_file.status_code != 200:
        raise Exception("Failed to download file from Telegram.")

    filename = file_url.split("/")[-1] or f"{uuid.uuid4().hex}.bin"
    file_bytes = BytesIO(tg_file.content)

    files = {"file": (filename, file_bytes)}
    data = {"token": API_TOKEN} if API_TOKEN else {}

    upload_url = f"https://{server}.gofile.io/uploadFile"
    logging.info(f"Uploading to GoFile at {upload_url}...")

    r = requests.post(upload_url, files=files, data=data)
    result = r.json()

    if result.get("status") == "ok":
        file_data = {
            "id": str(uuid.uuid4()),
            "name": filename,
            "url": result["data"]["downloadPage"],
            "code": result["data"]["code"]
        }
        uploaded_files[category].append(file_data)
        save_to_disk()
        return {
            "success": True,
            "data": file_data,
            "filename": filename
        }
    else:
        return {
            "success": False,
            "message": result.get("message", "Unknown error")
        }


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
    save_to_disk()
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
    save_to_disk()
    return item["url"], code


def get_random_file(category: str):
    from random import choice
    files = uploaded_files.get(category, [])
    return choice(files) if files else None


def get_file_by_code(code: str):
    for cat_files in uploaded_files.values():
        for file in cat_files:
            if file.get("code") == code:
                return file
    return None


def get_file_by_id(file_id: str):
    for cat_files in uploaded_files.values():
        for file in cat_files:
            if file.get("id") == file_id:
                return file
    return None


def get_all_files_by_type(category: str):
    return uploaded_files.get(category, [])


def delete_file(file_id: str):
    for category in uploaded_files:
        uploaded_files[category] = [
            f for f in uploaded_files[category] if f["id"] != file_id
        ]
    save_to_disk()


def save_to_disk(path: str = DATA_FILE):
    try:
        with open(path, "w") as f:
            json.dump(uploaded_files, f, indent=2)
        logging.info(f"Data saved to {path}")
    except Exception as e:
        logging.error(f"Error saving data: {e}")


def load_from_disk(path: str = DATA_FILE):
    global uploaded_files
    try:
        with open(path, "r") as f:
            uploaded_files = json.load(f)
        logging.info(f"Data loaded from {path}")
    except FileNotFoundError:
        logging.warning(f"{path} not found. Starting with empty data.")
    except Exception as e:
        logging.error(f"Error loading data: {e}")
