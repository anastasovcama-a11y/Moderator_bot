import asyncio
import csv
import os
import threading
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile

# ============================================================
# НАСТРОЙКИ
# ============================================================
CSV_FILE = "messages.csv"          # ← общий файл (НЕ МЕНЯТЬ)
MEDIA_DIR = "media"                # ← папка для медиа
ADMIN_CHAT_ID = 863066338          # ← ИЗМЕНИТЬ на ваш Telegram ID

os.makedirs(MEDIA_DIR, exist_ok=True)

# ============================================================
# СТОП-СЛОВА
# ============================================================
def load_bad_words():
    try:
        with open("bad_words.txt", "r", encoding="utf-8") as f:
            return [line.strip().lower() for line in f if line.strip()]
    except FileNotFoundError:
        return ["спам", "реклама", "казино", "ставки"]

BAD_WORDS = load_bad_words()

def normalize_text(text):
    text = text.lower()
    replacements = {
        "@": "а", "a": "а", "e": "е", "o": "о",
        "p": "р", "c": "с", "x": "х", "y": "у",
        "0": "о", "1": "и", "3": "з", "6": "б",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

# ============================================================
# СОХРАНЕНИЕ В CSV
# ============================================================
csv_lock = threading.Lock()

def save_to_csv(source, username, text, media_path=""):
    with csv_lock:
        file_exists = os.path.isfile(CSV_FILE)
        with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Дата", "Источник", "Отправитель", "Текст", "Медиа"])
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                source, username, text, media_path
            ])

# ============================================================
# СКАЧИВАНИЕ МЕДИА
# ============================================================
async def download_telegram_media(message: types.Message):
    media_path = ""
    try:
        if message.photo:
            file = await message.bot.get_file(message.photo[-1].file_id)
            filename = f"{MEDIA_DIR}/tg_{message.message_id}.jpg"
            await message.bot.download_file(file.file_path, filename)
            media_path = filename
        elif message.video:
            file = await message.bot.get_file(message.video.file_id)
            filename = f"{MEDIA_DIR}/tg_{message.message_id}.mp4"
            await message.bot.download_file(file.file_path, filename)
            media_path = filename
        elif message.document:
            file = await message.bot.get_file(message.document.file_id)
            filename = f"{MEDIA_DIR}/tg_{message.message_id}_{message.document.file_name or 'file'}"
            await message.bot.download_file(file.file_path, filename)
            media_path = filename
    except Exception as e:
        print(f"Ошибка медиа: {e}")
    return media_path

# ============================================================
# ЗАПУСК ОДНОГО БОТА
# ============================================================
async def start_telegram_bot(token: str, bot_name: str):
    bot = Bot(token=token)
    dp = Dispatcher()

    @dp.message(Command("start"))
    async def start_handler(message: types.Message):
        await message.answer("Привет! Я записываю все сообщения.")

    @dp.message(Command("export"))
    async def export_handler(message: types.Message):
        if os.path.isfile(CSV_FILE):
            await message.answer_document(FSInputFile(CSV_FILE), caption="📊 Выгрузка")
        else:
            await message.answer("Файл пока пуст.")

    @dp.message()
    async def tg_handler(message: types.Message):
        username = message.from_user.username or message.from_user.first_name or "Аноним"
        text = message.text or message.caption or ""
        normalized = normalize_text(text)
        if any(word in normalized for word in BAD_WORDS):
            try:
                await message.delete()
                await message.answer("⚠️ Сообщение удалено.")
            except Exception as e:
                print(f"Ошибка удаления: {e}")
            return
        media_path = await download_telegram_media(message)
        if text or media_path:
            save_to_csv(f"Telegram ({bot_name})", username, text, media_path)

    print(f"✅ Telegram-бот '{bot_name}' запущен")
    await dp.start_polling(bot)

# ============================================================
# ЗАПУСК
# ============================================================
# <<< ВСТАВЬТЕ СЮДА ВАШ ТОКЕН >>>
TELEGRAM_BOTS = [
    {"token":  os.environ.get("TELEGRAM_TOKEN"), "name": "Основной"},
]

async def main():
    tasks = [asyncio.create_task(start_telegram_bot(b["token"], b["name"])) for b in TELEGRAM_BOTS]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())