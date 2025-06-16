from fastapi import FastAPI, Request
from bot_commands import handle_telegram_update
from drive_utils import upload_to_drive, list_files_in_folder, get_random_file

app = FastAPI()

# === Telegram webhook endpoint ===
@app.post("/")
async def telegram_webhook(request: Request):
    update = await request.json()
    await handle_telegram_update(update)
    return {"status": "ok"}

# === Test route: Upload a file to a named folder ===
@app.get("/upload-demo")
def upload_demo():
    file_id = upload_to_drive("test.txt", "RenderUpload.txt", "BotFiles")
    return {"uploaded_file_id": file_id}

# === List all files in the given folder ===
@app.get("/list-files")
def list_files():
    files = list_files_in_folder("BotFiles")
    return {"files": files}

# === Get a random file from the folder ===
@app.get("/random-file")
def random_file():
    file = get_random_file("BotFiles")
    if file:
        return {"random_file": file}
    return {"error": "No files found"}
