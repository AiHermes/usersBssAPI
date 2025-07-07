from fastapi import APIRouter
# Импортируем нашу новую тестовую функцию
from services.blofin_service import test_blofin_connection

router = APIRouter()

@router.get("/test-connection")
async def test_connection_endpoint():
    """
    Эндпоинт для проверки базового подключения к Blofin API.
    """
    result = test_blofin_connection()
    return result