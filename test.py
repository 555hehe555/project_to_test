# chem_sandbox_realistic.py
# Потрібно: pygame
import pygame, random, math, time
pygame.init()

W, H = 1200, 720
SCREEN = pygame.display.set_mode((W, H))
CLOCK = pygame.time.Clock()
FONT = pygame.font.SysFont(None, 18)
BOLD = pygame.font.SysFont(None, 22)

# ------------------ Конфіги елементів ------------------
# symbol: valence, color, default charge (формальні значення, спрощено)
ELEMENTS = {
    "H":  {"valence": 1, "color": (220,220,255), "charge": 0},
    "O":  {"valence": 2, "color": (255,160,160), "charge": 0},
    "S":  {"valence": 6, "color": (255,210,140), "charge": 0},
    "Na": {"valence": 1, "color": (160,200,255), "charge": +1},
    "Cl": {"valence": 1, "color": (160,255,170), "charge": -1},
    "C":  {"valence": 4, "color": (200,200,200), "charge": 0},
    "Ca": {"valence": 2, "color": (210,190,140), "charge": +2},
}

# заборонені/малоймовірні прямі парні зв'язки (спрощено)
INVALID_PAIRS = {
    ("Na","Na"), ("Ca","Ca"), ("Na","Ca"),
    ("Na","C"), ("Ca","C"), ("Ca","S"), ("Na","S")
}

# готові групи (кластер атомів) - позиції відносно центру
# tuple: (symbol, dx, dy, formal_charge)
GROUP_TEMPLATES = {
    "OH": {
        "atoms": [("O", -18, 0, 0), ("H", 18, 0, 0)],
        "bonds": [(0,1)]
    },
    "H2O": {
        "atoms": [("O", 0, 0, 0), ("H", -36, -12, 0), ("H", 36, -12, 0)],
        "bonds": [(0,1),(0,2)]
    },
    "CO2": {
        "atoms": [("C", 0, 0, 0), ("O", -56, 0, 0), ("O", 56, 0, 0)],
        "bonds": [(0,1),(0,2)]
    },
    "NaCl": {
        "atoms": [("Na", -20, 0, +1), ("Cl", 20, 0, -1)],
        "bonds": [(0,1)]
    },
    # Ca(OH)2: представляємо як Ca2+ + 2 * (OH-) (спрощено формальні заряди)
    "Ca(OH)2": {
        "atoms": [
            ("Ca", 0, 0, +2),
            ("O", -44, -18, -1), ("H", -66, -10, 0),
            ("O", 44, -18, -1), ("H", 66, -10, 0)
        ],
        "bonds": [(0,1),(1,2),(0,3),(3,4)]
    },
    # H2SO4: спрощено як нейтральна молекула (формальний розподіл не деталізуємо)
    "H2SO4": {
        "atoms": [
            ("S", 0, 0, 0),
            ("O", -44, -36, 0), ("O", 44, -36, 0),
            ("O", -44, 36, 0), ("O", 44, 36, 0),
            ("H", -72, 56, 0), ("H", 72, 56, 0)
        ],
        "bonds": [(0,1),(0,2),(0,3),(0,4),(3,5),(4,6)]
    }
}

# UI розмітка
PANEL_W = 220
PANEL_RECT = pygame.Rect(W - PANEL_W, 0, PANEL_W, H)
CANVAS_RECT = pygame.Rect(0, 0, W - PANEL_W, H)

# Фізика та параметри
DIFFUSE = 0.6
ATTRACTION_FACTOR = 80.0   # притягання між протилежними зарядами
REPULSION_FACTOR = 30.0    # відштовхування однакових зарядів
BOND_DIST = 70
BOND_BREAK_DIST = 180
MAX_SPEED = 3.5
UNSTABLE_LIFE = 1.5  # сек

# ------------------ Класи ------------------
class Atom:
    R = 16
    def __init__(self, x, y, symbol, charge=None):
        self.x = float(x); self.y = float(y)
        self.vx = 0.0; self.vy = 0.0
        self.symbol = symbol
        # якщо в шаблоні явно заданий формальний заряд, використовуємо його
        self.charge = ELEMENTS.get(symbol, {}).get("charge", 0) if charge is None else charge
        self.bonds = []  # list of other Atom
        self.fixed = False  # при перетягуванні
        self.id = id(self)

    @property
    def valence(self):
        return ELEMENTS.get(self.symbol, {}).get("valence", 1)

    def free_valence(self):
        return max(0, self.valence - len(self.bonds))

    def draw(self, surf):
        col = ELEMENTS.get(self.symbol, {}).get("color", (200,200,200))
        # outline залежить від заряду
        if self.charge > 0:
            outline = (80,220,100)
        elif self.charge < 0:
            outline = (255,100,100)
        else:
            outline = (180,180,180)
        pygame.draw.circle(surf, outline, (int(self.x), int(self.y)), self.R+3)
        pygame.draw.circle(surf, col, (int(self.x), int(self.y)), self.R)
        txt = FONT.render(self.symbol, True, (10,10,10))
        surf.blit(txt, (self.x - txt.get_width()/2, self.y - txt.get_height()/2))
        if self.charge != 0:
            ch = ("+" if self.charge>0 else "−") + (str(abs(self.charge)) if abs(self.charge)>1 else "")
            ctxt = FONT.render(ch, True, (10,10,10))
            surf.blit(ctxt, (self.x + self.R - 6, self.y - self.R + 2))

