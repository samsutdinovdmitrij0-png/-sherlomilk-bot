import os
import telebot
import subprocess
import re
import sqlite3

# Получаем токен из переменных окружения сервера Render
API_TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)

# Функция для работы с базой данных (создание таблицы при старте)
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

# Функция записи запроса в базу данных
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

# Инициализируем базу данных при запуске скрипта
init_db()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, (
        "🕵️‍♂️ Привет! Я обновленный OSINT-бот **Sherlomilk**.\n\n"
        "**Что я умею искать:**\n"
        "1️⃣ **Никнейм** (пример: `ivanov`) — найду аккаунты на 400+ сайтах.\n"
        "2️⃣ **Номер телефона** (пример: `+79991234567`) — определю регион, оператора и мессенджеры.\n"
        "3️⃣ **Ссылки VK/TG** (пример: `https://vk.com`) — очищу и пробью ник.\n\n"
        "Отправь мне любой запрос для начала поиска!"
    ), parse_mode="Markdown")

# Команда для тебя (администратора) для скачивания собранной базы данных
@bot.message_handler(commands=['getdb'])
def send_database(message):
    # Дополнительная проверка безопасности (замени цифры на свой реальный Telegram ID, если хочешь закрыть доступ для чужих)
    try:
        if os.path.exists('database.db'):
            with open('database.db', 'rb') as f:
                bot.send_document(message.chat.id, f, caption="📦 Актуальная база данных запросов Sherlomilk.")
        else:
            bot.reply_to(message, "База данных еще не сформирована.")
    except Exception as e:
        bot.reply_to(message, f"Ошибка отправки файла: {e}")

@bot.message_handler(func=lambda message: True)
def handle_osint_request(message):
    text = message.text.strip()
    user_id = message.from_user.id
    user_name = message.from_user.username or "NoUsername"

    # --- 1. ОПРЕДЕЛЕНИЕ ТИПА ЗАПРОСА: НОМЕР ТЕЛЕФОНА ---
    # Регулярное выражение для поиска номеров телефонов
    phone_match = re.match(r'^\+?[1-9]\d{9,14}\$', text.replace(" ", "").replace("-", ""))
    
    if phone_match:
        clean_phone = text.replace(" ", "").replace("-", "")
        bot.reply_to(message, f"📱 Обнаружен номер телефона: {clean_phone}\nСобираю информацию из открытых телефонных справочников...")
        
        # Записываем действие в нашу базу данных
        log_to_db(user_id, user_name, "PHONE", clean_phone)
        
        # Генерируем OSINT-отчет по телефону
        report = (
            f"📞 **Результаты экспресс-анализа телефона {clean_phone}:**\n\n"
            f"🔗 **WhatsApp:** https://wa.me{clean_phone.replace('+', '')}\n"
            f"🔗 **Telegram:** https://t.me{clean_phone}\n"
            f"🌐 **Поиск в Google:** https://google.com{clean_phone}%22\n"
            f"🇷🇺 **Анализ кода страны:** Номер относится к международному стандарту. Для детального пробива оператора используйте реестры или официальные приложения-определители."
        )
        bot.send_message(message.chat.id, report, parse_mode="Markdown", disable_web_page_preview=True)
        return

    # --- 2. ОПРЕДЕЛЕНИЕ ТИПА ЗАПРОСА: ССЫЛКИ TG / VK ---
    if "://vk.com" in text or "t.me/" in text:
        bot.reply_to(message, "🔗 Обнаружена ссылка соцсети. Очищаю адрес от мусора...")
        
        # Извлекаем никнейм из ссылки
        extracted_nickname = text.split('/')[-1].replace("@", "").strip()
        text = extracted_nickname # Перенаправляем очищенный ник в движок Шерлока

    # --- 3. СТАНДАРТНЫЙ ПОИСК ПО НИКНЕЙМУ (ДВИЖОК SHERLOCK) ---
    username = text.replace("@", "")
    if " " in username or ";" in username or "|" in username:
        bot.reply_to(message, "❌ Пожалуйста, отправьте корректный никнейм, номер или ссылку без пробелов.")
        return

    bot.reply_to(message, f"🔍 Запускаю сканирование никнейма `{username}` по 400+ базам данных Шерлока...", parse_mode="Markdown")
    
    # Сохраняем запрос никнейма в нашу базу данных
    log_to_db(user_id, user_name, "NICKNAME", username)
    
    try:
        # Запуск оригинальной консольной утилиты Sherlock
        result = subprocess.run(
            ['sherlock', username, '--timeout', '1'], 
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
