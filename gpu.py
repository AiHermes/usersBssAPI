import os
import requests
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
USER_ID = 5077522918  # Убедись, что это ID пользователя, а не бота

def get_chat_info(user_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChat"
    params = {"chat_id": user_id}
    response = requests.get(url, params=params)
    data = response.json()
    if not data.get("ok"):
        print("❌ Не удалось получить информацию о чате.")
        return None
    return data["result"]

def get_user_profile_photo(user_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUserProfilePhotos"
    params = {
        "user_id": user_id,
        "limit": 1
    }
    response = requests.get(url, params=params)
    data = response.json()

    if not data.get("ok") or data["result"]["total_count"] == 0:
        print("❌ Фото не найдено или пользователь не писал боту.")
        return None

    file_id = data["result"]["photos"][0][0]["file_id"]
    print(f"✅ Найден file_id: {file_id}")
    return file_id

def get_file_url(file_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile"
    params = {"file_id": file_id}
    response = requests.get(url, params=params)
    data = response.json()

    if not data.get("ok"):
        print("❌ Не удалось получить file_path.")
        return None

    file_path = data["result"]["file_path"]
    photo_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
    return photo_url

if __name__ == "__main__":
    print(f"🔍 Проверяем user_id: {USER_ID}")

    chat_info = get_chat_info(USER_ID)
    if chat_info:
        print(f"✅ Пользователь найден: {chat_info.get('first_name')} (bot: {chat_info.get('is_bot')})")
    else:
        print("⛔ Ошибка: неправильный user_id или пользователь не писал боту.")
        exit()

    file_id = get_user_profile_photo(USER_ID)
    if file_id:
        photo_url = get_file_url(file_id)
        if photo_url:
            print(f"📷 Ссылка на изображение: {photo_url}")