class Molecule:
    def __init__(self, atoms=None):
        self.atoms = atoms if atoms else []
        self.unstable_since = None  # timestamp if detected unstable, else None

    def bonds_list(self):
        pairs = []
        seen = set()
        for a in self.atoms:
            for b in a.bonds:
                if a is b: continue
                key = tuple(sorted((a.id, b.id)))
                if key in seen: continue
                seen.add(key)
                pairs.append((a,b))
        return pairs

    def center(self):
        if not self.atoms: return (0,0)
        x = sum(a.x for a in self.atoms)/len(self.atoms)
        y = sum(a.y for a in self.atoms)/len(self.atoms)
        return (x,y)

    def draw(self, surf):
        # bonds
        for a,b in self.bonds_list():
            pygame.draw.line(surf, (200,200,200), (a.x,a.y),(b.x,b.y),6)
        # atoms
        for a in self.atoms:
            a.draw(surf)
        # if unstable - mark
        if self.is_unstable():
            cx,cy = self.center()
            txt = FONT.render("UNSTABLE", True, (255,80,80))
            surf.blit(txt, (cx - txt.get_width()/2, cy - 30))

    def is_unstable(self):
        # 1) надмір зв'язків
        for a in self.atoms:
            if len(a.bonds) > a.valence:
                return True
        # 2) зарядовий дисбаланс (сума формальних зарядів != 0)
        total = sum(a.charge for a in self.atoms)
        if abs(total) > 0.0001:
            return True
        return False

    def update_unstable_timer(self, now):
        if self.is_unstable():
            if self.unstable_since is None:
                self.unstable_since = now
        else:
            self.unstable_since = None

    def should_disassemble(self, now):
        if self.unstable_since is None: return False
        return (now - self.unstable_since) >= UNSTABLE_LIFE

    def disassemble(self):
        # розірвати всі зв'язки всередині молекули
        for a in self.atoms:
            for b in list(a.bonds):
                if b in self.atoms:
                    a.bonds.remove(b)
                    b.bonds.remove(a)
        self.unstable_since = None

# ------------------ Сцена ------------------
molecules = []  # список Molecule

def all_atoms():
    res = []
    for m in molecules:
        res += m.atoms
    return res

def spawn_atom(symbol, x=None, y=None):
    if x is None:
        x = CANVAS_RECT.w/2 + random.randint(-40,40)
    if y is None:
        y = CANVAS_RECT.h/2 + random.randint(-40,40)
    atom = Atom(x,y,symbol)
    mol = Molecule([atom])
    molecules.append(mol)
    return atom

def spawn_group(name, x=None, y=None):
    t = GROUP_TEMPLATES.get(name)
    if t is None: return None
    if x is None:
        x = CANVAS_RECT.w/2 + random.randint(-40,40)
    if y is None:
        y = CANVAS_RECT.h/2 + random.randint(-40,40)
    atoms = []
    for item in t["atoms"]:
        # unpack with optional 4th value (charge)
        if len(item) == 4:
            sym, dx, dy, ch = item
        else:
            sym, dx, dy = item
            ch = None
        atoms.append(Atom(x+dx, y+dy, sym, charge=ch))
    # bonds by indices
    for i,j in t["bonds"]:
        a = atoms[i]; b = atoms[j]
        a.bonds.append(b); b.bonds.append(a)
    mol = Molecule(atoms)
    molecules.append(mol)
    return mol

def spawn_item(key):
    if key in GROUP_TEMPLATES:
        spawn_group(key)
    else:
        spawn_atom(key)

# ------------------ UI ------------------
ATOM_BUTTONS = ["H","O","C","S","Na","Cl","Ca","OH","H2O","CO2","NaCl","Ca(OH)2","H2SO4"]
BUTTONS = []
def build_buttons():
    BUTTONS.clear()
    margin = 10
    x0 = W - PANEL_W + 12
    y0 = 20
    w = PANEL_W - 24
    h = 36
    for i, key in enumerate(ATOM_BUTTONS):
        rect = pygame.Rect(x0, y0 + i*(h+8), w, h)
        BUTTONS.append((rect, key))

