import os
import json
import asyncio
import random
from datetime import datetime, timedelta, timezone

from telethon import TelegramClient, events
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import GetMessagesViewsRequest

from apscheduler.schedulers.asyncio import AsyncIOScheduler

TURKIYE = timezone(timedelta(hours=3))

with open("config.json", "r") as f:
    config = json.load(f)

api_id = config["api_id"]
api_hash = config["api_hash"]
groups_config = config["groups"]
delay_min, delay_max = config["delay_range_seconds"]

ACCOUNTS_DIR = "accounts"


def read_sessions(file):
    with open(file, "r") as f:
        return [line.strip() for line in f if line.strip()]


group_sessions = {
    "A": read_sessions("group_a.txt"),
    "B": read_sessions("group_b.txt"),
    "C": read_sessions("group_c.txt"),
}

all_sessions = list(set(sum(group_sessions.values(), [])))

# Daha önce işlenmiş mesajlar
handled_messages = set()


async def start_clients(session_names):
    clients = {}
    for name in session_names:
        path = os.path.join(ACCOUNTS_DIR, f"{name}.session")
        client = TelegramClient(path, api_id, api_hash)
        await client.connect()
        if not await client.is_user_authorized():
            print(f"[!] {name} giriş yapılmamış.")
            continue
        clients[name] = client
    return clients


async def realistic_view(client, channel_username, msg_id):
    try:
        await client(JoinChannelRequest(channel_username))
        await asyncio.sleep(random.randint(2, 5))
        await asyncio.sleep(random.randint(delay_min, delay_max))
        await client.send_read_acknowledge(channel_username, max_id=msg_id)

        channel_entity = await client.get_entity(channel_username)
        views = await client(GetMessagesViewsRequest(
            peer=channel_entity,
            id=[msg_id],
            increment=True
        ))
        print(f"[✓] {client.session.filename} mesajı görüntüledi: {views}")

    except Exception as e:
        print(f"[X] {client.session.filename} hata: {e}")


async def plan_views(channel_username, msg_id, group_name, clients, scheduler):
    total = clients[:]
    random.shuffle(total)

    skip = random.randint(int(len(total) * 0.05), int(len(total) * 0.1))
    active = total[skip:]

    total_views = len(active)

    # İlk %25
    first_batch_count = int(total_views * 0.25)
    first_batch_clients = active[:first_batch_count]
    rest_clients = active[first_batch_count:]

    now = datetime.now(TURKIYE)

    # İlk batch: ilk 3 saat, ama ağırlık ilk 1 saatte
    for c in first_batch_clients:
        if random.random() < 0.7:
            # %70 ihtimalle ilk 1 saate
            delta_seconds = random.uniform(0, 1 * 3600)
        else:
            # %30 ihtimalle 1-3 saat arası
            delta_seconds = random.uniform(1 * 3600, 3 * 3600)

        plan_time = now + timedelta(seconds=delta_seconds)
        scheduler.add_job(
            realistic_view,
            'date',
            run_date=plan_time,
            args=[c, channel_username, msg_id],
            timezone=TURKIYE
        )
        print(f"[🕒 İlk Batch] {c.session.filename} zamanlandı: {plan_time}")

    # Kalan batch: 3. saatten 24. saatin sonuna kadar
    rest_start = now + timedelta(hours=3)
    rest_end = now + timedelta(hours=24)

    for c in rest_clients:
        delta_seconds = random.uniform(0, (rest_end - rest_start).total_seconds())
        plan_time = rest_start + timedelta(seconds=delta_seconds)
        scheduler.add_job(
            realistic_view,
            'date',
            run_date=plan_time,
            args=[c, channel_username, msg_id],
            timezone=TURKIYE
        )
        print(f"[🗓️ Diğer Batch] {c.session.filename} zamanlandı: {plan_time}")


async def main():
    clients = await start_clients(all_sessions)
    if not clients:
        print("Hiç client yok.")
        return

    scheduler = AsyncIOScheduler(timezone=TURKIYE)
    scheduler.start()

    group_channels = {
        "A": groups_config["A"]["channels"],
        "B": groups_config["B"]["channels"],
        "C": groups_config["C"]["channels"],
    }

    for name, client in clients.items():
        @client.on(events.NewMessage)
        async def handler(event, this_client_name=name):
            channel = await event.get_chat()
            username = channel.username or channel.id
            msg_id = event.id

            unique_id = f"{username}_{msg_id}"

            if unique_id in handled_messages:
                return  # Diğer client zaten planladı

            handled_messages.add(unique_id)

            matched_group = None
            for g, chans in group_channels.items():
                if str(username) in chans:
                    matched_group = g
                    break

            if matched_group:
                usable = [c for n, c in clients.items() if n in group_sessions[matched_group]]
                await plan_views(username, msg_id, matched_group, usable, scheduler)

    print("[✅] Dinlemede...")
    await asyncio.gather(*[c.run_until_disconnected() for c in clients.values()])


if __name__ == "__main__":
    asyncio.run(main())
