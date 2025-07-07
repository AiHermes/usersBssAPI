import os
import time
import hmac
import hashlib
import logging
import requests
import json
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("BYBIT_API_KEY")
SECRET_KEY = os.getenv("BYBIT_SECRET_KEY")
BASE_URL = "https://api.bybit.com"

def _get_bybit_signature(timestamp: str, api_key: str, recv_window: str, secret_key: str, params: str = "") -> str:
    message = timestamp + api_key + recv_window + params
    return hmac.new(bytes(secret_key, "utf-8"), bytes(message, "utf-8"), hashlib.sha256).hexdigest()

def is_user_direct_referral(uid: str) -> bool:
    if not all([API_KEY, SECRET_KEY]):
        logging.error("[BYBIT] API ключи не настроены в .env")
        return False

    try:
        request_path = "/v5/affiliate/aff-user-list"
        cursor = ""

        while True:
            timestamp = str(int(time.time() * 1000))
            recv_window = "10000"
            
            params_dict = {
                "size": 50,
                "cursor": cursor
            }
            params_str = "&".join([f"{k}={v}" for k, v in sorted(params_dict.items())])
            signature = _get_bybit_signature(timestamp, API_KEY, recv_window, SECRET_KEY, params_str)

            headers = {
                'X-BAPI-API-KEY': API_KEY,
                'X-BAPI-SIGN': signature,
                'X-BAPI-TIMESTAMP': timestamp,
                'X-BAPI-RECV-WINDOW': recv_window,
                'Content-Type': 'application/json'
            }

            full_url = BASE_URL + request_path + "?" + params_str
            response = requests.get(full_url, headers=headers)
            response.raise_for_status()
            data = response.json()

            if data.get("retCode") == 0:
                result = data.get("result", {})
                referral_list = result.get("list", [])
                
                # --- ДОБАВЛЕН ВЫВОД ---
                print(f"--- [BYBIT DEBUG] Получено и сравнено {len(referral_list)} записей на этой странице. ---")

                for referral in referral_list:
                    if referral.get("userId") == uid:
                        logging.info(f"[BYBIT] ✅ Пользователь {uid} НАЙДЕН.")
                        return True

                cursor = result.get("nextPageCursor", "")
                if not cursor:
                    logging.info(f"[BYBIT] Все страницы проверены. Пользователь {uid} не найден.")
                    return False
            else:
                logging.error(f"[BYBIT] API вернул ошибку: {data.get('retMsg')}")
                return False

    except Exception as e:
        logging.exception(f"❌ [BYBIT] Критическая ошибка при запросе к API: {e}")
        return False