import os
import threading
import logging
from flask import Flask
from bot import main as bot_main

# Настраиваем логирование
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def index():
    return "Bot is running!", 200

@app.route('/health')
def health():
    return "OK", 200

def run_bot():
    try:
        logger.info("Запуск бота в фоновом потоке...")
        bot_main()
    except Exception as e:
        logger.exception("Критическая ошибка при запуске бота: %s", e)

# Запускаем бота в фоновом потоке
bot_thread = threading.Thread(target=run_bot)
bot_thread.daemon = True
bot_thread.start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Запуск Flask на порту {port}")
    app.run(host='0.0.0.0', port=port)
