# filename: start_rw.py
import os
import base64
import logging
import sys
import uvicorn
from pathlib import Path

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
    Path(path).write_bytes(base64.b64decode(b64))
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = path
    os.environ["GOOGLE_CREDENTIALS_PATH"] = path
    logger.info(f"✅ Firebase credentials сохранены в {path}")

def main():
    logger.info("🚀 Запуск BssMiniApp сервиса на Railway...")
    ensure_firebase_creds()

    # Railway отдаёт нужный порт в PORT. Если не задан — жёстко 8080 (как в твоих настройках).
    port = int(os.environ.get("PORT", "8080"))
    host = "0.0.0.0"
    logger.info(f"🌐 Запуск FastAPI через Uvicorn на http://{host}:{port}")

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )

if __name__ == "__main__":
    main()
