import os
from mega import Mega

class MegaUploader:
    def __init__(self):
        self.mega = Mega()
        self.mega.login(os.getenv("MEGA_EMAIL"), os.getenv("MEGA_PASSWORD"))
        self.root_folder = "Telegram Storage"
        self._ensure_root()

    def _ensure_root(self):
        self.root = self.mega.find(self.root_folder)
        if not self.root:
            self.root = self.mega.create_folder(self.root_folder)

    def ensure_platform_folder(self, platform):
        folder_path = f"{self.root_folder}/{platform}"
        folder = self.mega.find(folder_path)
        if not folder:
            folder = self.mega.create_folder(folder_path)
        return folder

    def upload_to_platform(self, filepath, platform):
        folder = self.ensure_platform_folder(platform)
        return self.mega.upload(filepath, folder)

    def get_link(self, file):
        return self.mega.get_upload_link(file)

    def list_links(self, platform):
        folder = self.mega.find(f"{self.root_folder}/{platform}")
        return self.mega.get_files_in_node(folder) if folder else []
