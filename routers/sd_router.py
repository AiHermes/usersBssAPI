# filename: routers/sd_router.py
from fastapi import APIRouter, Query
import logging

from services.firebase_service import get_db_client
from services.sd_service import process_sd_request

router = APIRouter(prefix="/sd", tags=["service-desk"])

@router.api_route("/notify", methods=["GET", "POST"])
def sd_notify(
    id: str = Query(..., description="Telegram ID пользователя"),
    sd: str = Query(..., description="Код шаблона Service Desk (например, msg_sd)"),
):
    """
    Создаёт задание на отправку сообщения пользователю:
    - выбирает первый активный бот по приоритету: bssbot → binbot → bybbot
    - кладёт документ в коллекцию 'messages' (status='pending'), без картинки
    """
    db = get_db_client()
    if not db:
        return {"status": "error", "message": "Database connection failed."}

    result = process_sd_request(db, id, sd)
    logging.info(f"[sd_notify] id={id} sd={sd} -> {result.get('status')}, bot={result.get('bot')}")
    return result
