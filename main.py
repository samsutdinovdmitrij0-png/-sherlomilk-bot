import os
import telebot
import re
import sqlite3
import threading
from flask import Flask

# Импортируем официальные модули самого проекта Sherlock
from sherlock.sherlock import Sherlock
from sherlock.sites import SitesInformation

API_TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)

# --- БЛОК ВЕБ-СЕРВЕРА ДЛЯ RENDER (БЕСПЛАТНЫЙ ТАРИФ) ---
app = Flask('')

@app.route('/')
def home():
    return "Бот Sherlomilk запущен и работает!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_web_server, daemon=True).start()
# -----------------------------------------------------

def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            query_type TEXT,
            search_query TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def log_to_db(user_id, username, query_type, search_query):
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO search_history (user_id, username, query_type, search_query) VALUES (?, ?, ?, ?)',
            (user_id, username, query_type, search_query)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Ошибка БД: {e}")

init_db()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, (
        "🕵️‍♂️ Привет! Я твой автоматический OSINT-бот **Sherlomilk**.\n\n"
        "**Что я умею искать:**\n"
        "1️⃣ **Никнейм** (пример: `ivanov`) — найду аккаунты на 400+ сайтах.\n"
        "2️⃣ **Номер телефона** (пример: `+79991234567`) — выдам мессенджеры и пробив.\n"
        "3️⃣ **Ссылки VK/TG** (пример: `://vk.com` или `t.me/durov`) — найду скрытый телефон и зацепки.\n\n"
        "Отправь мне любой запрос для начала поиска!"
    ), parse_mode="Markdown")

@bot.message_handler(commands=['getdb'])
def send_database(message):
    try:
        if os.path.exists('database.db'):
            with open('database.db', 'rb') as f:
                bot.send_document(message.chat.id, f, caption="📦 Ваша собранная база данных запросов Sherlomilk.")
        else:
            bot.reply_to(message, "База данных еще пуста.")
    except Exception as e:
        bot.reply_to(message, f"Ошибка при отправке БД: {e}")

