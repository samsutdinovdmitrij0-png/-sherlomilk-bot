import os
import telebot
import subprocess
import re
import sqlite3

# Берем токен из настроек сервера Render
API_TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)

# Функция для инициализации базы данных запросов
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

# Функция записи действий пользователей в базу данных
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
        print(f"Ошибка записи в БД: {e}")

# Запускаем создание БД при старте
init_db()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, (
        "🕵️‍♂️ Привет! Я твой автоматический OSINT-бот **Sherlomilk**.\n\n"
        "**Что я умею искать:**\n"
        "1️⃣ **Никнейм** (пример: `ivanov`) — найду аккаунты на 400+ сайтах.\n"
        "2️⃣ **Номер телефона** (пример: `+79991234567`) — выдам ссылки на мессенджеры и пробив.\n"
        "3️⃣ **Ссылки VK/TG** (пример: `://vk.com`) — очищу от мусора и найду скрытый телефон.\n\n"
        "Отправь мне любой запрос для начала поиска!"
    ), parse_mode="Markdown")

# Админская команда для выгрузки собранной базы данных
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

    # Очищаем текст от лишних символов для проверки на номер
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
    if "://vk.com" in text:
        log_to_db(user_id, user_name, "VK_LINK", text)
        nickname = text.split('/')[-1].replace("@", "").strip()
        
        bot.reply_to(message, f"🔗 Обнаружен профиль VK: `{nickname}`...\nИщу скрытые упоминания телефона в кэше поисковиков.", parse_mode="Markdown")
        
        vk_report = (
            f"🕵️‍♂️ **OSINT-запросы для поиска телефона страницы VK (`{nickname}`):**\n\n"
            f"🔎 **Поиск телефона/email в кэше Google:**\n"
            f"`https://www.google.com/search?q=site:://vk.com{nickname}+%22%2B7%22`\n\n"
            f"📦 **Поиск связанных объявлений (Avito/Юла):**\n"
            f"`https://google.com://vk.com{nickname}%22+OR+%22id{nickname}%22`\n\n"
            f"⚙️ Сейчас я параллельно прогоню этот ник по базам Шерлока..."
        )
        bot.send_message(message.chat.id, vk_report, parse_mode="Markdown", disable_web_page_preview=True)
        text = nickname  # Передаем очищенный ник дальше в поиск Шерлока

    # --- 3. ЕСЛИ ОТПРАВИЛИ ССЫЛКУ TELEGRAM ---
    if "t.me/" in text:
        text = text.split('/')[-1].replace("@", "").strip()

    # --- 4. ГЛОБАЛЬНЫЙ ПОИСК ПО НИКНЕЙМУ (ДВИЖОК SHERLOCK) ---
    username = text.replace("@", "")
    if " " in username or ";" in username or "|" in username:
        bot.reply_to(message, "❌ Пожалуйста, введите корректный запрос одной строкой без пробелов.")
        return

    bot.reply_to(message, f"🔍 Запускаю сканирование никнейма `{username}` по 400+ базам данных Шерлока...", parse_mode="Markdown")
    log_to_db(user_id, user_name, "NICKNAME", username)
    
    try:
        # Добавлен флаг '--no-check-update' для исправления ошибки 'tag_name'
        result = subprocess.run(
            ['sherlock', username, '--timeout', '1', '--no-check-update'], 
            capture_output=True, 
            text=True, 
            check=False
        )
        
        if result.stdout:
            output = result.stdout
            if len(output) > 4000: 
                output = output[:4000] + "\n\n...список сокращен из-за лимитов Telegram."
            bot.send_message(message.chat.id, output)
        else:
            bot.send_message(message.chat.id, "❌ Профилей с таким никнеймом в глобальных базах Шерлока не найдено.")
            
    except Exception as e:
        bot.send_message(message.chat.id, "⚠️ Ошибка выполнения скрипта поиска на сервере.")

bot.infinity_polling()
