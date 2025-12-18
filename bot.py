import asyncio
import os
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
import config

client = TelegramClient("sessions/session", config.API_ID, config.API_HASH)

async def main():
    print("🔹 Починаємо запуск Telegram-клієнта…")
    await client.start(config.PHONE_NUMBER)
    print("✅ Бот запущений і працює 24/7")

    os.makedirs("logs", exist_ok=True)

    while True:
        now = datetime.now(ZoneInfo("Europe/Kyiv"))
        today_kyiv = now.date()

        # Обчислюємо точний час відправки
        target_time = now.replace(hour=config.SEND_HOUR, minute=config.SEND_MINUTE, second=0, microsecond=0)
        if now >= target_time:
            target_time += timedelta(days=1)  # якщо час вже пройшов, пересуваємо на завтра

        sleep_seconds = (target_time - now).total_seconds()
        print(f"⏱ Бот засне на {int(sleep_seconds)} секунд до {target_time.time()}")
        await asyncio.sleep(sleep_seconds)

        # Перевірка, чи вже відправляли сьогодні
        last_send_date = None
        if os.path.exists(config.LAST_SEND_DATE_FILE):
            with open(config.LAST_SEND_DATE_FILE, "r") as f:
                last_send_date = f.read().strip()
        if last_send_date == str(today_kyiv):
            print("ℹ️ Вже переслано сьогодні, чекаємо наступного дня...")
            continue

        # Останній ID
        last_id = 0
        if os.path.exists(config.LAST_MESSAGE_FILE):
            with open(config.LAST_MESSAGE_FILE, "r") as f:
                try:
                    last_id = int(f.read().strip())
                except:
                    last_id = 0
        print(f"📌 Останній ID повідомлення: {last_id}")

        # Отримуємо історію
        try:
            history = await client(GetHistoryRequest(
                peer=config.SOURCE_CHAT_ID,
                limit=100,
                offset_date=None,
                offset_id=0,
                max_id=0,
                min_id=0,
                add_offset=0,
                hash=0
            ))
        except Exception as e:
            print(f"❌ Помилка отримання історії: {e}")
            await asyncio.sleep(60)
            continue

        # Нові повідомлення
        new_messages = [m for m in history.messages if m.id > last_id]

        if new_messages:
            msg = new_messages[-1]  # найновіше
        else:
            # Старі медіа, яких ще не було
            old_media = sorted(
                [m for m in history.messages if getattr(m, 'media', None) and m.id > last_id],
                key=lambda x: x.id  # від старішого до новішого
            )
            if not old_media:
                print("ℹ️ Старих медіа для пересилання немає")
                continue
            msg = old_media[0]

        # Відправка повідомлень
        try:
            if getattr(msg, 'media', None):
                file_path = await client.download_media(msg)
                await client.send_file(config.TARGET_CHAT_ID, file_path)
                os.remove(file_path)
                print(f"📤 Переслано медіа ID {msg.id} без підпису 'Переслано від'")
            else:
                await client.send_message(config.TARGET_CHAT_ID, msg.message)
                print(f"📤 Переслано текстове повідомлення ID {msg.id}")
        except Exception as e:
            print(f"❌ Помилка при пересиланні: {e}")
            await asyncio.sleep(60)
            continue

        # Оновлюємо last_id і дату
        with open(config.LAST_MESSAGE_FILE, "w") as f:
            f.write(str(msg.id))
        with open(config.LAST_SEND_DATE_FILE, "w") as f:
            f.write(str(today_kyiv))

        print("✅ Всі дані оновлено, чекаємо наступного дня...")

if __name__ == "__main__":
    asyncio.run(main())
