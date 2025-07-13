import logging
from fastapi import APIRouter, Request
from pydantic import BaseModel
from services.bingx_service import is_uid_my_referral  # 🔧 Импорт исправлен

router = APIRouter()

# 🔹 Логгер
logger = logging.getLogger(__name__)

# 🔹 Модель запроса
class ReferralCheckRequest(BaseModel):
    uid: str

# 🔹 Проверка UID на рефералку
@router.post("/check-referral")
async def check_referral_uid(request: Request, body: ReferralCheckRequest):
    uid = body.uid
    logger.info(f"[BINGX] ▶️ Запрос /check-referral | UID: {uid}")

    try:
        result = is_uid_my_referral(uid)  # 🔧 Имя функции исправлено
        logger.info(f"[BINGX] ✅ Результат: {result}")
        return result
    except Exception as e:
        logger.exception(f"[BINGX] ❌ Ошибка при проверке UID {uid}: {str(e)}")
        return {"status": "error", "message": "INTERNAL_ERROR"}
