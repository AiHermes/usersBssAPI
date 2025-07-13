import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from config import get_db_client, setup_logger  # 👈 добавили setup_logger

# 🟢 Инициализация логгера
setup_logger()  # 👈 вызываем до создания логгера

logger = logging.getLogger(__name__)

# Импорт роутеров
from routers import (
    wallets_router,
    subscriptions_router,
    checkin_router,
    blofin_router,
    bybit_router,
    user_router,
    bingx_router  # 🆕 Добавлен роутер BingX
)

app = FastAPI(
    title="BssMiniApp API",
    description="Сервис для генерации кошельков и обработки API для BssMiniApp.",
    version="1.0.0"
)

# CORS настройки
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
logger.info("🔗 Подключение роутеров...")
app.include_router(wallets_router.router, prefix="/api", tags=["Wallets"])
app.include_router(subscriptions_router.router, prefix="/api", tags=["Subscriptions"])
app.include_router(checkin_router.router, prefix="/api", tags=["Check-in"])
app.include_router(blofin_router.router, prefix="/api/blofin", tags=["BloFin"])
app.include_router(bybit_router.router, prefix="/api/bybit", tags=["Bybit"])
app.include_router(user_router.router, prefix="/api", tags=["Users"])
app.include_router(bingx_router.router, prefix="/api/bingx", tags=["BingX"])
logger.info("✅ Все роутеры подключены")

@app.get("/", tags=["Root"])
def read_root():
    """Корневой эндпоинт для проверки работы сервиса."""
    logger.info("[ROOT] Проверка подключения к базе данных...")
    db = get_db_client()
    if not db:
        logger.error("[ROOT] ❌ Не удалось подключиться к базе данных.")
        return {"status": "error", "message": "Failed to connect to Database"}
    logger.info("[ROOT] ✅ API готов к работе.")
    return {"status": "ok", "message": "Welcome to BssMiniApp API"}

if __name__ == "__main__":
    logger.info("🚀 Запуск BssMiniApp API на http://0.0.0.0:8000")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
