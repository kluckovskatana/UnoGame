import socketio
import customtkinter as ctk
import threading
import pygame
import sys

HOST = "http://127.0.0.1:5555"

sio = socketio.Client()

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ===================== Socket.IO події =====================
@sio.event
def connect():
    print("Підключено до сервера")

@sio.event
def disconnect():
    print("Відключено від сервера")

@sio.event
def players(data):
    # оновлюємо список онлайн гравців
    text = "Онлайн:\n" + "\n".join(data)
    players_list.configure(text=text)

@sio.event
def start_game():
    print("Гра стартує!")
    threading.Thread(target=run_pygame_game).start()  # Pygame в окремому потоці

# ===================== Функції =====================
def connect_to_server():
    nickname = entry.get().strip()
    if nickname == "":
        return

    try:
        sio.connect(HOST)
        sio.emit("join", nickname)

        entry.configure(state="disabled")
        btn.configure(state="disabled", text="Підключено")
    except Exception as e:
        print("Помилка підключення:", e)

# ===================== Pygame Гра =====================
def run_pygame_game():
    pygame.init()
    WIDTH, HEIGHT = 600, 600
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Уно")

    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 36)

    running = True
    while running:
        screen.fill((200, 255, 200))  # світло-зелений фон

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False


        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    print("Pygame вікно закрите")

# ===================== GUI =====================
root = ctk.CTk()
root.title("Онлайн гра")
root.geometry("350x400")
root.resizable(False, False)

title = ctk.CTkLabel(root, text="Мережева гра", font=ctk.CTkFont(size=20, weight="bold"))
title.pack(pady=15)

entry = ctk.CTkEntry(root, placeholder_text="Введи нік", width=200)
entry.pack(pady=10)

btn = ctk.CTkButton(root, text="Увійти", command=lambda: threading.Thread(target=connect_to_server).start())
btn.pack(pady=10)

players_list = ctk.CTkLabel(root, text="Онлайн:\n-", justify="left")
players_list.pack(pady=20)

root.mainloop()
