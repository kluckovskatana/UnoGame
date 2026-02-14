import socketio
import eventlet
from eventlet import wsgi
from flask import Flask

sio = socketio.Server(cors_allowed_origins="*")  # дозволяємо всі джерела
app = Flask(__name__)

players = []  # список підключених гравців
colors = ['G', 'R', 'B', 'Y']
numbers = [str(i) for i in range(10)]

result = [f"{num}_{color}" for color in colors for num in numbers]
# ===================== Socket.IO події =====================
@sio.event
def connect(sid, environ):
    print(f"Підключено: {sid}")

@sio.event
def disconnect(sid):
    global players
    print(f"Відключено: {sid}")
    # видаляємо гравця за sid
    for p in players:
        if p["sid"] == sid:
            players.remove(p)
            break
    # надсилаємо оновлений список всім
    sio.emit("players", [p["name"] for p in players])

@sio.event
def join(sid, nickname):
    global players
    print(f"{nickname} приєднався")
    players.append({"sid": sid, "name": nickname})
    # надсилаємо список усім клієнтам
    sio.emit("players", [p["name"] for p in players])

    # якщо двоє гравців, стартуємо гру
    if len(players) == 2:
        sio.emit("start_game")
        print("Гра стартує!")

# ===================== Запуск сервера =====================
if __name__ == "__main__":
    app = socketio.WSGIApp(sio, app)
    print("Сервер запущено на http://127.0.0.1:5555")
    wsgi.server(eventlet.listen(("0.0.0.0", 5555)), app)
