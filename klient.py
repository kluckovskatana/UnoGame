import pygame
from PIL import Image
import numpy as np

# ---------- Налаштування ----------
IMAGE_PATH = "./images/0_red.png"
WIDTH, HEIGHT = 600, 400
FPS = 60

# ---------- Pygame init ----------
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

# ---------- Завантаження зображення ----------
pil_img = Image.open(IMAGE_PATH).convert("RGB")
pil_img = pil_img.resize((WIDTH, HEIGHT))

def shift_hue(pil_image, hue_shift):
    img = pil_image.convert("HSV")
    data = np.array(img)

    # Hue канал (0–255)
    data[..., 0] = (data[..., 0] + hue_shift) % 255

    img = Image.fromarray(data, "HSV").convert("RGB")
    return pygame.image.fromstring(img.tobytes(), img.size, img.mode)

# ---------- Loop ----------
hue = 0
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                hue += 5
                print("Поточний Hue",hue)
    # 155=синій, 40=жовтий, 85=зелений  
    #  # hue = (hue + 1) % 256
    surf = shift_hue(pil_img, hue)

    screen.blit(surf, (0, 0))
    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
