import socketio
import eventlet

# створюємо сервер Socket.IO
sio = socketio.Server(cors_allowed_origins="*")
app = socketio.WSGIApp(sio)

clients = {}  # sid -> nickname
game_started = False  # стан гри


@sio.event
def connect(sid, environ):
    print(f"[+] Нове підключення: {sid}")


@sio.event
def disconnect(sid):
    global game_started
    if sid in clients:
        nickname = clients[sid]
        print(f"[-] {nickname} вийшов")
        del clients[sid]
        send_players()
        # якщо гравців менше 2 — гра зупиняється
        if game_started and len(clients) < 2:
            game_started = False
            sio.emit("stop_game")


@sio.event
def join(sid, nickname):
    global game_started
    clients[sid] = nickname
    print(f"[+] {nickname} підключився")
    send_players()

    # Якщо підключилось 2 гравці і гра ще не почалася — стартуємо гру
    if len(clients) == 2 and not game_started:
        game_started = True
        print("Стартує гра!")
        sio.emit("start_game")  # всім клієнтам сигнал про старт гри


def send_players():
    players_list = list(clients.values())
    print(f"Онлайн: {players_list}")
    sio.emit("players", players_list)


# запуск сервера
if __name__ == "__main__":
    print("Socket.IO сервер запущено...")
    eventlet.wsgi.server(eventlet.listen(("0.0.0.0", 5555)), app)
