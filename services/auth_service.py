import hmac
import hashlib
import urllib.parse
import json
import os
from typing import Optional, Dict

def validate_telegram_init_data(init_data: str) -> Optional[Dict]:
    """
    Валидация initData, полученной от Telegram WebApp.
    Алгоритм реализован строго по спецификации Telegram:
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-web-app
    """
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        print("❌ BOT_TOKEN не найден в переменных окружения")
        return None

    try:
        # Разбор строки initData в словарь
        parsed_qs = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
        print(f"📥 Исходные данные: {parsed_qs}")

        received_hash = parsed_qs.pop("hash", None)
        if not received_hash:
            print("❌ Параметр hash отсутствует в initData")
            return None

        # Оставшиеся поля форматируются как "ключ=значение"
        # и сортируются в алфавитном порядке ключей
        data_check_list = [f"{k}={v}" for k, v in sorted(parsed_qs.items())]
        data_check_string = "\n".join(data_check_list)

        print("📤 Строка для проверки подписи (data_check_string):")
        print(data_check_string)

        # Ключ: HMAC_SHA256("WebAppData", bot_token)
        secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()

        # Вычисляем контрольный хеш
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        print(f"🔑 Хеш от Telegram: {received_hash}")
        print(f"🔐 Вычисленный HMAC: {calculated_hash}")

        # Сравнение с использованием безопасной функции
        if not hmac.compare_digest(calculated_hash, received_hash):
            print("❌ Подпись не совпадает — данные не подлинные")
            return None

        print("✅ Подпись подтверждена — данные валидны")
        return parsed_qs

    except Exception as e:
        print(f"💥 Ошибка при валидации данных: {e}")
        return None
