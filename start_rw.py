# start_rw.py
import os
import base64
import subprocess
import logging
import sys

# ===== Настройка логгера =====
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout
)
logger = logging.getLogger("RailwayStart")

logger.info("🚀 Запуск BssMiniApp сервиса на Railway...")

# ===== Читаем переменные окружения =====
bot_token = os.environ.get("BOT_TOKEN")
creds_b64 = os.environ.get("GOOGLE_CREDENTIALS_BASE64")

if not bot_token:
    logger.error("❌ Переменная BOT_TOKEN не найдена!")
    sys.exit(1)

if not creds_b64:
    logger.error("❌ Переменная GOOGLE_CREDENTIALS_BASE64 не найдена!")
    sys.exit(1)

# ===== Сохраняем ключ во временный файл =====
try:
    creds_path = "/tmp/google_credentials.json"
    with open(creds_path, "wb") as f:
        f.write(base64.b64decode(creds_b64))
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path
    logger.info(f"✅ Firebase credentials сохранены в {creds_path}")
except Exception as e:
    logger.exception(f"❌ Ошибка при сохранении ключа Firebase: {e}")
    sys.exit(1)

# ===== Запускаем uvicorn =====
try:
    logger.info("🌐 Запуск FastAPI через Uvicorn...")
    subprocess.run(
        ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"],
        check=True
    )
except subprocess.CalledProcessError as e:
    logger.exception(f"❌ Ошибка при запуске Uvicorn: {e}")
    sys.exit(1)
except Exception as e:
    logger.exception(f"❌ Неизвестная ошибка: {e}")
    sys.exit(1)
