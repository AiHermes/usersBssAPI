from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging

from services.bybit_service import link_bybit_uid, get_referral_kyc_status

router = APIRouter()

class BybitLinkRequest(BaseModel):
    telegram_id: str
    bybit_uid: str

@router.post("/link-uid")
async def link_bybit_uid_endpoint(request: BybitLinkRequest):
    logging.info(f"[API] POST /link-uid | Body: {request.dict()}")

    result = link_bybit_uid(telegram_id=request.telegram_id, bybit_uid=request.bybit_uid)

    if result["status"] == "error":
        logging.warning(f"[API] Ошибка привязки: {result['message']}")
        raise HTTPException(status_code=409, detail=result["message"])
    
    logging.info(f"[API] Успешная привязка UID: {request.bybit_uid}")
    return result

@router.get("/kyc-status/{user_uid}")
async def get_kyc_status_endpoint(user_uid: str):
    logging.info(f"[API] GET /kyc-status/{user_uid}")
    
    result = get_referral_kyc_status(user_uid)

    if result.get("status") == "error":
        logging.warning(f"[API] Ошибка получения KYC: {result.get('message')}")
        raise HTTPException(status_code=404, detail=result.get("message"))

    logging.info(f"[API] Успешный ответ по KYC: {result}")
    return result
