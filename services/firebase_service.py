# filename: services/firebase_service.py
import os
import hashlib
import logging
import firebase_admin
from firebase_admin import auth, credentials, firestore

logger = logging.getLogger(__name__)

cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")


def _ensure_firebase_app():
    if firebase_admin._apps:
        return
    if not cred_path:
        logger.error("[FIREBASE_SERVICE] ❌ GOOGLE_APPLICATION_CREDENTIALS не установлена.")
        raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS is not set")
    try:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        logger.info(f"[FIREBASE_SERVICE] ✅ Firebase инициализирован с {cred_path}")
    except Exception as e:
        logger.exception(f"[FIREBASE_SERVICE] ❌ Ошибка инициализации Firebase: {e}")
        raise


_db = None
def get_db_client():
    global _db
    if _db is not None:
        return _db
    _ensure_firebase_app()
    try:
        _db = firestore.client()
        logger.info("[FIREBASE_SERVICE] ✅ Firestore клиент готов")
        return _db
    except Exception as e:
        logger.exception(f"[FIREBASE_SERVICE] ❌ Ошибка создания Firestore клиента: {e}")
        raise


def create_custom_token(telegram_id: int) -> str:
    try:
        _ensure_firebase_app()
        uid = str(telegram_id)
        token = auth.create_custom_token(uid).decode("utf-8")

        token_hash = hashlib.sha256(token.encode()).hexdigest()
        token_snippet = token[:20]

        logger.info(f"[FIREBASE_SERVICE] 🔐 Сгенерирован Firebase токен для UID={uid}")
        logger.info(f"[FIREBASE_SERVICE] 🔑 Хеш токена: {token_hash}")
        logger.info(f"[FIREBASE_SERVICE] 🔑 Начало токена: {token_snippet}...")

        return token
    except Exception as e:
        logger.exception(f"[FIREBASE_SERVICE] ❌ Ошибка при создании токена для {telegram_id}: {e}")
        raise
