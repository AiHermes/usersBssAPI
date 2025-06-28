from fastapi import FastAPI
import uvicorn
from config import db # Убедимся, что Firebase инициализировался
from routers import wallets_router

# Создаем экземпляр FastAPI
app = FastAPI(
    title="BssMiniApp API",
    description="Сервис для генерации кошельков и обработки API для BssMiniApp.",
    version="1.0.0"
)

# Подключаем роутер для кошельков
app.include_router(wallets_router.router, prefix="/api", tags=["Wallets"])

@app.get("/", tags=["Root"])
def read_root():
    """Корневой эндпоинт для проверки работы сервиса."""
    return {"status": "ok", "message": "Welcome to BssMiniApp API"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)