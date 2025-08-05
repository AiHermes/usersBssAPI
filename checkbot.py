import requests
import sys
import os
from dotenv import load_dotenv

# Загружаем переменные из файла .env в окружение
load_dotenv()

# 1. ПОЛУЧАЕМ ТОКЕН ИЗ ОКРУЖЕНИЯ
#    Скрипт ищет файл .env в той же папке.
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Проверка, был ли загружен токен
if not BOT_TOKEN:
    print("❌ ОШИБКА: Токен не найден в переменных окружения.")
    print("   Убедитесь, что в этой же папке есть файл .env")
    print("   и в нем содержится строка вида: BOT_TOKEN='ВАШ_ТОКЕН'")
    sys.exit()

# Формируем URL для запроса getMe
url = f'https://api.telegram.org/bot{BOT_TOKEN}/getMe'

print("Отправка запроса к Telegram API...")

try:
    # Выполняем GET-запрос
    response = requests.get(url, timeout=10)
    
    # Преобразуем ответ в формат JSON
    data = response.json()

    # Проверяем, успешен ли запрос
    if data.get('ok'):
        # Если да, выводим информацию о боте
        bot_info = data.get('result')
        print("\n✅ УСПЕХ! Токен валиден, бот отвечает.")
        print(f"   ID бота: {bot_info.get('id')}")
        print(f"   Имя: {bot_info.get('first_name')}")
        print(f"   Юзернейм: @{bot_info.get('username')}")
    else:
        # Если нет, выводим ошибку от Telegram
        print("\n❌ ОШИБКА! Telegram API вернул ошибку.")
        print(f"   Код ошибки: {data.get('error_code')}")
        print(f"   Описание: {data.get('description')}")
        print("\n   ПРОВЕРЬТЕ ПРАВИЛЬНОСТЬ ТОКЕНА В ФАЙЛЕ .env!")

except requests.exceptions.RequestException as e:
    # Обрабатываем ошибки сети
    print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: Не удалось подключиться к Telegram API.")
    print(f"   Детали: {e}")