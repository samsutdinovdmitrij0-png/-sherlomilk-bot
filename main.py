import os
import telebot
import subprocess

# Токен автоматически подтянется из настроек бесплатного сервера
API_TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "🕵️‍♂️ Привет! Я автоматический бот Sherlomilk.\nОтправь мне никнейм человека (например: ivanov), и я найду его аккаунты по всему интернету!")

@bot.message_handler(func=lambda message: True)
def search_username(message):
    username = message.text.strip().replace("@", "")
    
    # Защита от пробелов и лишних символов
    if " " in username or ";" in username or "|" in username:
        bot.reply_to(message, "❌ Пожалуйста, введите корректный никнейм одной строкой без пробелов.")
        return

    bot.reply_to(message, f"🔍 Запускаю глубокий поиск для: {username}...\nЭто займет около 1-2 минут.")
    
    try:
        # Запуск оригинальной утилиты sherlock внутри сервера
        result = subprocess.run(
            ['sherlock', username, '--timeout', '1'], 
            capture_output=True, 
            text=True, 
            check=False
        )
        
        if result.stdout:
            output = result.stdout
            if len(output) > 4000:
                output = output[:4000] + "\n\n...и еще несколько ссылок."
            bot.send_message(message.chat.id, output)
        else:
            bot.send_message(message.chat.id, "❌ Ничего не найдено в базах данных.")
            
    except Exception as e:
        bot.send_message(message.chat.id, "⚠️ Произошел сбой программы. Напишите никнейм еще раз.")

bot.infinity_polling()
