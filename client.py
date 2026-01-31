import socket
import threading
import tkinter as tk

HOST = '127.0.0.1'  # IP сер
PORT = 5555

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

def connect():
    nickname = entry.get()
    if nickname == "":
        return

    client.connect((HOST, PORT))
    client.send(nickname.encode())

    entry.config(state="disabled")
    btn.config(state="disabled")

    threading.Thread(target=receive).start()

def receive():
    while True:
        try:
            players = client.recv(1024).decode()
            players_list.config(text="Онлайн:\n" + players.replace(",", "\n"))
        except:
            break

# вікно
root = tk.Tk()
root.title("Онлайн гра")
root.geometry("300x300")
root.resizable(False, False)

tk.Label(root, text="Введи нік:", font=("Arial", 12)).pack(pady=10)

entry = tk.Entry(root, font=("Arial", 12))
entry.pack()

btn = tk.Button(root, text="Увійти", font=("Arial", 12), command=connect)
btn.pack(pady=10)

players_list = tk.Label(root, text="Онлайн:\n-", font=("Arial", 10))
players_list.pack(pady=10)

root.mainloop()
