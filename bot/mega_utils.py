from mega import Mega
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad
import os

class MegaUploader:
    def __init__(self):
        self.mega = Mega()
        self.m = self.mega.login()

    def upload_file(self, file_path):
        return self.m.upload(file_path)

    def encrypt_file(self, input_file, output_file, key):
        cipher = AES.new(key, AES.MODE_CBC)
        with open(input_file, 'rb') as f_in:
            data = pad(f_in.read(), AES.block_size)
            ct_bytes = cipher.encrypt(data)
        with open(output_file, 'wb') as f_out:
            f_out.write(cipher.iv + ct_bytes)

    def decrypt_file(self, input_file, output_file, key):
        with open(input_file, 'rb') as f_in:
            iv = f_in.read(16)
            ct = f_in.read()
            cipher = AES.new(key, AES.MODE_CBC, iv=iv)
            pt = unpad(cipher.decrypt(ct), AES.block_size)
        with open(output_file, 'wb') as f_out:
            f_out.write(pt)
