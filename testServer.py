import socketio
import eventlet

# створюємо сервер Socket.IO
sio = socketio.Server(cors_allowed_origins="*")
app = socketio.WSGIApp(sio)

clients = {}  # sid -> nickname


@sio.event
def connect(sid, environ):
    print(f"[+] Нове підключення: {sid}")


@sio.event
def disconnect(sid):
    if sid in clients:
        nickname = clients[sid]
        print(f"[-] {nickname} вийшов")
        del clients[sid]
        send_players()


@sio.event
def join(sid, nickname):
    clients[sid] = nickname
    print(f"[+] {nickname} підключився")
    send_players()


def send_players():
    players_list = list(clients.values())
    print(f"Онлайн: {players_list}")
    sio.emit("players", players_list)


# запуск сервера
if __name__ == "__main__":
    print("Socket.IO сервер запущено...")
    eventlet.wsgi.server(eventlet.listen(("0.0.0.0", 5555)), app)
