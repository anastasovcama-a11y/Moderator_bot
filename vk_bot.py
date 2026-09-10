import csv
import os
import threading
from datetime import datetime
from vkbottle.bot import Bot, Message
from vkbottle import GroupEventType, GroupTypes

# ============================================================
# НАСТРОЙКИ
# ============================================================
CSV_FILE = "messages.csv"          # ← общий файл (НЕ МЕНЯТЬ)

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

def save_to_csv(source, username, text, media=""):
    with csv_lock:
        file_exists = os.path.isfile(CSV_FILE)
        with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Дата", "Источник", "Отправитель", "Текст", "Медиа"])
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                source, username, text, media
            ])

# ============================================================
# МЕДИА
# ============================================================
def extract_vk_media(message: Message):
    links = []
    if message.attachments:
        for attach in message.attachments:
            if attach.type == "photo":
                sizes = attach.photo.sizes
                if sizes:
                    links.append(sizes[-1].url)
            elif attach.type == "video":
                links.append(f"https://vk.com/video{attach.video.owner_id}_{attach.video.id}")
    return "; ".join(links) if links else ""

# ============================================================
# ЗАПУСК ОДНОГО БОТА
# ============================================================
def run_vk_bot(token: str, bot_name: str):
    bot = Bot(token=token)

    @bot.on.message()
    async def vk_handler(message: Message):
        user_info = await bot.api.users.get(user_ids=message.from_id)
        username = user_info[0].first_name if user_info else "Аноним"
        text = message.text or ""
        media = extract_vk_media(message)
        if any(word in normalize_text(text) for word in BAD_WORDS):
            try:
                await bot.api.messages.delete(message_ids=message.id, delete_for_all=True)
            except Exception as e:
                print(f"Ошибка удаления: {e}")
            return
        if text or media:
            save_to_csv(f"VK ({bot_name})", username, text, media)

    @bot.on.raw_event(GroupEventType.WALL_REPLY_NEW)
    async def vk_comment_handler(event: GroupTypes.WallReplyNew):
        username = f"id{event.object.from_id}"
        text = event.object.text or ""
        if any(word in normalize_text(text) for word in BAD_WORDS):
            try:
                await bot.api.wall.delete_comment(comment_id=event.object.id)
            except Exception as e:
                print(f"Ошибка удаления: {e}")
            return
        save_to_csv(f"VK-Comment ({bot_name})", username, text)

    print(f"✅ VK-бот '{bot_name}' запущен")
    bot.run_forever()

# ============================================================
# ЗАПУСК
# ============================================================
# <<< ВСТАВЬТЕ СЮДА ВАШ ТОКЕН >>>
VK_BOTS = [
    {"token": os.environ.get("VK_TOKEN"), "Torero": "Основное"},
]

if __name__ == "__main__":
    threads = []
    for b in VK_BOTS:
        t = threading.Thread(target=run_vk_bot, args=(b["token"], b["name"]), daemon=True)
        t.start()
        threads.append(t)
    for t in threads:
        t.join()