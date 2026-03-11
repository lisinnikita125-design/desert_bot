import os
import threading
from flask import Flask, request
from bot import main as bot_main  # ваш основной файл bot.py

app = Flask(__name__)

@app.route('/')
def index():
    return "Bot is running!", 200

@app.route('/health')
def health():
    return "OK", 200

# Запускаем бота в фоновом потоке
def run_bot():
    bot_main()  # предполагается, что в bot.py есть функция main()

thread = threading.Thread(target=run_bot)
thread.daemon = True
thread.start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)