build_buttons()

# ------------------ Interaction state ------------------
paused = False
dragging = None  # (atom, offset_x, offset_y, source_molecule)
selected_atom = None  # for manual bonding: first click selects
mouse_down_pos = (0,0)

# ------------------ Utility ------------------
def dist(a,b):
    return math.hypot(a.x-b.x, a.y-b.y)

def distance_points(ax,ay,bx,by):
    return math.hypot(ax-bx, ay-by)

def find_atom_at(px,py):
    for m in molecules:
        for a in m.atoms:
            if distance_points(a.x,a.y,px,py) <= Atom.R+4:
                return a, m
    return None, None

def find_button_at(px,py):
    for rect, key in BUTTONS:
        if rect.collidepoint(px,py):
            return key
    return None

# ------------------ Хімічні правила ------------------
def can_bond(a,b):
    if a is b: return False
    if b in a.bonds: return False
    # перевірка валентності
    if a.free_valence() <= 0 or b.free_valence() <= 0:
        return False
    # заборонені пари
    if (a.symbol,b.symbol) in INVALID_PAIRS or (b.symbol,a.symbol) in INVALID_PAIRS:
        return False
    # дозволяємо зв'язок коли:
    # - обидва нейтральні (ковалентний)
    # - або мають протилежні формальні заряди (іонний)
    if (a.charge == 0 and b.charge == 0) or (a.charge * b.charge < 0):
        return True
    # інші комбінації забороняємо
    return False

def make_bond(a,b):
    if not can_bond(a,b): return False
    a.bonds.append(b); b.bonds.append(a)
    merge_molecules_containing(a,b)
    return True

def remove_bond(a,b):
    if b in a.bonds:
        a.bonds.remove(b)
    if a in b.bonds:
        b.bonds.remove(a)

def merge_molecules_containing(a,b):
    ma = None; mb = None
    for m in molecules:
        if a in m.atoms: ma = m
        if b in m.atoms: mb = m
    if ma and mb and ma is not mb:
        ma.atoms += mb.atoms
        molecules.remove(mb)

def split_disconnected(mol):
    atoms = mol.atoms[:]
    if not atoms: return
    comps = []
    visited = set()
    for a in atoms:
        if a in visited: continue
        stack = [a]; comp=[]
        while stack:
            cur = stack.pop()
            if cur in visited: continue
            visited.add(cur)
            comp.append(cur)
            for nb in cur.bonds:
                if nb in atoms and nb not in visited:
                    stack.append(nb)
        comps.append(comp)
    if len(comps) <= 1:
        return
    mol.atoms = comps[0]
    for comp in comps[1:]:
        newm = Molecule(comp)
        molecules.append(newm)

# ------------------ Physics update ------------------
def physics_step(dt):
    all_at = all_atoms()

    for i in range(len(all_at)):
        a = all_at[i]
        if a.fixed: continue
        fx = fy = 0.0
        # diffusion
        fx += (random.random()*2-1)*DIFFUSE
        fy += (random.random()*2-1)*DIFFUSE

        # charges interactions
        for j in range(len(all_at)):
            if i == j: continue
            b = all_at[j]
            dx = b.x - a.x; dy = b.y - a.y
            d2 = dx*dx + dy*dy
            if d2 < 0.001: continue
            d = math.sqrt(d2)
            nx = dx / d; ny = dy / d
            q = a.charge * b.charge
            if q < 0:
                strength = ATTRACTION_FACTOR * abs(q) / (d + 10)
                fx += nx * strength
                fy += ny * strength
            elif q > 0:
                strength = REPULSION_FACTOR * abs(q) / (d + 10)
                fx -= nx * strength
                fy -= ny * strength
            # short-range overlap prevention
            if d < Atom.R*2:
                overlap = (Atom.R*2 - d)
                fx -= nx * overlap * 0.6
                fy -= ny * overlap * 0.6

        # bonded springs
        for nb in a.bonds:
            dx = nb.x - a.x; dy = nb.y - a.y
            d = math.hypot(dx,dy)
            if d == 0: continue
            pref = BOND_DIST * 0.6
            k = 0.12
            fx += dx/d * k * (d - pref)
            fy += dy/d * k * (d - pref)

        a.vx += fx * dt
        a.vy += fy * dt
        # clamp
        speed = math.hypot(a.vx, a.vy)
        if speed > MAX_SPEED:
            factor = MAX_SPEED / speed
            a.vx *= factor; a.vy *= factor

    # apply velocities and boundaries
    for a in all_at:
        if a.fixed: continue
        a.x += a.vx
        a.y += a.vy
        left = 4; top = 4; right = CANVAS_RECT.w - 4; bottom = CANVAS_RECT.h - 4
        a.x = max(left, min(right, a.x))
        a.y = max(top, min(bottom, a.y))

    # bond formation / break
    for i in range(len(all_at)):
        for j in range(i+1, len(all_at)):
            a = all_at[i]; b = all_at[j]
            if b in a.bonds:
                if distance_points(a.x,a.y,b.x,b.y) > BOND_BREAK_DIST:
                    remove_bond(a,b)
            else:
                if can_bond(a,b) and distance_points(a.x,a.y,b.x,b.y) <= BOND_DIST:
                    make_bond(a,b)

    # split molecules if disconnected
    for m in molecules[:]:
        split_disconnected(m)

