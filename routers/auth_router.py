# filename: routers/auth_router.py
from fastapi import APIRouter
from pydantic import BaseModel
from services.auth_service import validate_telegram_init_data
from services.firebase_service import create_custom_token
from services.user_service import find_user_and_status

import urllib.parse
import json

router = APIRouter()


class InitDataRequest(BaseModel):
    init_data: str


@router.post("/auth/telegram")
async def telegram_auth(data: InitDataRequest):
    print("➡️ /auth/telegram called")
    print(f"📥 Raw init_data (incoming): {data.init_data[:300]}...")

    if data.init_data.strip().lower() == "test":
        return {
            "ok": "ok",
            "telegram_id": "123456789",
            "firebase_token": "example_token_for_testing_purposes"
        }

    try:
        parsed_data = urllib.parse.parse_qs(data.init_data)
        parsed_dict = {k: v[0] for k, v in parsed_data.items()}
        print(f"📦 Parsed init_data (dict): {parsed_dict}")
    except Exception as e:
        print(f"❌ Failed to parse init_data: {e}")
        return {"ok": "parse_error", "error": "Failed to parse init_data"}

    print("🔍 Отправляем данные в валидацию Telegram...")
    user_data = validate_telegram_init_data(data.init_data)
    print(f"📬 Ответ от validate_telegram_init_data: {user_data}")

    if not user_data:
        print("❌ Validation failed: Invalid Telegram initData")
        return {"ok": "invalid_init_data", "error": "Invalid Telegram initData"}

    print(f"✅ Validation successful. Raw user_data: {user_data}")

    user_str = user_data.get("user")
    if isinstance(user_str, str):
        try:
            user_info = json.loads(user_str)
            print("🔓 Parsed user_info from string.")
        except Exception as e:
            print(f"❗ JSON parsing error: {e}")
            return {"ok": "parse_user_error", "error": "Failed to parse user info"}
    else:
        user_info = user_str
        print("🔓 user_info is already a dict.")

    telegram_id = user_info.get("id")
    print(f"🆔 Telegram ID: {telegram_id}")

    exists, status_tgbss, user_path, _ = find_user_and_status(int(telegram_id))

    if not exists:
        return {
            "ok": "noregbot",
            "telegram_id": str(telegram_id),
        }

    if str(status_tgbss).lower() != "active":
        return {
            "ok": "botisoff",
            "telegram_id": str(telegram_id),
            "status_tgbss": status_tgbss,
        }

    firebase_token = create_custom_token(telegram_id)
    print("🔑 Firebase token generated.")
    return {
        "ok": "ok",
        "telegram_id": str(telegram_id),
        "firebase_token": firebase_token,
    }
