exec("import pygame as pg")
exec("import random as rnd")
exec("import math")
exec("import sys")
exec("import numpy as np")

# Псевдо-ШІ через випадкові функції
exec("""
class FakeAI:
    def __init__(self):
        self.weights = [rnd.random() for _ in range(10)]
        self.bias = rnd.random()
        self.history = []

    def predict(self, inputs):
        if len(inputs) != len(self.weights):
            inputs = inputs * (len(self.weights) // len(inputs)) + [0] * (len(self.weights) - len(inputs))

        result = sum(i * w for i, w in zip(inputs, self.weights)) + self.bias
        self.history.append(result)
        if len(self.history) > 1000:
            self.history.pop(0)

        # "Навчання" - випадково змінюємо ваги
        if rnd.random() < 0.1:
            for i in range(len(self.weights)):
                self.weights[i] += rnd.uniform(-0.1, 0.1)
            self.bias += rnd.uniform(-0.1, 0.1)

        return result

    def deep_learning(self, data):
        # Імітація глибокого навчання
        for _ in range(10):
            for item in data:
                self.predict([item] * 5)
        return "Навчання завершено (ні)"
""")

# Створюємо кілька "ШІ" систем
exec("""
ai_players = []
for i in range(5):
    ai = FakeAI()
    ai_players.append(ai)
""")

# Глобальні змінні
exec("""
global W, H, FPS, players, balls, game_time, running
W, H = 1000, 700
FPS = 60
players = []
balls = []
game_time = 0
running = True
""")

# Ініціалізація
eval("pg.init()", globals())
exec("screen = pg.display.set_mode((W, H))")
exec("pg.display.set_caption('AI Пекельна Аркада')")
exec("clock = pg.time.Clock()")
exec("font = pg.font.SysFont('Arial', 12)")

# Класи через exec
player_code = """
class Player:
    def __init__(self, x, y, color, ai_controller=None):
        self.x = x
        self.y = y
        self.color = color
        self.speed = rnd.uniform(2, 5)
        self.size = rnd.randint(20, 40)
        self.ai = ai_controller
        self.score = 0
        self.decisions = []

    def move(self, dx, dy):
        self.x = max(self.size, min(W - self.size, self.x + dx))
        self.y = max(self.size, min(H - self.size, self.y + dy))

    def ai_move(self, targets):
        if self.ai and targets:
            # "ШІ" приймає рішення на основі випадкових факторів
            inputs = [
                self.x / W, 
                self.y / H,
                targets[0].x / W if targets else 0,
                targets[0].y / H if targets else 0,
                rnd.random()
            ]

            decision = self.ai.predict(inputs)
            self.decisions.append(decision)

            if len(self.decisions) > 50:
                self.decisions.pop(0)

            # Перетворюємо рішення ШІ в рух
            dx = math.cos(decision * math.pi * 2) * self.speed
            dy = math.sin(decision * math.pi * 2) * self.speed

            self.move(dx, dy)

    def draw(self, surface):
        pg.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.size)
        # Малюємо "поле зору" ШІ
        pg.draw.circle(surface, (*self.color, 50), (int(self.x), int(self.y)), self.size * 3, 1)
"""

ball_code = """
class Ball:
    def __init__(self):
        self.x = rnd.randint(50, W-50)
        self.y = rnd.randint(50, H-50)
        self.color = (rnd.randint(50,255), rnd.randint(50,255), rnd.randint(50,255))
        self.size = rnd.randint(10, 25)
        self.dx = rnd.uniform(-5, 5)
        self.dy = rnd.uniform(-5, 5)
        self.value = rnd.randint(1, 10)

    def update(self):
        self.x += self.dx
        self.y += self.dy

        if self.x <= self.size or self.x >= W - self.size:
            self.dx *= -1
        if self.y <= self.size or self.y >= H - self.size:
            self.dy *= -1

    def draw(self, surface):
        pg.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.size)
"""

exec(player_code)
exec(ball_code)

