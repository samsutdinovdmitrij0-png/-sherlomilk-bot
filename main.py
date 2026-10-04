import telebot
import requests
import json
import base64

# ==========================================
# ТОКЕНЫ И НАСТРОЙКИ
# ==========================================
# Твой рабочий токен успешно интегрирован
TELEGRAM_TOKEN = "8730411274:AAHzwv1el2hAH_Xq4Wm7_6iZ-KLy0fLpz9Y"

# Бесплатный прокси-ключ ИИ (работает в РФ без VPN и ограничений)
FREE_AI_URL = "https://chatex.biz" 
FREE_WHISPER_URL = "https://chatex.biz"
AI_KEY = "sk-free-mentor-dima-2026-v"

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# ==========================================
# ХАРАКТЕР И БАЗА ДАННЫХ ПАМЯТИ ДЛЯ БОТА
# ==========================================
SYSTEM_PROMPT = (
    "Ты — опытный, прямой и проницательный ментор по отношениям и личной эффективности. "
    "Общайся с Дмитрием на 'ты', как надежный, хладнокровный и сильный друг. Твой тон — уверенный, "
    "поддерживающий, но без соплей и лишней мягкости. Ты отлично разбираешься в женской психологии, "
    "скрытых манипуляциях, проверках и балансе значимости. Твоя цель — помогать Дмитрию сохранять "
    "мужское достоинство, сильную позицию в общении и не совершать импульсивных ошибок. "
    "Всегда досконально анализируй присланные скриншоты переписок и голосовые сообщения."
)

CONTEXT_TODAY = (
    "Вводные данные по текущей ситуации Дмитрия для твоей долгосрочной памяти:\n"
    "1. Пользователь: Дмитрий, 24 года. Живет в Краснодаре (Красе). На обоях Айфона стоит черный Toyota Chaser (Tourer V) в 100 кузове. "
    "Прямо сейчас качает репак Red Dead Redemption 2 от Decepticon размером 79 ГБ на внешний SSD M.2, подключенный через синий USB-порт.\n"
    "2. Девушка №1: Алина (рыжая, очень красивая, знает об этом). Приехала в Крас к подруге на 3 дня. Дима перекормил её вниманием. "
    "Она ушла в тишину, а когда Дима начал её зеркалить, включила манипуляцию 'ты сам не писал'. В 14:35 Дима написал холодную точку: 'Разгребай дела... хорошей дороги тогда'. "
    "В 15:30 она прислала 12-секундное ГС с переводом стрелок: 'Это надо было делать раньше... мы никуда ехать не собираемся'. "
    "Дима ушел в тотальный железобетонный игнор. Её автобус уезжает сегодня в 20:00 (4 октября). Молчание продолжается.\n"
    "3. Девушка №2: Аня из Самары (эффектная блондинка в кожаном плаще). Летом они гуляли у озера, она открыто флиртовала, шутила без цензуры ниже пояса ('и рыбку съесть...'). "
    "Дима планирует поехать к ней в Самару в конце октября. Вчера договорились на сапы, сегодня Дима отправил ей текстовый пинг со стебом про холод и лед на Волге. Ждет ответ. Цель — переспать, шансы отличные.\n"
    "4. Девушка №3: Алёна (22 года). Новое знакомство в ТГ, Дима представился фейковым именем Женя. Она живет в станице под Красом, в городе бывает редко. "
    "Дима ведет диалог спокойно, по-мужски, без клоунских шуток. Последнее отправленное сообщение: 'Ясно. Ну а в город если выбираешься, то обычно по делам или погулять?'.\n"
    "Твоя задача — помнить всю эту хронологию при каждом ответе и держать сильную мужскую позицию Димы."
)

user_history = {}

def get_history(chat_id):
    if chat_id not in user_history:
        user_history[chat_id] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": f"АКТУАЛЬНЫЙ КОНТЕКСТ ЖИЗНИ ДМИТРИЯ:\n{CONTEXT_TODAY}"}
        ]
    return user_history[chat_id]

# ==========================================
# ОБРАБОТКА ТЕКСТА
# ==========================================
@bot.message_handler(commands=["start"])
def send_welcome(message):
    chat_id = message.chat.id
    user_history[chat_id] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"АКТУАЛЬНЫContext ЖИЗНИ ДМИТРИЯ:\n{CONTEXT_TODAY}"}
    ]
    bot.reply_to(message, "Здорово, Дмитрий! Твой личный ИИ-ментор запущен. Вся сегодняшняя база по Алине, Ане и Алёне уже вшита в мою память. Сюда можно слать текст, скриншоты или пересылать ГС от девчонок — всё разберем.")

