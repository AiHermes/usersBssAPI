# start_rw.py
import os
import base64
import logging

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s - %(message)s")

logging.info("🚀 Запуск BssMiniApp сервиса на Railway...")

# Получаем ключ из переменных окружения
creds_b64 = os.getenv("GOOGLE_CREDENTIALS_BASE64")
if not creds_b64:
    logging.error("❌ Переменная GOOGLE_CREDENTIALS_BASE64 не задана")
    raise SystemExit(1)

# Сохраняем JSON во временный файл
creds_path = "/tmp/google_credentials.json"
try:
    with open(creds_path, "wb") as f:
        f.write(base64.b64decode(creds_b64))
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path
    logging.info(f"✅ Firebase credentials сохранены в {creds_path}")
except Exception as e:
    logging.error(f"❌ Ошибка при сохранении ключа: {e}")
    raise SystemExit(1)

# Теперь можно импортировать main, когда переменная уже установлена
import uvicorn

if __name__ == "__main__":
    logging.info("🌐 Запуск FastAPI через Uvicorn...")
    try:
        uvicorn.run("main:app", host="0.0.0.0", port=8000)
    except Exception as e:
        logging.error(f"❌ Uvicorn завершился с ошибкой: {e}")
        raise