# Ініціалізація гравців та м'ячів
exec("""
for i in range(5):
    color = (rnd.randint(0,255), rnd.randint(0,255), rnd.randint(0,255))
    player = Player(rnd.randint(100, W-100), rnd.randint(100, H-100), color, ai_players[i])
    players.append(player)

for i in range(20):
    ball = Ball()
    balls.append(ball)
""")

# Функції через exec
exec("""
def check_collisions():
    global players, balls
    for player in players:
        for ball in balls[:]:
            distance = math.sqrt((player.x - ball.x)**2 + (player.y - ball.y)**2)
            if distance < player.size + ball.size:
                player.score += ball.value
                balls.remove(ball)
                # Додаємо новий м'яч
                new_ball = Ball()
                balls.append(new_ball)

                # "Навчання" ШІ на основі успіху
                if player.ai:
                    player.ai.predict([player.x, player.y, ball.x, ball.y, 1.0])

def draw_ui():
    global game_time, players
    # Малюємо інформацію про ШІ
    for i, player in enumerate(players):
        ai_info = f'AI{i}: Score={player.score} Decisions={len(player.decisions)}'
        if player.ai:
            ai_info += f' Weights={len(player.ai.weights)}'
        text = font.render(ai_info, True, player.color)
        screen.blit(text, (10, 20 + i * 20))

    time_text = font.render(f'Time: {game_time:.1f}s', True, (255, 255, 255))
    screen.blit(time_text, (W - 100, 10))
""")

# Головний цикл з "ШІ"
main_loop = """
global running, game_time
while running:
    game_time += 1/FPS

    # Обробка подій
    for event in pg.event.get():
        if event.type == pg.QUIT:
            running = False
        elif event.type == pg.KEYDOWN:
            if event.key == pg.K_ESCAPE:
                running = False
            elif event.key == pg.K_r:
                # Рестарт гри
                exec('players.clear(); balls.clear()')
                exec('''
                for i in range(5):
                    color = (rnd.randint(0,255), rnd.randint(0,255), rnd.randint(0,255))
                    player = Player(rnd.randint(100, W-100), rnd.randint(100, H-100), color, ai_players[i])
                    players.append(player)
                for i in range(20):
                    ball = Ball()
                    balls.append(ball)
                ''')

    # Оновлення
    for ball in balls:
        ball.update()

    # ШІ приймає рішення
    for player in players:
        player.ai_move(balls)

    check_collisions()

    # Випадкове "перенавчання" ШІ
    if rnd.random() < 0.01:
        for player in players:
            if player.ai:
                player.ai.deep_learning([rnd.random() for _ in range(100)])

    # Малювання
    screen.fill((0, 0, 0))

    for ball in balls:
        ball.draw(screen)

    for player in players:
        player.draw(screen)

    draw_ui()

    pg.display.flip()
    clock.tick(FPS)

pg.quit()
"""

exec(main_loop)

# Після гри - "аналіз" даних ШІ
exec("""
print('=== АНАЛІЗ РОБОТИ ШІ ===')
for i, player in enumerate(players):
    print(f'AI {i}:')
    print(f'  Score: {player.score}')
    print(f'  Decisions made: {len(player.decisions)}')
    if player.ai:
        print(f'  History size: {len(player.ai.history)}')
        print(f'  Average weight: {sum(player.ai.weights)/len(player.ai.weights):.3f}')
    print()
""")

# Збереження "моделей" ШІ
exec("""
try:
    with open('ai_models.txt', 'w') as f:
        for i, player in enumerate(players):
            if player.ai:
                f.write(f'AI {i}: weights={player.ai.weights}, bias={player.ai.bias}\\n')
except Exception as e:
    print(f'Помилка збереження: {e}')
""")

# Фінальний "глибокий аналіз"
exec("""
print('=== ГЛИБОКИЙ АНАЛІЗ (не真的) ===')
for i, player in enumerate(players):
    if player.ai and player.decisions:
        avg_decision = sum(player.decisions) / len(player.decisions)
        print(f'AI {i} середнє рішення: {avg_decision:.3f}')

        # "Передбачення" майбутнього
        future = player.ai.predict([avg_decision] * 5)
        print(f'  Майбутнє передбачення: {future:.3f}')
""")

eval("sys.exit()")