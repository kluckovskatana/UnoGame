import socketio
from PIL import Image
import customtkinter as ctk
import threading
import pygame
import sys
import numpy as np

player_name = None
HOST = "http://127.0.0.1:5555"

# Game state received from server
game_state = {
    "your_hand": [],
    "top_card": None,
    "current_turn_name": None,
    "is_your_turn": False,
    "players_card_counts": [],
    "winner": None,
    "chain_number": None,   # number string like "5", or None
    "has_drawn": False,
}

sio = socketio.Client()

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ===================== Socket.IO Events =====================
@sio.event
def connect():
    print("Підключено до сервера")

@sio.event
def disconnect():
    print("Відключено від сервера")

@sio.event
def players(data):
    text = "Онлайн:\n" + "\n".join(data)
    players_list.configure(text=text)

@sio.event
def start_game(player_names):
    """Сервер сигналізує про початок гри."""
    print("Гра почалась! Гравці:", player_names)
    threading.Thread(target=run_pygame_game, daemon=True).start()

@sio.event
def game_update(state):
    """Отримуємо оновлений стан гри від сервера."""
    global game_state
    game_state.update(state)
    print(f"Хід: {state['current_turn_name']} | Верхня: {state['top_card']} | Рука: {state['your_hand']}")

@sio.event
def error_msg(msg):
    print(f"[Помилка сервера] {msg}")

# ===================== Card Rendering =====================
HUE_MAP = {
    "R": 0,
    "G": 85,
    "B": 170,
    "Y": 42
}

_image_cache = {}

def shift_hue(pil_image, hue_shift):
    img = pil_image.convert("HSV")
    data = np.array(img)
    data[..., 0] = (data[..., 0] + hue_shift) % 255
    img = Image.fromarray(data, "HSV").convert("RGB")
    return pygame.image.fromstring(img.tobytes(), img.size, img.mode)

def load_card_image(card_code, width=90, height=75):
    if card_code in _image_cache:
        return _image_cache[card_code]
    number = card_code[:-1]   # everything except last char
    color_letter = card_code[-1]
    pil_image = Image.open(f"./images/{number}_red.png").convert("RGB")
    pil_image = pil_image.resize((width, height))
    hue_shift = HUE_MAP.get(color_letter, 0)
    surface = shift_hue(pil_image, hue_shift)
    _image_cache[card_code] = surface
    return surface

def load_card_back(width=90, height=75):
    if "BACK" in _image_cache:
        return _image_cache["BACK"]
    try:
        img = Image.open("./images/card_back.png").convert("RGB").resize((width, height))
        surface = pygame.image.fromstring(img.tobytes(), img.size, img.mode)
    except FileNotFoundError:
        surface = pygame.Surface((width, height))
        surface.fill((30, 30, 180))
    _image_cache["BACK"] = surface
    return surface

# ===================== Підключення =====================
def get_cyrillic_font(size, bold=False):
    """Повертає шрифт з підтримкою кирилиці."""
    candidates = ["dejavusans", "freesans", "liberationsans", "arial", "notosans", "ubuntu"]
    for name in candidates:
        try:
            f = pygame.font.SysFont(name, size, bold=bold)
            # Перевіряємо чи шрифт рендерить кирилицю (не порожній surface)
            test = f.render("Тест", True, (0, 0, 0))
            if test.get_width() > 10:
                return f
        except Exception:
            continue
    return pygame.font.SysFont(None, size, bold=bold)  # fallback

