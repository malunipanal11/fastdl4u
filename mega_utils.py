import os
from mega import Mega

class MegaStorage:
    def __init__(self):
        self.mega = Mega()
        self.mega.login(os.getenv("MEGA_EMAIL"), os.getenv("MEGA_PASSWORD"))
        self.root_folder = "Telegram Storage"
        self.ensure_path(self.root_folder)

    def ensure_path(self, folder_path):
        folders = folder_path.split("/")
        parent = None
        for name in folders:
            node = self.mega.find(name, parent)
            if node is None:
                node = self.mega.create_folder(name, parent)
            parent = node
        return parent

    def upload_file(self, file_path, subfolder="General"):
        path = f"{self.root_folder}/{subfolder}"
        self.ensure_path(path)
        return self.mega.upload(file_path, dest=path)
