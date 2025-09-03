# filename: services/sd_service.py
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from firebase_admin import firestore

# Приоритет выбора бота по полям статуса в документе пользователя
_STATUS_TO_BOT = [
    ("status_tgbss", "bssbot"),
    ("status_tgbin", "binbot"),
    ("status_tgbyb", "bybbot"),
]

# Шаблоны сообщений по коду sd
SD_TEMPLATES: Dict[str, str] = {
    "msg_sd": (
        "📩 <b>У вас новое сообщение от службы поддержки AIHermes.</b>\n"
        "Зайдите в приложение — сообщение уже ждёт вас в разделе <b>Чат</b>."
    ),
    # TODO: сюда добавим другие коды и тексты по мере необходимости
}


def resolve_bot_for_user(user_data: dict) -> Optional[str]:
    """Возвращает имя бота по приоритету статусов или None, если ни один не активен."""
    for status_field, bot_name in _STATUS_TO_BOT:
        if user_data.get(status_field) == "active":
            return bot_name
    return None


def get_sd_text(sd_code: str) -> Optional[str]:
    """Возвращает текст сообщения по коду sd."""
    return SD_TEMPLATES.get(sd_code)


def create_message_doc(
    db: firestore.Client,
    telegram_id: str,
    bot_name: str,
    text: str,
) -> str:
    """
    Создаёт документ в коллекции messages для сендера.
    Возвращает ID созданного документа.
    """
    now = datetime.now(timezone.utc)
    doc_ref = db.collection("messages").document()  # auto-id
    payload: Dict[str, Any] = {
        "telegram_id": str(telegram_id),
        "status": "pending",
        "bot_name": bot_name,
        "created_at": now,
        "memo": {
            "text": text,
            "buttons": [],  # без картинки и кнопок
        },
    }
    doc_ref.set(payload)
    return doc_ref.id


def process_sd_request(
    db: firestore.Client,
    telegram_id: str,
    sd_code: str,
) -> dict:
    """
    Главная функция: проверяет пользователя, выбирает бот, создаёт задание на отправку.
    """
    # 1) Текст по коду
    text = get_sd_text(sd_code)
    if not text:
        return {"status": "error", "message": f"Unsupported sd code: {sd_code}"}

    # 2) Документ пользователя
    user_ref = db.collection("telegram_users").document(str(telegram_id))
    snap = user_ref.get()
    if not snap.exists:
        return {"status": "error", "message": "User not found", "telegram_id": str(telegram_id)}

    user_data = snap.to_dict() or {}

    # 3) Определяем бот по приоритету
    bot_name = resolve_bot_for_user(user_data)
    if not bot_name:
        return {"status": "error", "message": "No active bots for user", "telegram_id": str(telegram_id)}

    # 4) Создаём сообщение для сендера
    try:
        msg_id = create_message_doc(db, str(telegram_id), bot_name, text)
        logging.info(f"[sd] created message {msg_id} for {telegram_id} via {bot_name} (sd={sd_code})")
        return {
            "status": "ok",
            "telegram_id": str(telegram_id),
            "sd": sd_code,
            "bot": bot_name,
            "messageId": msg_id,
        }
    except Exception as e:
        logging.exception(f"[sd] failed to create message for {telegram_id}: {e}")
        return {"status": "error", "message": str(e), "telegram_id": str(telegram_id)}
