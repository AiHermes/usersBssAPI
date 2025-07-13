import logging
from fastapi import APIRouter, Request
from pydantic import BaseModel
from services.bingx_service import link_bingx_uid  # ✅ только нужная функция

router = APIRouter()
logger = logging.getLogger(__name__)


# 🔹 Модель запроса для проверки UID
class ReferralCheckRequest(BaseModel):
    uid: str


# 🔹 Модель запроса для привязки UID к Telegram ID
class LinkUIDRequest(BaseModel):
    telegram_id: str
    uid: str


# 🔹 Проверка UID — является ли рефералом (заглушка, если нужно — добавим логику)
@router.post("/check-referral")
async def check_referral_uid(request: Request, body: ReferralCheckRequest):
    uid = body.uid
    logger.info(f"[BINGX] ▶️ Запрос /check-referral | UID: {uid}")
    try:
        from services.bingx_service import find_uid_info  # локальный импорт (если понадобится)
        result = find_uid_info(uid)
        logger.info(f"[BINGX] ✅ Результат: {result}")
        return {
            "status": "success" if result.get("found") else "error",
            "message": "FOUND" if result.get("found") else "NOT_FOUND"
        }
    except Exception as e:
        logger.exception(f"[BINGX] ❌ Ошибка при проверке UID {uid}: {str(e)}")
        return {"status": "error", "message": "INTERNAL_ERROR"}


# 🔹 Привязка UID к Telegram ID
@router.post("/link-uid")
async def link_uid_to_user(request: Request, body: LinkUIDRequest):
    telegram_id = body.telegram_id
    uid = body.uid
    logger.info(f"[BINGX] ▶️ Запрос /link-uid | Telegram ID: {telegram_id} | UID: {uid}")

    try:
        result = link_bingx_uid(telegram_id, uid)
        logger.info(f"[BINGX] ✅ Результат привязки: {result}")
        return result
    except Exception as e:
        logger.exception(f"[BINGX] ❌ Ошибка при привязке UID {uid}: {str(e)}")
        return {"status": "error", "message": "INTERNAL_ERROR"}
