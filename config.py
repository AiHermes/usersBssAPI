import os
import logging
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

load_dotenv()

# Глобальная переменная для хранения одного экземпляра клиента БД
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
            # Проверяем, было ли уже инициализировано приложение
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
            return None # Возвращаем None в случае ошибки
            
    return _db_client