import pygame
import math
import sys
import random

pygame.init()

# ==== ГЛОБАЛЬНІ КОНСТАНТИ ====
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 800

fps = 60

# Фізика
gravity = 0.5
bounce_factor = 1.03
max_speed = 17

# Кольори
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
DARK_GRAY = (50, 50, 50)


# ==== КЛАСИ ====
def draw_text(surface, text, pos, color=WHITE, font_size=24):
    font = pygame.font.Font("PressStart2P-Regular.ttf", font_size)
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect(center=pos)
    surface.blit(text_surface, text_rect)


def check_collision_with_ring(ball, ring):
    # Вектор від центра кільця до м'яча
    dx = ball.x - ring.x
    dy = ball.y - ring.y
    dist = math.hypot(dx, dy)

    # Визначаємо чи всередині кільця (з урахуванням радіусу м'яча)
    inner_limit = ring.radius - ring.thickness / 2 - ball.radius - 5
    outer_limit = ring.radius + ring.thickness / 2 + ball.radius + 100

    if inner_limit <= dist <= outer_limit:
        # Нормалізований вектор
        if dist == 0:
            return  # уникнення ділення на 0
        nx = dx / dist
        ny = dy / dist

        # Віддзеркалення швидкості по нормалі
        dot = ball.vx * nx + ball.vy * ny
        ball.vx -= 2 * dot * nx
        ball.vy -= 2 * dot * ny

        # Енерговтрати
        ball.vx *= bounce_factor
        ball.vy *= bounce_factor

        # Відштовхування за межу, щоб не застряг
        overlap = outer_limit - dist if dist > ring.radius else dist - inner_limit - 10
        ball.x += nx * overlap * 0.5
        ball.y += ny * overlap * 0.5

        ring.radius -= 0.01  # Зменшення радіусу кільця при зіткненні


class Ball:
    def __init__(self, x, y, radius=10, color=RED):
        self.x = x
        self.y = y
        self.radius = radius
        self.vx = 0
        self.vy = 0
        self.color = color

    def apply_physics(self):
        self.vy += gravity
        # Обмеження швидкості
        speed = math.hypot(self.vx, self.vy)
        if speed > max_speed:
            factor = max_speed / speed
            self.vx *= factor
            self.vy *= factor

    def rect(self):
        return pygame.Rect(self.x - self.radius, self.y - self.radius, self.radius * 2, self.radius * 2)

    def move(self):
        if not self.y > SCREEN_HEIGHT:
            self.x += self.vx
            self.y += self.vy
        else:
            self.x = SCREEN_WIDTH // 2
            self.y = SCREEN_HEIGHT // 2
            self.vx = random.randint(-5, 5)
            self.vy = random.randint(-5, 5)

    def draw(self, surface):
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.radius)


class RingSegment:
    def __init__(self, x, y, radius=200, thickness=10, color=GREEN):
        self.x = x
        self.y = y
        self.radius = radius
        self.thickness = thickness
        self.color = color

    def draw(self, surface):
        pygame.draw.circle(surface, self.color, (self.x, self.y), self.radius + self.thickness // 2, self.thickness)

    def update(self):
        self.radius -= 0.5


# ==== ІНІЦІАЛІЗАЦІЯ ====

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
clock = pygame.time.Clock()

balls = [
    Ball(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2,
         color=(random.randint(0,255), random.randint(0,255), random.randint(0,255))) for _ in range(70)
]
for ball in balls:
    ball.vx = random.randint(-5, 5)
    ball.vy = random.randint(-5, 5)

# Кільце — можеш додати ще одне з іншим кольором / радіусом
ring = RingSegment(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, radius=400, thickness=10, color=GREEN)

# ==== ГОЛОВНИЙ ЦИКЛ ====
running = True
paused = False
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_SPACE:
                paused = not paused
            elif event.key == pygame.K_r:
                for ball in balls:
                    ball.vx, ball.vy = random.randint(-5, 5), random.randint(-5, 5)

            elif event.key == pygame.K_UP:
                fps += 10
            elif event.key == pygame.K_DOWN:
                fps = fps - 10 if fps > 1 else 1

            elif event.key == pygame.K_RIGHT:
                bounce_factor += 0.01
            elif event.key == pygame.K_LEFT:
                bounce_factor -= 0.01 if bounce_factor > 0.01 else 0

    screen.fill((0, 0, 0))
    real_fps = int(clock.get_fps())
    draw_text(screen, f"FPS: {real_fps}", (150, 50), color=WHITE)
    draw_text(screen, f"Bounce: {bounce_factor:.2f}", (200, 100), color=WHITE)

    # Фізика
    if not paused:
        for ball in balls:
            ball.apply_physics()
            ball.move()

        for i in balls:
            for j in balls:
                if i != j and pygame.Rect.colliderect(i.rect(), j.rect()):
                    # Відштовхування м'ячів
                    dx = j.x - i.x
                    dy = j.y - i.y
                    dist = math.hypot(dx, dy)
                    if dist != 0:
                        overlap = (i.radius + j.radius) - dist
                        nx = dx / dist
                        ny = dy / dist
                        i.x -= nx * overlap / 2
                        i.y -= ny * overlap / 2
                        j.x += nx * overlap / 2
                        j.y += ny * overlap / 2
                        # Обмінятися швидкостями по напрямку зіткнення
                        vi = i.vx * nx + i.vy * ny
                        vj = j.vx * nx + j.vy * ny
                        i.vx += (vj - vi) * nx
                        i.vy += (vj - vi) * ny
                        j.vx += (vi - vj) * nx
                        j.vy += (vi - vj) * ny


    for ball in balls:
        if ring.radius - 20 <= ball.radius:
            ball.vx = random.randint(-5, 5)
            ball.vy = random.randint(-5, 5)
            ring = RingSegment(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, radius=400, thickness=10,
                               color=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
        else:
            check_collision_with_ring(ball, ring)
        ball.draw(screen)

    ring.draw(screen)

    pygame.display.flip()
    clock.tick(fps)

pygame.quit()
sys.exit()
