import os
import json
import logging
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

# Загружаем переменные из .env файла
load_dotenv()

def initialize_firebase():
    """Инициализирует Firebase Admin SDK, если он еще не был инициализирован."""
    if not firebase_admin._apps:
        logging.info("Инициализация Firebase...")
        try:
            # Пытаемся получить креды из переменной окружения (для Railway)
            firebase_creds_json_str = os.getenv("FIREBASE_CREDENTIALS_JSON")
            if firebase_creds_json_str:
                cred_dict = json.loads(firebase_creds_json_str)
                cred = credentials.Certificate(cred_dict)
                logging.info("Firebase инициализирован из переменной окружения.")
            else:
                # --- ИЗМЕНЕНИЕ ЗДЕСЬ ---
                # Иначе ищем локальный файл по указанному вами пути
                cred_path = ".secrets/bss2025-b1285-firebase-adminsdk-fbsvc-d578014c5e.json"
                logging.info(f"Ищем ключ Firebase по локальному пути: {cred_path}")
                cred = credentials.Certificate(cred_path)
            
            firebase_admin.initialize_app(cred)
            logging.info("✅ Firebase успешно инициализирован.")
        except Exception as e:
            # Выводим более детальную ошибку, если файл все равно не найден
            if isinstance(e, FileNotFoundError):
                 logging.error(f"❌ Файл ключа не найден по пути: {cred_path}. Убедитесь, что он на месте.")
            else:
                logging.exception(f"❌ Непредвиденная ошибка при инициализации Firebase: {e}")
            return None
    
    return firestore.client()

# Инициализируем и экспортируем клиент БД для использования в других модулях
db = initialize_firebase()