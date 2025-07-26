# services/remote_config_service.py
import os
import logging
import time
import requests
from datetime import datetime # <-- Добавлен импорт для работы с датой
from google.oauth2 import service_account
from google.auth.transport.requests import Request as AuthRequest

def signal_update():
    """
    Обновляет параметр в Firebase Remote Config через прямой вызов REST API,
    записывая дату и время в виде строки.
    """
    try:
        logging.info("[REMOTE_CONFIG_API] Начало обновления флага через REST API...")
        
        project_id = os.getenv("GCP_PROJECT_ID")
        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not project_id or not creds_path:
            logging.error("[REMOTE_CONFIG_API] Переменные GCP_PROJECT_ID или GOOGLE_APPLICATION_CREDENTIALS не установлены.")
            return False

        scopes = ['https://www.googleapis.com/auth/firebase.remoteconfig']
        creds = service_account.Credentials.from_service_account_file(creds_path, scopes=scopes)
        
        creds.refresh(AuthRequest())
        access_token = creds.token
        
        url = f"https://firebaseremoteconfig.googleapis.com/v1/projects/{project_id}/remoteConfig"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        logging.info("[REMOTE_CONFIG_API] Получаю текущий шаблон (GET)...")
        response_get = requests.get(url, headers=headers)
        response_get.raise_for_status() 

        template = response_get.json()
        etag = response_get.headers.get('ETag')

        parameter_name = 'users_last_updated'
        
        # --- ИЗМЕНЕНИЕ ЗДЕСЬ: Форматируем текущее время в строку ---
        current_value = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if 'parameters' not in template:
            template['parameters'] = {}
            
        template['parameters'][parameter_name] = {
            'defaultValue': {'value': current_value}
        }
        logging.info(f"[REMOTE_CONFIG_API] Устанавливаю новое значение: {current_value}")
        
        headers_put = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json; UTF-8',
            'If-Match': etag
        }
        
        logging.info("[REMOTE_CONFIG_API] Публикую обновленный шаблон (PUT)...")
        response_put = requests.put(url, json=template, headers=headers_put)
        response_put.raise_for_status()

        logging.info(f"✅ [REMOTE_CONFIG_API] Шаблон успешно опубликован.")
        return True

    except Exception as e:
        logging.exception(f"❌ [REMOTE_CONFIG_API] Не удалось установить флаг в Remote Config: {e}")
        return False