@bot.message_handler(func=lambda message: True)
def handle_osint_request(message):
    text = message.text.strip()
    user_id = message.from_user.id
    user_name = message.from_user.username or "NoUsername"

    clean_text = text.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    
    # --- 1. ЕСЛИ ОТПРАВИЛИ НОМЕР ТЕЛЕФОНА ---
    if clean_text.isdigit() or (clean_text.startswith('+') and clean_text[1:].isdigit()):
        bot.reply_to(message, f"📱 Анализирую номер телефона: {clean_text}...")
        log_to_db(user_id, user_name, "PHONE", clean_text)
        
        phone_no_plus = clean_text.replace('+', '')
        report = (
            f"📞 **Результаты экспресс-анализа телефона {clean_text}:**\n\n"
            f"🔗 **WhatsApp:** https://wa.me{phone_no_plus}\n"
            f"🔗 **Viber:** https://viber.click{phone_no_plus}\n"
            f"🌐 **Поиск владельца в Google:** https://google.com{clean_text}%22"
        )
        bot.send_message(message.chat.id, report, parse_mode="Markdown", disable_web_page_preview=True)
        return

    # --- 2. ЕСЛИ ОТПРАВИЛИ ССЫЛКУ VK ---
    if "://vk.com" in text or "vk.ru/" in text:
        log_to_db(user_id, user_name, "VK_LINK", text)
        nickname = text.split('/')[-1].replace("@", "").strip()
        
        bot.reply_to(message, f"🔗 Обнаружен профиль VK: `{nickname}`...\nИщу скрытые упоминания телефона в кэше поисковиков.", parse_mode="Markdown")
        
        vk_report = (
            f"🕵️‍♂️ **OSINT-запросы для поиска телефона страницы VK (`{nickname}`):**\n\n"
            f"🔎 **Поиск телефона/email в кэше Google:**\n"
            f"https://google.com{nickname}%22+%22%2B7%22\n\n"
            f"📦 **Поиск связанных объявлений (Avito/Юла):**\n"
            f"https://google.com/search?q=site:://vk.com{nickname}+OR+%22id{nickname}%22\n\n"
            f"⚙️ Сейчас я параллельно прогоню этот ник по базам Шерлока..."
        )
        bot.send_message(message.chat.id, vk_report, parse_mode="Markdown", disable_web_page_preview=True)
        text = nickname

    # --- 3. ЕСЛИ ОТПРАВИЛИ ССЫЛКУ TELEGRAM ИЛИ ЮЗЕРНЕЙМ ---
    if "t.me/" in text or text.startswith("@") or (len(text) > 3 and not "/" in text and not "." in text):
        is_tg_request = "t.me/" in text or text.startswith("@")
        nickname = text.split('/')[-1].replace("@", "").strip()
        
        if is_tg_request or (message.reply_to_message is None): 
            log_to_db(user_id, user_name, "TG_LINK", text)
            bot.reply_to(message, f"🔮 Анализирую аккаунт Telegram: `@{nickname}`\nИщу привязанный номер телефона по открытым базам...", parse_mode="Markdown")
            
            tg_report = (
                f"🕵️‍♂️ **OSINT-пробив для Telegram `@{nickname}`:**\n\n"
                f"🗄 **1. Поиск привязанного телефона в архивных базах Telegram:**\n"
                f"👉 https://buzz.im{nickname}\n\n"
                f"🔎 **2. Поиск телефона, привязанного к этому нику в Google:**\n"
                f"👉 https://google.com{nickname}%22+%22%2B7%22\n\n"
                f"⚙️ Теперь я параллельно прогоню ник `{nickname}` по остальным 400+ соцсетям..."
            )
            bot.send_message(message.chat.id, tg_report, parse_mode="Markdown", disable_web_page_preview=True)
            text = nickname

    # --- 4. ГЛОБАЛЬНЫЙ ПОИСК ПО НИКНЕЙМУ (НАСТОЯЩИЙ SHERLOCK ВНУТРИ PYTHON) ---
    username = text.replace("@", "")
    if " " in username or ";" in username or "|" in username or len(username) < 2:
        return

    bot.reply_to(message, f"🔍 Запускаю сканирование никнейма `{username}` по базам Шерлока...", parse_mode="Markdown")
    log_to_db(user_id, user_name, "NICKNAME", username)
    
    try:
        # Инициализируем базу данных сайтов самого Шерлока
        sites = SitesInformation()
        # Запускаем оригинальный процесс поиска Шерлока внутри нашей программы
        sherlock_instance = Sherlock(sites)
        
        # Получаем результаты сканирования (timeout=1 секунда на сайт, как у вас и было)
        results = sherlock_instance.id_from_username(username, timeout=1)
        
        output = f"📊 **Результаты поиска для `{username}`:**\n\n"
        found_links = []
        
        # Обрабатываем оригинальный словарь ответов Шерлока
        for site_name, site_data in results.items():
            if site_data.get('status') == 'CLAIMED':  # Если аккаунт точно найден
                url = site_data.get('url_user')
                found_links.append(f"🔹 **{site_name}**: {url}")
        
        if found_links:
            output += "\n".join(found_links)
            if len(output) > 4000: 
                output = output[:4000] + "\n\n...список сокращен из-за лимитов Telegram."
            bot.send_message(message.chat.id, output, disable_web_page_preview=True)
        else:
            bot.send_message(message.chat.id, "❌ Профилей с таким никнеймом в глобальных базах Шерлока не найдено.")
            
    except Exception as e:
        print(f"Ошибка Sherlock API: {e}")
        bot.send_message(message.chat.id, "⚠️ Ошибка выполнения скрипта поиска на сервере.")

if __name__ == '__main__':
    bot.infinity_polling()
