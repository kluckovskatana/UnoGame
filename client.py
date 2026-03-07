import socketio
from PIL import Image
import customtkinter as ctk
import threading
import pygame
import sys
import numpy as np

data = None
player_name = None
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
def start_game(players):
    global data
    data = players
    threading.Thread(target=run_pygame_game).start()  # Pygame в окремому потоці

# Map card letters to approximate hue shift (0–255 in HSV)
HUE_MAP = {
    "R": 0,    # red, no shift
    "G": 85,   # green
    "B": 170,  # blue
    "Y": 42    # yellow
}

def shift_hue(pil_image, hue_shift):
    """Shift the hue of a PIL image and convert to Pygame surface."""
    img = pil_image.convert("HSV")
    data = np.array(img)
    data[..., 0] = (data[..., 0] + hue_shift) % 255  # Hue channel
    img = Image.fromarray(data, "HSV").convert("RGB")
    return pygame.image.fromstring(img.tobytes(), img.size, img.mode)

def load_card_image(card_code):
    """Load base card and shift its hue according to card color."""
    number = card_code[0]
    color_letter = card_code[1]

    pil_image = Image.open(f"./images/{number}_red.png").convert("RGB")
    # Resize the image (ERROR)
    pil_image = pil_image.resize((90,75))
    hue_shift = HUE_MAP.get(color_letter, 0)

    return shift_hue(pil_image, hue_shift)

# ===================== Функції =====================
def connect_to_server():
    global player_name
    nickname = entry.get().strip()
    player_name = nickname
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
    WIDTH, HEIGHT = 800, 600
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("UNO")
    clock = pygame.time.Clock()

    # Prepare all players' hands
    players_cards = []
    for player in data:
        if player["name"] == player_name:
            print(f"Твоя рука: {player['hand']}")
            hand_images = [load_card_image(card) for card in player['hand']]
            players_cards.append(hand_images)

    running = True
    while running:
        screen.fill((200, 255, 200))  # light green background

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Draw players' hands (example: one row per player)
        y_offset = 400
        for hand_images in players_cards:
            x_offset = 50
            for img in hand_images:
                screen.blit(img, (x_offset, y_offset))
                x_offset += img.get_width() + 10
            y_offset -= 100  # next player's hand above

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    print("Pygame window closed")

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
