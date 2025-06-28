Запуск локального сервера и проброска ip
./run_local.sh



▶️ Запуск
Запускай так:

bash
Копировать
Редактировать
./run_server.sh
✅ После этого
Ты вручную запускаешь:

сервер FastAPI:
uvicorn main:app --reload

ngrok:
ngrok http 8000



 1. Найди процесс, который использует порт 8000:
bash
Копировать
Редактировать
lsof -i :8000
Пример вывода:

graphql
Копировать
Редактировать
COMMAND   PID     USER   FD   TYPE             DEVICE SIZE/OFF NODE NAME
Python  12345  aihermes    3u  IPv4 0x...      0t0  TCP localhost:8000 (LISTEN)
✅ 2. Заверши процесс:
Допустим, PID — это 12345:

bash
Копировать
Редактировать
kill -9 12345