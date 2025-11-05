import random
import pygame


pygame.init()
window = pygame.display.set_mode((800, 600))


def how_away(a, b):
    return ((a.x - b.x) ** 2 + (a.y - b.y) ** 2) ** 0.5


class ChemicalElement:
    def __init__(self, x, y, name, charge, connect):
        self.x = x
        self.y = y
        self.name = name
        self.charge = charge
        self.connect = connect

    def draw(self):
        color = (0, 255, 0) if self.charge > 0 else (255, 0, 0) if self.charge < 0 else (0, 0, 255)
        pygame.draw.circle(window, color, (self.x, self.y), 20)
        font = pygame.font.SysFont(None, 24)
        text = font.render(self.name, True, (255, 255, 255))
        window.blit(text, (self.x - text.get_width() // 2, self.y - text.get_height() // 2))

    def random_move(self):
        self.x += random.randint(-1, 1)
        self.y += random.randint(-1, 1)
        self.x = max(20, min(780, self.x))
        self.y = max(20, min(580, self.y))

    def move_mouse(self, mouse_pos):
        self.x, self.y = mouse_pos

    def move_to(self, other, attract):
        speed = 2
        dx = 1 if self.x < other.x else -1 if self.x > other.x else 0
        dy = 1 if self.y < other.y else -1 if self.y > other.y else 0

        if attract:
            self.x += dx * speed
            self.y += dy * speed
        else:
            self.x -= dx * speed
            self.y -= dy * speed

    def connect_to(self, other):
        if other not in self.connect:
            self.connect.append(other)

        dist = how_away(self, other)

        if dist < 35:
            self.move_to(other, False)
        elif dist < 80:
            pygame.draw.line(window, (255, 255, 255), (self.x, self.y), (other.x, other.y), 10)
        elif dist > 200:
            if other in self.connect:
                self.connect.remove(other)
        else:
            pygame.draw.line(window, (255, 255, 255), (self.x, self.y), (other.x, other.y), 10)
            self.move_to(other, True)


chem = [
    ChemicalElement(100, 100, "H", 1, []),
    ChemicalElement(200, 200, "Cl", -1, [])
]

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()

    window.fill((0, 0, 0))

    for c in chem:
        mouse_pos = pygame.mouse.get_pos()
        if (pygame.mouse.get_pressed()[0] and
                ((c.x - mouse_pos[0]) ** 2 + (c.y - mouse_pos[1]) ** 2) ** 0.5 < 20):
            c.move_mouse(mouse_pos)
        else:
            c.random_move()

    # обробка зв’язків між усіма елементами
    for i in range(len(chem)):
        for j in range(i + 1, len(chem)):
            c1, c2 = chem[i], chem[j]
            if how_away(c1, c2) < 90:
                c1.connect_to(c2)
                c2.connect_to(c1)

    for c in chem:
        c.draw()

    pygame.display.flip()
    pygame.time.delay(10)
