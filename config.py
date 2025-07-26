# config.py
import os
import logging
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

# Загружаем .env
load_dotenv()

# 🟢 Настройка логгера
def setup_logger():
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

# 🔁 Глобальный клиент Firestore
_db_client = None

def get_db_client():
    """
    Возвращает клиент Firestore. 
    Инициализирует Firebase при первом вызове.
    """
    global _db_client
    if _db_client is None:
        logging.info("[CONFIG] Создаю или обновляю подключение к Firebase...")
        try:
            if not firebase_admin._apps:
                creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
                if not creds_path:
                    logging.error("Переменная GOOGLE_APPLICATION_CREDENTIALS не установлена!")
                    return None
                
                cred = credentials.Certificate(creds_path)
                firebase_admin.initialize_app(cred)
                logging.info("✅ [CONFIG] Приложение Firebase успешно инициализировано.")

            _db_client = firestore.client()
        except Exception as e:
            logging.exception(f"❌ [CONFIG] Ошибка при инициализации Firebase: {e}")
            return None
            
    return _db_client
