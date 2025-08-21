# services/auth_service.py
import hmac
import hashlib
import urllib.parse
import os
from typing import Optional, Dict, List

def _iter_bot_tokens() -> List[str]:
    """
    Возвращает список токенов-ботов, с которыми нужно уметь валидировать initData.
    - BOT_TOKENS: список через запятую
    - BOT_TOKEN: одиночный токен (fallback)
    """
    tokens: List[str] = []
    multi = os.getenv("BOT_TOKENS", "")
    if multi:
        tokens += [t.strip() for t in multi.split(",") if t.strip()]
    single = os.getenv("BOT_TOKEN", "").strip()
    if single:
        tokens.append(single)

    # убрать дубликаты, сохранив порядок
    seen = set()
    uniq = []
    for t in tokens:
        if t not in seen:
            uniq.append(t)
            seen.add(t)
    return uniq

def _build_data_check_string(parsed_qs: Dict[str, str]) -> str:
    """
    Формирует data_check_string: все пары key=value (кроме 'hash'),
    отсортированные по ключу, соединённые \n.
    """
    items = []
    for k in sorted(parsed_qs.keys()):
        if k == "hash":
            continue
        items.append(f"{k}={parsed_qs[k]}")
    return "\n".join(items)

def validate_telegram_init_data(init_data: str) -> Optional[Dict]:
    """
    Валидация initData, полученной от Telegram WebApp.
    Спецификация: https://core.telegram.org/bots/webapps#validating-data-received-via-the-web-app

    Алгоритм:
      secret_key = HMAC_SHA256(key="WebAppData", msg=bot_token)
      calc_hash  = HMAC_SHA256(key=secret_key, msg=data_check_string)
      сравнить calc_hash с присланным 'hash' (hex).
    """
    tokens = _iter_bot_tokens()
    if not tokens:
        print("❌ Не найдены токены ботов. Установите BOT_TOKEN или BOT_TOKENS")
        return None

    try:
        parsed_qs = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
        print(f"📥 Исходные данные: {parsed_qs}")

        received_hash = parsed_qs.get("hash")
        if not received_hash:
            print("❌ Параметр 'hash' отсутствует в initData")
            return None

        dcs = _build_data_check_string(parsed_qs)
        print("📤 Строка для проверки подписи (data_check_string):")
        print(dcs)

        for idx, token in enumerate(tokens, start=1):
            # ✅ ПРАВИЛЬНЫЙ расчёт secret_key
            secret_key = hmac.new(
                key=b"WebAppData",
                msg=token.encode("utf-8"),
                digestmod=hashlib.sha256
            ).digest()

            calculated_hash = hmac.new(
                key=secret_key,
                msg=dcs.encode("utf-8"),
                digestmod=hashlib.sha256
            ).hexdigest()

            print(f"🔑 Хеш от Telegram: {received_hash}")
            print(f"🔐 Вычисленный HMAC токеном #{idx}: {calculated_hash}")

            if hmac.compare_digest(calculated_hash, received_hash):
                print(f"✅ Подпись подтверждена токеном #{idx} — данные валидны")
                return parsed_qs

        print("❌ Подпись не совпала ни с одним из токенов — данные не подлинные")
        return None

    except Exception as e:
        print(f"💥 Ошибка при валидации данных: {e}")
        return None
