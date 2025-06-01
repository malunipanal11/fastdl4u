import os
import requests
import uuid
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

GOFILE_TOKEN = os.getenv("GOFILE_TOKEN")
user_categories = {}
uploaded_files = defaultdict(list)

def upload_to_gofile(file_bytes, filename, category):
    try:
        server_resp = requests.get("https://api.gofile.io/getServer", params={"token": GOFILE_TOKEN})
        server_resp.raise_for_status()
        server_data = server_resp.json()

        if server_data.get("status") != "ok":
            return {"success": False, "message": "Failed to get GoFile server."}

        server = server_data["data"]["server"]
        file_bytes.seek(0)
        files = {"file": (filename, file_bytes)}
        upload_url = f"https://{server}.gofile.io/uploadFile"

        res = requests.post(upload_url, files=files, data={"token": GOFILE_TOKEN})
        res.raise_for_status()
        result = res.json()

        if result.get("status") == "ok":
            file_data = {
                "id": str(uuid.uuid4()),
                "name": filename,
                "url": result["data"]["downloadPage"],
                "code": result["data"]["code"]
            }
            uploaded_files[category].append(file_data)
            return {"success": True, "data": file_data}
        else:
            return {"success": False, "message": result.get("message", "Unknown error")}
    except Exception as e:
        return {"success": False, "message": str(e)}