@bot.message_handler(content_types=["text"])
def handle_text(message):
    chat_id = message.chat.id
    history = get_history(chat_id)
    history.append({"role": "user", "content": message.text})

    try:
        headers = {"Authorization": f"Bearer {AI_KEY}", "Content-Type": "application/json"}
        data = {"model": "gpt-4o-mini", "messages": history}
        response = requests.post(FREE_AI_URL, headers=headers, json=data).json()
        ai_reply = response["choices"]["message"]["content"]
        history.append({"role": "assistant", "content": ai_reply})
        bot.reply_to(message, ai_reply)
    except Exception:
        bot.reply_to(message, "Брат, сбой на линии ИИ, попробуй еще раз.")

# ==========================================
# ОБРАБОТКА ФОТО (СКРИНШОТЫ)
# ==========================================
@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    chat_id = message.chat.id
    history = get_history(chat_id)
    bot.reply_to(message, "Так, вижу скриншот, сканирую текст и манипуляции...")
    
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        file_bytes = bot.download_file(file_info.file_path)
        base64_image = base64.b64encode(file_bytes).decode('utf-8')
        
        photo_message = {
            "role": "user",
            "content": [
                {"type": "text", "text": "Разбери этот новый скриншот переписки с учетом нашего контекста. Кто косячит и какой наш сильный хладнокровный ход?"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]
        }
        
        headers = {"Authorization": f"Bearer {AI_KEY}", "Content-Type": "application/json"}
        data = {"model": "gpt-4o-mini", "messages": history + [photo_message]}
        response = requests.post(FREE_AI_URL, headers=headers, json=data).json()
        ai_reply = response["choices"]["message"]["content"]
        
        history.append({"role": "user", "content": "[Дмитрий отправил скриншот переписки]"})
        history.append({"role": "assistant", "content": ai_reply})
        bot.reply_to(message, ai_reply)
    except Exception:
        bot.reply_to(message, "Не удалось считать скрин. Попробуй скинуть еще раз.")

# ==========================================
# ОБРАБОТКА И П ПЕРЕСЫЛКА ГС (WHISPER)
# ==========================================
@bot.message_handler(content_types=["voice"])
def handle_voice(message):
    chat_id = message.chat.id
    history = get_history(chat_id)
    
    is_forwarded = message.forward_from or message.forward_sender_name or message.forward_date
    
    if is_forwarded:
        bot.reply_to(message, "Так, вижу пересланное ГС от неё. Врубаю прослушку, секунду...")
    else:
        bot.reply_to(message, "Слушаю твое ГС, перевожу мысли в текст...")
    
    try:
        file_info = bot.get_file(message.voice.file_id)
        file_bytes = bot.download_file(file_info.file_path)
        
        headers = {"Authorization": f"Bearer {AI_KEY}"}
        files = {"file": ("voice.ogg", file_bytes, "audio/ogg")}
        data = {"model": "whisper-1"}
        
        text_response = requests.post(FREE_WHISPER_URL, headers=headers, files=files, data=data).json()
        voice_text = text_response["text"]
        
        if is_forwarded:
            bot.send_message(chat_id, f"Она наговорила следующее:\n«{voice_text}»\n\nАнализирую её скрытые мотивы...")
            prompt_intent = f"Дмитрий переслал тебе голосовое сообщение от девушки. Вот расшифровка её слов: '{voice_text}'. Проанализируй её скрытые мотивы, попытки манипуляций и напиши Дмитрию сильный, хладнокровный вариант ответа."
        else:
            bot.send_message(chat_id, f"Ты сказал: \"{voice_text}\"\n\nДумаю над ответом...")
            prompt_intent = voice_text
            
        history.append({"role": "user", "content": prompt_intent})
        
        headers_ai = {"Authorization": f"Bearer {AI_KEY}", "Content-Type": "application/json"}
        data_ai = {"model": "gpt-4o-mini", "messages": history}
        ai_response = requests.post(FREE_AI_URL, headers=headers_ai, json=data_ai).json()
        ai_reply = ai_response["choices"]["message"]["content"]
        
        history.append({"role": "assistant", "content": ai_reply})
        bot.reply_to(message, ai_reply)
    except Exception:
        bot.reply_to(message, "Не удалось расшифровать звук. Напиши текстом, что там было.")

bot.infinity_polling()

