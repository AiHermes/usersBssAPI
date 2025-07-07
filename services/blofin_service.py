import os
import hmac
import base64
import logging
from datetime import datetime, timezone
import requests
import json
from uuid import uuid4 # <-- 1. Импортируем генератор для nonce

# ... (API_KEY, SECRET_KEY, и т.д. остаются без изменений)
API_KEY = os.getenv("BLOFIN_API_KEY")
SECRET_KEY = os.getenv("BLOFIN_SECRET_KEY")
PASSPHRASE = os.getenv("BLOFIN_PASSPHRASE")
BASE_URL = "https://api.blofin.com"


def _get_signature(timestamp: str, method: str, request_path: str, nonce: str, body: str = "") -> str:
    """Генерирует подпись для запроса, включая nonce."""
    # --- ИЗМЕНЕНИЕ ЗДЕСЬ: Собираем строку как в документации ---
    message = request_path + method.upper() + timestamp + nonce + body
    
    mac = hmac.new(bytes(SECRET_KEY, 'utf-8'), bytes(message, 'utf-8'), digestmod='sha256')
    
    # --- ИЗМЕНЕНИЕ ЗДЕСЬ: Сначала в hex, потом в base64 ---
    hex_signature = mac.hexdigest().encode('utf-8')
    return base64.b64encode(hex_signature).decode('utf-8')


def test_blofin_connection() -> dict:
    """
    Тестовая функция с правильной подписью.
    """
    if not all([API_KEY, SECRET_KEY, PASSPHRASE]):
        # ...
        return {"status": "error", "message": "API ключи не настроены"}

    try:
        method = "GET"
        request_path = "/api/v1/account/balance"
        
        timestamp = str(int(datetime.now().timestamp() * 1000))
        nonce = str(uuid4()) # <-- 2. Генерируем nonce

        # Генерируем подпись, передавая nonce
        signature = _get_signature(timestamp, method, request_path, nonce)

        # Формируем заголовки, добавляя nonce
        headers = {
            "ACCESS-KEY": API_KEY,
            "ACCESS-SIGN": signature,
            "ACCESS-TIMESTAMP": timestamp,
            "ACCESS-NONCE": nonce, # <-- 3. Добавляем nonce в заголовки
            "ACCESS-PASSPHRASE": PASSPHRASE,
            "Content-Type": "application/json"
        }

        # ... (остальной код запроса и вывода остается без изменений) ...
        response = requests.get(BASE_URL + request_path, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(json.dumps(response.json(), indent=2))
        response.raise_for_status()
        return response.json()

    except Exception as e:
        # ...
        return {"status": "error", "message": str(e)}