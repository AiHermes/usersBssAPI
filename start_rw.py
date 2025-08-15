# start_rw.py
import os
import base64
import subprocess
import logging
import sys

def setup_logger():
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]  # ⬅️ Пишем в stdout
    )

def main():
    setup_logger()
    logger = logging.getLogger(__name__)

    logger.info("🚀 Запуск BssMiniApp сервиса на Railway...")

    bot_token = os.environ.get("BOT_TOKEN")
    creds_b64 = os.environ.get("GOOGLE_CREDENTIALS_BASE64")

    if not bot_token or not creds_b64:
        logger.error("❌ BOT_TOKEN или GOOGLE_CREDENTIALS_BASE64 не указаны")
        sys.exit(1)

    creds_path = "/tmp/google_credentials.json"
    try:
        with open(creds_path, "wb") as f:
            f.write(base64.b64decode(creds_b64))
        logger.info(f"✅ Firebase credentials сохранены в {creds_path}")
    except Exception as e:
        logger.exception("❌ Ошибка сохранения credentials")
        sys.exit(1)

    logger.info("🌐 Запуск FastAPI через Uvicorn...")
    try:
        subprocess.run(
            ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"],
            check=True
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Uvicorn завершился с ошибкой: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception("❌ Неожиданная ошибка при запуске сервера")
        sys.exit(1)

if __name__ == "__main__":
    main()
