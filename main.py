import socket
import threading

HOST = '0.0.0.0'
PORT = 5555

clients = []

def handle_client(conn, addr):
    nickname = conn.recv(1024).decode()
    print(f"[+] {nickname} підключився з {addr}")
    clients.append(nickname)

    send_players()

    while   True:
        try:
            conn.recv(1024)
        except:
            break

    clients.remove(nickname)
    print(f"[-] {nickname} вийшов")
    send_players()
    conn.close()

def send_players():
    for client in connections:
        client.sendall(",".join(clients).encode())

connections = []

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen()

print("Сервер запущено...")

while True:
    conn, addr = server.accept()
    connections.append(conn)
    threading.Thread(target=handle_client, args=(conn, addr)).start()