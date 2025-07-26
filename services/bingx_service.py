# bingx_service.py
import os
import time
import hmac
import requests
from hashlib import sha256
from dotenv import load_dotenv
from config import get_db_client

load_dotenv()

API_KEY = os.getenv("BINGX_API_KEY")
SECRET_KEY = os.getenv("BINGX_SECRET_KEY")
BASE_URL = "https://open-api.bingx.com"

def generate_signature(params_map: dict) -> tuple[str, str]:
    sorted_keys = sorted(params_map)
    params_str = "&".join([f"{key}={params_map[key]}" for key in sorted_keys])
    signature = hmac.new(SECRET_KEY.encode(), params_str.encode(), digestmod=sha256).hexdigest()
    return signature, params_str

def get_referrals_page(page_index: int = 1, page_size: int = 50):
    timestamp = str(int(time.time() * 1000))
    params_map = {
        "pageIndex": str(page_index),
        "pageSize": str(page_size),
        "timestamp": timestamp
    }
    signature, params_str = generate_signature(params_map)
    url = f"{BASE_URL}/openApi/agent/v1/account/inviteAccountList?{params_str}&signature={signature}"
    headers = {"X-BX-APIKEY": API_KEY}
    response = requests.get(url, headers=headers)
    try:
        return response.json()
    except Exception:
        return {"code": -1, "msg": "INVALID_JSON", "data": {}}

def find_uid_info(uid: str) -> dict:
    page = 1
    while True:
        result = get_referrals_page(page_index=page)
        if result.get("code") != 0:
            return {"found": False}
        data = result.get("data", {})
        referrals = data.get("list", [])
        if not isinstance(referrals, list):
            return {"found": False}
        for ref in referrals:
            if isinstance(ref, dict) and str(ref.get("uid")) == str(uid):
                return {
                    "found": True,
                    "kyc": ref.get("kycResult", False)
                }
        if len(referrals) < 50:
            break
        page += 1
    return {"found": False}

def link_bingx_uid(telegram_id: str, uid: str) -> dict:
    db = get_db_client()
    if not db:
        return {"status": "error", "message": "DATABASE_ERROR"}
    ref_info = find_uid_info(uid)
    if not ref_info["found"]:
        return {"status": "error", "message": "ERROR_NOT_FOUND"}
    users_ref = db.collection("telegram_users")
    conflicting = users_ref.where("bingx_uid", "==", uid).stream()
    conflicting_users = [doc.id for doc in conflicting]
    if conflicting_users and telegram_id not in conflicting_users:
        return {"status": "error", "message": "ERROR_TAKEN"}
    try:
        user_doc = users_ref.document(telegram_id)
        update_data = {"bingx_uid": uid}
        raw_kyc = ref_info.get("kyc", False)
        if isinstance(raw_kyc, bool) and raw_kyc is True:
            update_data["bingx_kyc"] = "KYC"
        user_doc.set(update_data, merge=True)
        return {"status": "success", "message": f"UID {uid} привязан к пользователю {telegram_id}"}
    except Exception:
        return {"status": "error", "message": "FIRESTORE_WRITE_ERROR"}
