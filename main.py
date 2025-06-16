from fastapi import FastAPI, Request
from bot_commands import handle_telegram_update
from drive_utils import upload_to_drive, list_files_in_folder, get_random_file
import io

app = FastAPI()

@app.post("/")
async def telegram_webhook(request: Request):
    update = await request.json()
    await handle_telegram_update(update)
    return {"status": "ok"}

@app.get("/upload-demo")
def upload_demo():
    # Create the file content in memory instead of writing to disk
    file_content = io.BytesIO(b"This is a demo file uploaded from FastAPI (in-memory).")
    file_id = upload_to_drive(file_content, "RenderUpload.txt", "BotFiles")
    return {"uploaded_file_id": file_id}

@app.get("/list-files")
def list_files():
    files = list_files_in_folder("BotFiles")
    return {"files": files}

@app.get("/random-file")
def random_file():
    file = get_random_file("BotFiles")
    if file:
        return {"random_file": file}
    return {"error": "No files found"}
