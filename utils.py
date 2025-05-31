import random
import string
import json
import os

DB_FILE = "db.json"

# Generate a random short code
def generate_code(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


# Save metadata to JSON DB
def save_file_metadata(file_id, url, category, uploader_id, code=None):
    data = {
        "id": file_id,
        "url": url,
        "category": category,
        "uploader_id": uploader_id,
        "code": code or generate_code()
    }

    if not os.path.exists(DB_FILE):
        with open(DB_FILE, 'w') as f:
            json.dump([], f)

    with open(DB_FILE, 'r') as f:
        files = json.load(f)

    files.append(data)

    with open(DB_FILE, 'w') as f:
        json.dump(files, f, indent=2)
