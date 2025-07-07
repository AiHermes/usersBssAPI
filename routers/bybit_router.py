from fastapi import APIRouter, HTTPException
from services.bybit_service import is_user_direct_referral

router = APIRouter()

# Оставляем только основной эндпоинт
@router.get("/check_bybit_referral/{user_uid}")
async def check_bybit_referral_endpoint(user_uid: str):
    """
    Эндпоинт для проверки статуса прямого реферала Bybit по UID.
    """
    if not user_uid:
        raise HTTPException(status_code=400, detail="UID пользователя не указан.")
    
    is_referral = is_user_direct_referral(user_uid)
    
    return {
        "uid": user_uid,
        "is_direct_referral": is_referral
    }