def connect_to_server():
    global player_name
    nickname = entry.get().strip()
    player_name = nickname
    if not nickname:
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
    WIDTH, HEIGHT = 900, 680
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("UNO — Онлайн")
    clock = pygame.time.Clock()

    font       = get_cyrillic_font(20, bold=True)
    font_big   = get_cyrillic_font(36, bold=True)
    font_small = get_cyrillic_font(15)

    CARD_W, CARD_H  = 80, 110
    CARD_SPACING    = 88
    GREEN_TABLE     = (34, 139, 34)
    YELLOW          = (255, 230, 0)
    ORANGE          = (255, 140, 0)
    WHITE           = (255, 255, 255)
    RED_ERR         = (255, 80, 80)
    GREY            = (160, 160, 160)

    # Centre layout
    draw_pile_rect = pygame.Rect(WIDTH // 2 - 110, HEIGHT // 2 - CARD_H // 2, CARD_W, CARD_H)
    top_card_rect  = pygame.Rect(WIDTH // 2 + 30,  HEIGHT // 2 - CARD_H // 2, CARD_W, CARD_H)

    # Action buttons  (drawn dynamically, rects computed each frame)
    btn_end_turn = pygame.Rect(0, 0, 130, 40)   # "End Turn / Skip"
    btn_draw     = pygame.Rect(0, 0, 130, 40)   # "Draw Card"

    card_rects   = []   # [(rect, card_code), ...]
    error_flash  = ""
    error_timer  = 0

    running = True
    while running:
        screen.fill(GREEN_TABLE)
        gs = game_state

        chain    = gs.get("chain_number")
        has_drawn = gs.get("has_drawn", False)
        my_turn  = gs["is_your_turn"]

        # Position buttons bottom-right area
        btn_end_turn.topleft = (WIDTH - 155, HEIGHT - 110)
        btn_draw.topleft     = (WIDTH - 155, HEIGHT - 60)

        # ── Events ────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos

                # Card in hand clicked
                for rect, card_code in card_rects:
                    if rect.collidepoint(pos):
                        if my_turn:
                            sio.emit("play_card", card_code)
                        else:
                            error_flash = "Не ваш хід!"
                            error_timer = 90
                        break

                # Draw pile clicked
                if draw_pile_rect.collidepoint(pos):
                    if my_turn:
                        if not has_drawn and chain is None:
                            sio.emit("draw_card")
                        elif has_drawn:
                            error_flash = "Вже брали карту цього ходу!"
                            error_timer = 90
                        elif chain is not None:
                            error_flash = "Не можна брати під час ланцюжка!"
                            error_timer = 90
                    else:
                        error_flash = "Не ваш хід!"
                        error_timer = 90

                # End Turn button clicked
                if btn_end_turn.collidepoint(pos):
                    if my_turn:
                        sio.emit("end_turn")
                    else:
                        error_flash = "Не ваш хід!"
                        error_timer = 90

                # Draw button clicked (duplicate of draw pile, convenience)
                if btn_draw.collidepoint(pos):
                    if my_turn:
                        if not has_drawn and chain is None:
                            sio.emit("draw_card")
                        elif has_drawn:
                            error_flash = "Вже брали карту цього ходу!"
                            error_timer = 90
                        elif chain is not None:
                            error_flash = "Не можна брати під час ланцюжка!"
                            error_timer = 90
                    else:
                        error_flash = "Не ваш хід!"
                        error_timer = 90

        # ── Opponents at top ──────────────────────────────────
        y_top = 15
        for info in gs["players_card_counts"]:
            name  = info["name"]
            count = info["count"]
            if name == player_name:
                continue
            label = font.render(f"{name}: {count} карт", True, WHITE)
            screen.blit(label, (20, y_top))
            for i in range(min(count, 12)):
                back = load_card_back(46, 64)
                screen.blit(back, (220 + i * 50, y_top))
            y_top += 80

        # ── Draw pile ─────────────────────────────────────────
        back_img = load_card_back(CARD_W, CARD_H)
        # Dim draw pile if player can't use it
        draw_available = my_turn and not has_drawn and chain is None
        if not draw_available:
            dimmed = back_img.copy()
            dimmed.set_alpha(100)
            screen.blit(dimmed, draw_pile_rect.topleft)
        else:
            pygame.draw.rect(screen, YELLOW, draw_pile_rect.inflate(6, 6), 3)
            screen.blit(back_img, draw_pile_rect.topleft)
        draw_lbl = font_small.render("ВЗЯТИ", True, WHITE)
        screen.blit(draw_lbl, (draw_pile_rect.centerx - draw_lbl.get_width() // 2,
                                draw_pile_rect.bottom + 4))

        # ── Top card (discard) ────────────────────────────────
        top_card = gs["top_card"]
        if top_card:
            try:
                top_surf = load_card_image(top_card, CARD_W, CARD_H)
                screen.blit(top_surf, top_card_rect.topleft)
            except Exception:
                pygame.draw.rect(screen, (200, 50, 50), top_card_rect)
            lbl = font_small.render(top_card, True, WHITE)
            screen.blit(lbl, (top_card_rect.centerx - lbl.get_width() // 2,
                               top_card_rect.bottom + 4))

        # ── Chain banner ──────────────────────────────────────
        if chain is not None and my_turn:
            banner_surf = font.render(f"Ланцюжок! Грайте {chain} або завершіть хід", True, ORANGE)
            screen.blit(banner_surf, (WIDTH // 2 - banner_surf.get_width() // 2,
                                      HEIGHT // 2 + CARD_H // 2 + 35))

        # ── Turn indicator ────────────────────────────────────
        if my_turn:
            turn_text = font.render("ВАШ ХІД", True, YELLOW)
        else:
            name = gs["current_turn_name"] or "..."
            turn_text = font.render(f"Хід: {name}", True, (200, 200, 200))
        screen.blit(turn_text, (WIDTH // 2 - turn_text.get_width() // 2,
                                 HEIGHT // 2 + CARD_H // 2 + 8))

        # ── Your hand ─────────────────────────────────────────
        hand = gs["your_hand"]
        card_rects = []
        total_width = len(hand) * CARD_SPACING - (CARD_SPACING - CARD_W)
        start_x = max(10, WIDTH // 2 - total_width // 2)
        y_hand = HEIGHT - CARD_H - 20

        for i, card_code in enumerate(hand):
            x    = start_x + i * CARD_SPACING
            rect = pygame.Rect(x, y_hand, CARD_W, CARD_H)
            card_num = card_code[:-1]

            # Determine if this card is playable right now
            if my_turn:
                if chain is not None:
                    playable = (card_num == chain)
                    highlight_col = ORANGE if playable else None
                else:
                    playable = can_play_client(card_code, top_card)
                    highlight_col = YELLOW if playable else None
            else:
                playable = False
                highlight_col = None

            # Draw highlight glow
            if highlight_col:
                glow = pygame.Surface((CARD_W + 10, CARD_H + 10), pygame.SRCALPHA)
                glow.fill((*highlight_col, 160))
                screen.blit(glow, (x - 5, y_hand - 5))
            elif not my_turn or not playable:
                # Dim non-playable cards on your turn
                pass  # keep normal rendering

            try:
                card_surf = load_card_image(card_code, CARD_W, CARD_H)
                if my_turn and not playable:
                    card_surf = card_surf.copy()
                    card_surf.set_alpha(140)
                screen.blit(card_surf, rect.topleft)
            except Exception:
                pygame.draw.rect(screen, GREY, rect)
                lbl = font_small.render(card_code, True, (0, 0, 0))
                screen.blit(lbl, (x + 5, y_hand + 40))

            card_rects.append((rect, card_code))

        # ── Action buttons ────────────────────────────────────
        # End Turn button — always shown on your turn
        et_color  = (180, 60, 60) if my_turn else (80, 80, 80)
        et_border = RED_ERR if my_turn else GREY
        pygame.draw.rect(screen, et_color,  btn_end_turn, border_radius=8)
        pygame.draw.rect(screen, et_border, btn_end_turn, 2, border_radius=8)
        et_lbl = font.render("Завершити хід", True, WHITE)
        screen.blit(et_lbl, (btn_end_turn.centerx - et_lbl.get_width() // 2,
                               btn_end_turn.centery - et_lbl.get_height() // 2))

        # Draw button — greyed out if already drawn or chain active
        can_draw  = my_turn and not has_drawn and chain is None
        dr_color  = (50, 120, 200) if can_draw else (70, 70, 70)
        dr_border = (100, 180, 255) if can_draw else GREY
        pygame.draw.rect(screen, dr_color,  btn_draw, border_radius=8)
        pygame.draw.rect(screen, dr_border, btn_draw, 2, border_radius=8)
        dr_lbl_text = "Взяти карту" if not has_drawn else "Вже взяли"
        dr_lbl = font.render(dr_lbl_text, True, WHITE if can_draw else GREY)
        screen.blit(dr_lbl, (btn_draw.centerx - dr_lbl.get_width() // 2,
                               btn_draw.centery - dr_lbl.get_height() // 2))

        # ── Error flash ───────────────────────────────────────
        if error_timer > 0:
            err_surf = font.render(error_flash, True, RED_ERR)
            screen.blit(err_surf, (WIDTH // 2 - err_surf.get_width() // 2, HEIGHT // 2 - 90))
            error_timer -= 1

        # ── Winner overlay ────────────────────────────────────
        winner = gs.get("winner")
        if winner:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            screen.blit(overlay, (0, 0))
            msg_text = "ВИ ПЕРЕМОГЛИ!" if winner == player_name else f"{winner} переміг!"
            msg_col  = YELLOW if winner == player_name else RED_ERR
            msg = font_big.render(msg_text, True, msg_col)
            screen.blit(msg, (WIDTH // 2 - msg.get_width() // 2, HEIGHT // 2 - 40))
            hint = font.render("Закрийте вікно для виходу", True, (200, 200, 200))
            screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT // 2 + 20))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    print("Pygame window closed")

def can_play_client(card, top):
    """Client-side check to highlight playable cards (mirrors server logic)."""
    if top is None:
        return True
    card_num, card_color = card[:-1], card[-1]
    top_num, top_color  = top[:-1], top[-1]
    return card_color == top_color or card_num == top_num

# ===================== GUI =====================
root = ctk.CTk()
root.title("UNO Онлайн")
root.geometry("350x400")
root.resizable(False, False)

title = ctk.CTkLabel(root, text="UNO Онлайн", font=ctk.CTkFont(size=22, weight="bold"))
title.pack(pady=15)

entry = ctk.CTkEntry(root, placeholder_text="Введіть нікнейм", width=200)
entry.pack(pady=10)

btn = ctk.CTkButton(root, text="Увійти", command=lambda: threading.Thread(target=connect_to_server).start())
btn.pack(pady=10)

players_list = ctk.CTkLabel(root, text="Онлайн:\n-", justify="left")
players_list.pack(pady=20)

root.mainloop()