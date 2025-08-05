# services/firebase_service.py

import os
import firebase_admin
from firebase_admin import auth, credentials
import logging

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
    Генерирует Firebase custom token для пользователя с указанным Telegram ID.
    UID в формате 'telegram:{id}'.
    """
    try:
        uid = f"telegram:{telegram_id}"
        token = auth.create_custom_token(uid).decode("utf-8")
        logger.info(f"[FIREBASE_SERVICE] 🔐 Сгенерирован Firebase токен для {uid}")
        return token
    except Exception as e:
        logger.exception(f"[FIREBASE_SERVICE] ❌ Ошибка при создании токена для {telegram_id}: {e}")
        raise
