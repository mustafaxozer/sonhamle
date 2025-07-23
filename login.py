import asyncio
import os
from telethon import TelegramClient, errors
import json

# Config oku
with open("config.json", "r") as f:
    config = json.load(f)

api_id = config["api_id"]
api_hash = config["api_hash"]

ACCOUNTS_DIR = "accounts"
os.makedirs(ACCOUNTS_DIR, exist_ok=True)

def get_session_path(phone_number):
    return os.path.join(ACCOUNTS_DIR, phone_number)

async def add_account():
    while True:
        phone = input("Numarayı gir (örn: +905xxxxxxxxx): ").strip()
        session_path = get_session_path(phone)

        if os.path.exists(session_path + ".session"):
            print("[!] Bu hesap zaten eklenmiş.")
            continue

        client = TelegramClient(session_path, api_id, api_hash)
        try:
            await client.start(phone=phone)
            print(f"[✓] {phone} başarıyla eklendi.")
            await client.disconnect()
        except errors.SessionPasswordNeededError:
            pwd = input("2 adımlı doğrulama parolası gir: ")
            await client.start(phone=phone, password=pwd)
            print(f"[✓] {phone} başarıyla eklendi (parolalı giriş).")
            await client.disconnect()
        except Exception as e:
            print(f"[X] Hata oluştu: {e}")

        again = input("Başka hesap eklemek ister misin? (E/H): ").strip().lower()
        if again != 'e':
            break

if __name__ == "__main__":
    asyncio.run(add_account())
