# filename: services/firebase_service.py
import os
import hashlib
import logging
import firebase_admin
from firebase_admin import auth, credentials

logger = logging.getLogger(__name__)

# Используем путь из переменной окружения
cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

if not cred_path:
    logger.error("[FIREBASE_SERVICE] ❌ GOOGLE_APPLICATION_CREDENTIALS не установлена.")
else:
    if not firebase_admin._apps:
        try:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            logger.info(f"[FIREBASE_SERVICE] ✅ Firebase инициализирован с {cred_path}")
        except Exception as e:
            logger.exception(f"[FIREBASE_SERVICE] ❌ Ошибка инициализации Firebase: {e}")

def create_custom_token(telegram_id: int) -> str:
    """
    Генерирует Firebase Custom Token для пользователя с указанным Telegram ID.
    UID = "<telegram_id>" (строго равен Telegram ID, без префиксов).
    """
    try:
        uid = str(telegram_id)  # <-- UID теперь равен телеграм-ID
        token = auth.create_custom_token(uid).decode("utf-8")

        # 🔐 Логируем хеш токена и его начало (безопасно)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        token_snippet = token[:20]

        logger.info(f"[FIREBASE_SERVICE] 🔐 Сгенерирован Firebase токен для UID={uid}")
        logger.info(f"[FIREBASE_SERVICE] 🔑 Хеш токена: {token_hash}")
        logger.info(f"[FIREBASE_SERVICE] 🔑 Начало токена: {token_snippet}...")

        return token

    except Exception as e:
        logger.exception(f"[FIREBASE_SERVICE] ❌ Ошибка при создании токена для {telegram_id}: {e}")
        raise
