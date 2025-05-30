from fastapi import FastAPI, UploadFile, File
from bot.mega_utils import MegaUploader
import os

app = FastAPI()
uploader = MegaUploader()

@app.post("/upload/")
async def upload(file: UploadFile = File(...)):
    file_location = f"temp_{file.filename}"
    with open(file_location, "wb") as f:
        f.write(await file.read())
    uploaded = uploader.upload_file(file_location)
    os.remove(file_location)
    return {"filename": file.filename, "uploaded": uploaded}