# ------------------ Stability update ------------------
def stability_step():
    now = time.time()
    for m in molecules:
        m.update_unstable_timer(now)
    for m in molecules[:]:
        if m.should_disassemble(time.time()):
            m.disassemble()
            split_disconnected(m)

# ------------------ Main loop ------------------
def draw_ui():
    pygame.draw.rect(SCREEN, (28,28,30), PANEL_RECT)
    title = BOLD.render("ELEMENTS / GROUPS", True, (220,220,220))
    SCREEN.blit(title, (PANEL_RECT.x + 10, 6))
    for rect, key in BUTTONS:
        pygame.draw.rect(SCREEN, (45,45,48), rect)
        txt = FONT.render(key, True, (230,230,230))
        SCREEN.blit(txt, (rect.x + 8, rect.y + (rect.h - txt.get_height())/2))
    ctrl_y = PANEL_RECT.y + H - 120
    info = [
        "Controls:",
        "Left click button - spawn item",
        "Left click atom - pick up / select (click another to bond)",
        "Right click atom - delete atom",
        "Space - pause / resume",
        "R - reset scene",
    ]
    for i, s in enumerate(info):
        SCREEN.blit(FONT.render(s, True, (200,200,200)), (PANEL_RECT.x+10, ctrl_y + i*18))
    if selected_atom:
        SCREEN.blit(FONT.render(f"Selected: {selected_atom.symbol} fv:{selected_atom.free_valence()}", True, (255,220,120)), (PANEL_RECT.x+10, 200))

def world_to_screen(x,y):
    return x, y

def screen_to_world(px,py):
    return px, py

def clear_scene():
    molecules.clear()

running = True
last_time = time.time()

while running:
    dt = CLOCK.tick(60) / 1000.0
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                paused = not paused
            elif event.key == pygame.K_r:
                clear_scene()
            elif event.key == pygame.K_ESCAPE:
                running = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            mx,my = event.pos
            if event.button == 1:  # left
                btn = find_button_at(mx,my)
                if btn:
                    spawn_item(btn)
                else:
                    if CANVAS_RECT.collidepoint(mx,my):
                        ax, ay = screen_to_world(mx, my)
                        atom, mol = find_atom_at(ax, ay)
                        if atom:
                            dragging = (atom, ax - atom.x, ay - atom.y, mol)
                            atom.fixed = True
                            mouse_down_pos = (mx,my)
                        else:
                            selected_atom = None
            elif event.button == 3:  # right: delete atom if any
                ax, ay = screen_to_world(mx, my)
                atom, mol = find_atom_at(ax, ay)
                if atom and mol:
                    for nb in list(atom.bonds):
                        remove_bond(atom, nb)
                    mol.atoms.remove(atom)
                    if not mol.atoms:
                        molecules.remove(mol)
                    else:
                        split_disconnected(mol)

        elif event.type == pygame.MOUSEBUTTONUP:
            mx,my = event.pos
            if event.button == 1 and dragging:
                atom, ox, oy, mol = dragging
                atom.fixed = False
                dx = mx - mouse_down_pos[0]; dy = my - mouse_down_pos[1]
                if abs(dx) < 6 and abs(dy) < 6:
                    if selected_atom is None:
                        selected_atom = atom
                    else:
                        if selected_atom is atom:
                            selected_atom = None
                        else:
                            make_bond(selected_atom, atom)
                            selected_atom = None
                dragging = None

    if dragging:
        atom, ox, oy, mol = dragging
        mx,my = pygame.mouse.get_pos()
        wx,wy = screen_to_world(mx, my)
        atom.x = wx - ox
        atom.y = wy - oy
        atom.vx = 0; atom.vy = 0

    if not paused:
        physics_step(dt)
        stability_step()

    SCREEN.fill((12,12,16))
    pygame.draw.rect(SCREEN, (18,18,22), CANVAS_RECT)

    for m in molecules:
        m.draw(SCREEN)

    draw_ui()

    status = f"Atoms: {len(all_atoms())}   Molecules: {len(molecules)}   {'PAUSED' if paused else ''}"
    SCREEN.blit(FONT.render(status, True, (200,200,200)), (8,8))

    pygame.display.flip()

pygame.quit()
