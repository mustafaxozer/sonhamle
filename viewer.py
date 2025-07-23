import os
import json
import asyncio
import random
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient, events
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import GetMessagesViewsRequest

# Türkiye saat dilimi
TURKIYE_ZAMANI = timezone(timedelta(hours=3))

# Config dosyasını oku
with open("config.json", "r") as f:
    config = json.load(f)

api_id = config["api_id"]
api_hash = config["api_hash"]
channels = config["channels"]
delay_min, delay_max = config["delay_range_seconds"]

ACCOUNTS_DIR = "accounts"

async def start_account_sessions():
    clients = []
    for session_file in os.listdir(ACCOUNTS_DIR):
        if not session_file.endswith(".session"):
            continue
        name = session_file.replace(".session", "")
        client = TelegramClient(os.path.join(ACCOUNTS_DIR, name), api_id, api_hash)
        await client.connect()

        if not await client.is_user_authorized():
            print(f"[!] {name} giriş yapılmamış.")
            continue

        clients.append(client)
    return clients

async def realistic_view(client, channel_username, msg_id):
    try:
        await client(JoinChannelRequest(channel_username))
        await asyncio.sleep(random.randint(2, 5))

        await asyncio.sleep(random.randint(delay_min, delay_max))
        await client.send_read_acknowledge(channel_username, max_id=msg_id)

        channel_entity = await client.get_entity(channel_username)

        try:
            views = await client(GetMessagesViewsRequest(
                peer=channel_entity,
                id=[msg_id],
                increment=True
            ))
            print(f"[✓] {client.session.filename} mesajı görüntüledi: {views}")
        except Exception as e:
            print(f"[!] {client.session.filename} görüntüleme hatası: {e}")

    except Exception as e:
        print(f"[X] {client.session.filename} hata: {e}")

async def delayed_view(client, username, msg_id, delay):
    await asyncio.sleep(delay)
    await realistic_view(client, username, msg_id)

async def main():
    clients = await start_account_sessions()
    if not clients:
        print("Aktif hesap yok.")
        return

    for client in clients:
        @client.on(events.NewMessage(chats=channels))
        async def handler(event):
            channel = await event.get_chat()
            username = channel.username or channel.id
            msg_id = event.id

            if event.message.views is None:
                print(f"[⏭️] View bilgisi yok, mesaj atlandı: {username} / ID: {msg_id}")
                return

            print(f"[📢] Yeni görüntülenebilir mesaj: {username} / ID: {msg_id}")

            total_clients = clients[:]
            random.shuffle(total_clients)

            skip_count = random.randint(int(len(clients) * 0.05), int(len(clients) * 0.1))
            active_clients = total_clients[skip_count:]

            now = datetime.now(TURKIYE_ZAMANI)
            post_time = now  # Postun atıldığı zaman

            def random_delay_between(start_sec, end_sec):
                return random.uniform(start_sec, end_sec)

            def schedule_delay(sec_from_post):
                delay_sec = (post_time + timedelta(seconds=sec_from_post) - now).total_seconds()
                return max(delay_sec, 1)

            total_views = len(active_clients)

            # Saat dilimleri (saniye cinsinden)
            night_start = 0               # 00:00
            night_end = 8 * 3600          # 08:00
            morning_before_peak_start = 8 * 3600    # 08:00
            morning_before_peak_end = 9 * 3600 + 40 * 60  # 09:40
            peak_start = 9 * 3600 + 40 * 60  # 09:40
            peak_end = 10 * 3600               # 10:00
            after_peak_start = 10 * 3600        # 10:00
            after_peak_end = 24 * 3600           # 24:00

            # Yüzdelik dağılımlar
            night_pct = 0.15
            morning_before_peak_pct = 0.2
            peak_pct = 0.45
            after_peak_pct = 0.20

            night_count = int(total_views * night_pct)
            morning_before_peak_count = int(total_views * morning_before_peak_pct)
            peak_count = int(total_views * peak_pct)
            after_peak_count = total_views - (night_count + morning_before_peak_count + peak_count)

            random.shuffle(active_clients)
            night_clients = active_clients[:night_count]
            morning_before_peak_clients = active_clients[night_count: night_count + morning_before_peak_count]
            peak_clients = active_clients[night_count + morning_before_peak_count: night_count + morning_before_peak_count + peak_count]
            after_peak_clients = active_clients[night_count + morning_before_peak_count + peak_count:]

            # Gece 00:00 - 08:00 arası düşük tempoda görüntüleme
            for c in night_clients:
                delay_sec = schedule_delay(random_delay_between(night_start, night_end))
                asyncio.create_task(delayed_view(c, username, msg_id, delay_sec))

            # Sabah 08:00 - 09:40 arası orta tempoda görüntüleme
            for c in morning_before_peak_clients:
                delay_sec = schedule_delay(random_delay_between(morning_before_peak_start, morning_before_peak_end))
                asyncio.create_task(delayed_view(c, username, msg_id, delay_sec))

            # Sabah 09:40 - 10:00 arası büyük patlama
            for c in peak_clients:
                delay_sec = schedule_delay(random_delay_between(peak_start, peak_end))
                asyncio.create_task(delayed_view(c, username, msg_id, delay_sec))

            # 10:00 - 24:00 arası yavaş tamamlanma
            for c in after_peak_clients:
                delay_sec = schedule_delay(random_delay_between(after_peak_start, after_peak_end))
                asyncio.create_task(delayed_view(c, username, msg_id, delay_sec))

    print("[✅] Bot çalışıyor, yeni gönderiler dinleniyor...")
    await asyncio.gather(*[client.run_until_disconnected() for client in clients])

if __name__ == "__main__":
    asyncio.run(main())
