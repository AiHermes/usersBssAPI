# routers/blofin_router.py
from fastapi import APIRouter, Request
from pydantic import BaseModel
import logging
from services.blofin_service import link_blofin_uid

router = APIRouter()  # ❗ Без prefix и tags

# 📦 Модель запроса
class BlofinLinkRequest(BaseModel):
    telegram_id: str
    blofin_uid: str

# 🔗 Привязка UID
@router.post("/link-uid")
async def link_blofin_uid_endpoint(payload: BlofinLinkRequest, request: Request):
    telegram_id = payload.telegram_id
    blofin_uid = payload.blofin_uid
    logging.info(f"[API][BLOFIN] ▶️ Запрос: POST /link-uid | telegram_id: {telegram_id}, blofin_uid: {blofin_uid}")

    try:
        result = link_blofin_uid(telegram_id, blofin_uid)

        if result.get("status") == "success":
            logging.info(f"[API][BLOFIN] ✅ Привязка успешна: {result}")
            return result

        elif result.get("message") == "ERROR_TAKEN":
            logging.warning(f"[API][BLOFIN] ⚠️ UID уже занят другим пользователем.")
            return result

        elif result.get("message") == "ERROR_NOT_FOUND":
            logging.warning(f"[API][BLOFIN] ⚠️ UID не найден среди твоих приглашённых.")
            return result

        else:
            logging.warning(f"[API][BLOFIN] ⚠️ Неизвестная ошибка при привязке: {result}")
            return {
                "status": "error",
                "message": result.get("message", "Unknown error")
            }

    except Exception as e:
        logging.exception(f"[API][BLOFIN] ❌ Критическая ошибка при привязке UID {blofin_uid}")
        return {
            "status": "error",
            "message": "Internal Server Error"
        }
