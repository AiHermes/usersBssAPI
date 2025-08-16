# filename: start_rw.py
import os
import base64
import logging
import sys
import uvicorn
from pathlib import Path

# --- ЛОГИ В STDOUT (чтобы Railway не красил всё в error) ---
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("RailwayStart")


def ensure_firebase_creds():
    b64 = os.environ.get("GOOGLE_CREDENTIALS_BASE64")
    if not b64:
        logger.error("❌ GOOGLE_CREDENTIALS_BASE64 не задана")
        raise SystemExit(1)
    path = "/tmp/google_credentials.json"
    try:
        Path(path).write_bytes(base64.b64decode(b64))
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = path
        os.environ["GOOGLE_CREDENTIALS_PATH"] = path  # на случай, если где-то используется
        logger.info(f"✅ Firebase credentials сохранены в {path}")
    except Exception as e:
        logger.exception(f"❌ Ошибка при сохранении ключа Firebase: {e}")
        raise SystemExit(1)


def main():
    logger.info("🚀 Запуск BssMiniApp сервиса на Railway...")
    ensure_firebase_creds()

    # Важно: тут уже есть GOOGLE_APPLICATION_CREDENTIALS
    logger.info("🌐 Запуск FastAPI через Uvicorn...")
    try:
        uvicorn.run("main:app", host="0.0.0.0", port=8000)
    except Exception:
        logger.exception("❌ Uvicorn завершился с ошибкой")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
