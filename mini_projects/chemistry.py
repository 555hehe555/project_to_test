import pygame, random, math, time
pygame.init()

# ------------------ ЕКРАН І ОСНОВНІ НАЛАШТУВАННЯ ------------------
W, H = 1200, 720
SCREEN = pygame.display.set_mode((W, H))
CLOCK = pygame.time.Clock()
FONT = pygame.font.SysFont(None, 18)
BOLD = pygame.font.SysFont(None, 22)

PANEL_W = 260
PANEL_RECT = pygame.Rect(W - PANEL_W, 0, PANEL_W, H)
CANVAS_RECT = pygame.Rect(0, 0, W - PANEL_W, H)

# ------------------ ЕЛЕМЕНТИ ТА ЇХ ВЛАСТИВОСТІ ------------------
ELEMENTS = {
    "H":  {"valence": 1, "color": (220,220,255)},   # Гідроген
    "O":  {"valence": 2, "color": (255,160,160)},   # Оксиген
    "Na": {"valence": 1, "color": (160,200,255)},   # Натрій
    "Cl": {"valence": 1, "color": (160,255,170)},   # Хлор
    "Ca": {"valence": 2, "color": (210,190,140)},   # Кальцій
}
ATOM_TYPES = list(ELEMENTS.keys())

# ------------------ ПАРАМЕТРИ ФІЗИКИ ------------------
PHYSICS = {
    "diffuse_strength": 1.0,      # сила хаотичного (теплового) руху
    "bond_distance": 120,         # максимальна відстань для створення зв’язку
    "bond_break_distance": 200,   # відстань, після якої зв’язок розривається
    "bond_spring_k": 0.14,        # жорсткість зв’язку
    "bond_preferred_scale": 0.6,  # природна довжина зв’язку
    "repulsion_strength": 0.8,    # сила відштовхування між атомами
    "max_speed": 4.0,             # обмеження швидкості
    "unstable_lifetime": 5.0,     # час існування нестабільної молекули
    # індивідуальні радіуси атомів
    "radii": {
        "H": 12,
        "O": 16,
        "Na": 18,
        "Cl": 17,
        "Ca": 20,
        "standard": 16,
    }
}

# ------------------ ХІМІЧНІ ПРАВИЛА ------------------
STABLE_COUNTS = [
    {"H":2}, {"O":2}, {"O":3}, {"Cl":2},
    {"H":2,"O":1}, {"H":2,"O":2}, {"H":1,"Cl":1},
    {"Ca":1,"O":1}, {"Na":2,"O":1}, {"Na":2,"O":2},
    {"Na":1,"Cl":1}, {"Ca":1,"Cl":2}, {"O":1,"Cl":2},
    {"Ca":1,"O":2,"H":2}, {"Na":1,"O":1,"H":1},
    {"Ca":1,"H":2}, {"Na":1,"H":1}
]

UNSTABLE_COUNTS = [
    {"Na":1,"Ca":1},
    {"Na":1,"O":1}, {"Ca":1,"Cl":1},
    {"Na":1,"H":1}, {"Ca":1,"H":2},
    {"H":1,"O":3,"Cl":1}, {"H":1,"O":1,"Cl":1},
    {"Na":1,"Ca":1,"Cl":1}, {"Na":1,"Ca":1,"O":1},
]

IMPOSSIBLE_COUNTS = [
    {"Na":1,"Ca":1},
    {"Na":2}, {"Ca":2},
    {"Na":1,"Cl":3}, {"Na":2,"Cl":1},
    {"Ca":1,"Cl":3}, {"Ca":2,"Cl":1},
    {"Ca":1,"O":3}, {"Na":1,"O":3}, {"H":1,"O":3},
    {"Ca":1,"H":3}, {"Na":1,"H":3},
]

IMPOSSIBLE_BONDS = {("Na","Na"), ("Ca","Ca"), ("Na","Ca")}

# ------------------ КЛАС АТОМ ------------------
class Atom:
    """Описує окремий атом"""
    def __init__(self, x, y, symbol):
        self.x=float(x); self.y=float(y)
        self.vx=self.vy=0.0
        self.symbol=symbol
        self.bonds=[]; self.fixed=False
        self.id=id(self)
        self.R = PHYSICS["radii"].get(symbol, PHYSICS["radii"]["standard"])

    @property
    def valence(self): return ELEMENTS[self.symbol]["valence"]
    def free_valence(self): return max(0, self.valence - len(self.bonds))
    def bond_count_with(self, other): return self.bonds.count(other)

    def draw(self, surf):
        """Малює атом і відображає його валентність"""
        col=ELEMENTS[self.symbol]["color"]
        pygame.draw.circle(surf,(60,60,64),(int(self.x),int(self.y)),self.R+3)
        pygame.draw.circle(surf,col,(int(self.x),int(self.y)),self.R)
        txt=FONT.render(self.symbol,True,(10,10,10))
        surf.blit(txt,(self.x-txt.get_width()/2,self.y-txt.get_height()/2))
        fv=FONT.render(str(self.free_valence()),True,(140,140,140))
        surf.blit(fv,(self.x-6,self.y+self.R-14))

# ------------------ КЛАС МОЛЕКУЛА ------------------
class Molecule:
    """Група атомів, зв’язаних у молекулу"""
    def __init__(self, atoms=None):
        self.atoms=atoms if atoms else []
        self.unstable_since=None

    def bonds_list(self):
        """Повертає список унікальних зв’язків"""
        pairs=[];seen=set()
        for a in self.atoms:
            for b in a.bonds:
                key=tuple(sorted((a.id,b.id)))
                if key not in seen:
                    seen.add(key); pairs.append((a,b))
        return pairs

    def center(self):
        """Центр молекули для позиціонування підписів"""
        if not self.atoms: return (0,0)
        return (sum(a.x for a in self.atoms)/len(self.atoms),
                sum(a.y for a in self.atoms)/len(self.atoms))

    def formula_counts(self):
        """Підрахунок кількості кожного елемента"""
        c={}
        for a in self.atoms: c[a.symbol]=c.get(a.symbol,0)+1
        return c

    def is_unstable(self):
        """Перевіряє стабільність молекули"""
        if len(self.atoms)<=1: return False
        mine=self.formula_counts()
        if any(mine==stable for stable in STABLE_COUNTS): return False
        if any(mine==unst for unst in UNSTABLE_COUNTS): return True
        for bad in IMPOSSIBLE_COUNTS:
            if all(mine.get(k,0)>=v for k,v in bad.items()):
                return True
        for a in self.atoms:
            if len(a.bonds)>a.valence: return True
        return True

    def update_unstable_timer(self, now):
        """Фіксує час появи нестабільності"""
        if self.is_unstable():
            if self.unstable_since is None: self.unstable_since=now
        else:
            self.unstable_since=None

    def should_disassemble(self, now):
        """Перевіряє, чи настав час розпаду"""
        return self.unstable_since and (now-self.unstable_since>=PHYSICS["unstable_lifetime"])

    def disassemble(self):
        """Розпад молекули — видалення всіх зв’язків і надання імпульсу"""
        cx,cy=self.center()
        for a in self.atoms:
            for b in list(a.bonds):
                if b in a.bonds: a.bonds.remove(b)
                if a in b.bonds: b.bonds.remove(a)
            dx,dy=a.x-cx,a.y-cy; d=math.hypot(dx,dy)+1e-6
            nx,ny=dx/d,dy/d; force=5+random.uniform(0,3)
            a.vx+=nx*force; a.vy+=ny*force
        self.unstable_since=None

    def draw(self, surf):
        """Малює молекулу, зв’язки, атоми та підписи"""
        for a,b in self.bonds_list():
            dx,dy=b.x-a.x,b.y-a.y; d=math.hypot(dx,dy)
            if d==0: continue
            nx,ny=dy/d,-dx/d
            if a.bond_count_with(b)>=2:
                off=5
                pygame.draw.line(surf,(200,200,200),(a.x+nx*off,a.y+ny*off),(b.x+nx*off,b.y+ny*off),3)
                pygame.draw.line(surf,(200,200,200),(a.x-nx*off,a.y-ny*off),(b.x-nx*off,b.y-ny*off),3)
            else:
                pygame.draw.line(surf,(200,200,200),(a.x,a.y),(b.x,b.y),6)
        for a in self.atoms: a.draw(surf)

        # малювання написів — формула + позначка нестабільності
        cx,cy=self.center()
        counts=self.formula_counts()
        formula="".join(f"{el}{'' if n==1 else n}" for el,n in counts.items())
        txt=FONT.render(formula,True,(255,255,150))
        surf.blit(txt,(cx-txt.get_width()/2,cy-30))

        if self.is_unstable():
            warn=FONT.render("НЕСТАБІЛЬНА",True,(255,80,80))
            surf.blit(warn,(cx-warn.get_width()/2,cy-48))

# ------------------ ДОПОМІЖНІ ФУНКЦІЇ ------------------
molecules=[]
def all_atoms(): return [a for m in molecules for a in m.atoms]

def spawn_atom(symbol,x=None,y=None):
    """Створює новий атом на полі"""
    if x is None: x=CANVAS_RECT.w/2+random.randint(-80,80)
    if y is None: y=CANVAS_RECT.h/2+random.randint(-80,80)
    atom=Atom(x,y,symbol)
    molecules.append(Molecule([atom]))
    return atom

# ------------------ ХІМІЯ ------------------
def can_bond(a,b):
    """Перевірка, чи можуть два атоми зв’язатися"""
    if a is b: return False
    if a.free_valence()<=0 or b.free_valence()<=0: return False
    if (a.symbol,b.symbol) in IMPOSSIBLE_BONDS or (b.symbol,a.symbol) in IMPOSSIBLE_BONDS: return False
    if a.bond_count_with(b)>=2: return False
    return True

def make_bond(a,b):
    """Створює зв’язок між двома атомами"""
    if not can_bond(a,b): return False
    a.bonds.append(b); b.bonds.append(a)
    merge_molecules_containing(a,b)
    return True

def remove_bond(a,b):
    """Видаляє зв’язок між атомами"""
    if b in a.bonds: a.bonds.remove(b)
    if a in b.bonds: b.bonds.remove(a)

def merge_molecules_containing(a,b):
    """Об’єднує дві молекули, якщо атоми з них зв’язалися"""
    ma=mb=None
    for m in molecules:
        if a in m.atoms: ma=m
        if b in m.atoms: mb=m
    if ma and mb and ma is not mb:
        ma.atoms=list(set(ma.atoms+mb.atoms))
        molecules.remove(mb)

def split_disconnected(mol):
    """Розділяє молекулу, якщо частини втратили зв’язок"""
    atoms=mol.atoms[:]
    if not atoms: return
    comps=[];vis=set()
    for a in atoms:
        if a in vis: continue
        stack=[a];comp=[]
        while stack:
            cur=stack.pop()
            if cur in vis: continue
            vis.add(cur); comp.append(cur)
            for nb in cur.bonds:
                if nb in atoms and nb not in vis: stack.append(nb)
        comps.append(comp)
    if len(comps)<=1: return
    mol.atoms=comps[0]
    for comp in comps[1:]: molecules.append(Molecule(comp))

# ------------------ ФІЗИКА ------------------
def physics_step(dt):
    all_at = all_atoms()
    for a in all_at:
        if a.fixed:
            continue

        # --- дифузія ---
        fx = (random.random() * 2 - 1) * PHYSICS["diffuse_strength"]
        fy = (random.random() * 2 - 1) * PHYSICS["diffuse_strength"]

        # --- взаємне відштовхування ---
        for b in all_at:
            if a is b:
                continue
            dx = b.x - a.x
            dy = b.y - a.y
            d2 = dx * dx + dy * dy
            if d2 < 1e-6:
                continue
            d = math.sqrt(d2)

            ra = PHYSICS["radii"].get(a.symbol, PHYSICS["radii"]["standard"])
            rb = PHYSICS["radii"].get(b.symbol, PHYSICS["radii"]["standard"])
            min_dist = ra + rb

            if d < min_dist:
                over = (min_dist - d)
                nx, ny = dx / d, dy / d
                fx -= nx * over * PHYSICS["repulsion_strength"]
                fy -= ny * over * PHYSICS["repulsion_strength"]

        # --- пружні зв’язки ---
        for nb in a.bonds:
            dx = nb.x - a.x
            dy = nb.y - a.y
            d = math.hypot(dx, dy)
            if d == 0:
                continue
            pref = PHYSICS["bond_distance"] * PHYSICS["bond_preferred_scale"]
            k = PHYSICS["bond_spring_k"]
            fx += (dx / d) * k * (d - pref)
            fy += (dy / d) * k * (d - pref)

        # --- оновлення швидкості ---
        a.vx += fx * dt
        a.vy += fy * dt

        # --- обмеження швидкості ---
        s = math.hypot(a.vx, a.vy)
        if s > PHYSICS["max_speed"]:
            f = PHYSICS["max_speed"] / s
            a.vx *= f
            a.vy *= f

    # --- оновлення позицій ---
    for a in all_at:
        if a.fixed:
            continue
        a.x += a.vx
        a.y += a.vy
        a.x = max(4, min(CANVAS_RECT.w - 4, a.x))
        a.y = max(4, min(CANVAS_RECT.h - 4, a.y))

    # --- перевірка зв’язків ---
    for i in range(len(all_at)):
        for j in range(i + 1, len(all_at)):
            a, b = all_at[i], all_at[j]
            dist = math.hypot(a.x - b.x, a.y - b.y)
            if b in a.bonds and dist > PHYSICS["bond_break_distance"]:
                remove_bond(a, b)
            elif dist <= PHYSICS["bond_distance"] and can_bond(a, b):
                make_bond(a, b)

    # --- перевірка розпаду молекул ---
    for m in molecules[:]:
        split_disconnected(m)

def stability_step():
    """Оновлює стабільність молекул та виконує їх розпад"""
    now=time.time()
    for m in molecules: m.update_unstable_timer(now)
    for m in molecules[:]:
        if m.should_disassemble(now):
            m.disassemble(); split_disconnected(m)

# ------------------ ІНТЕРФЕЙС ------------------
def draw_ui(selected_atom,paused):
    """Малює праву панель з кнопками та інформацією"""
    pygame.draw.rect(SCREEN,(28,28,30),PANEL_RECT)
    SCREEN.blit(BOLD.render("АТОМИ",True,(230,230,230)),(PANEL_RECT.x+10,6))
    # кнопки створення атомів
    for i,key in enumerate(ATOM_TYPES):
        rect=pygame.Rect(W-PANEL_W+12,20+i*44,PANEL_W-24,36)
        pygame.draw.rect(SCREEN,(45,45,48),rect)
        SCREEN.blit(FONT.render(key,True,(230,230,230)),(rect.x+8,rect.y+8))
    # підказки управління
    info=["ЛКМ - створити/зв’язати","ПКМ - видалити","Пробіл - пауза","R - очистити"]
    for i,s in enumerate(info):
        SCREEN.blit(FONT.render(s,True,(200,200,200)),(PANEL_RECT.x+10,500+i*20))
    # інформація про вибір
    if selected_atom:
        SCREEN.blit(FONT.render(f"Обрано: {selected_atom.symbol} ({selected_atom.free_valence()})",
                                True,(255,220,120)),(10,30))
    # статусна стрічка
    status=f"Атомів: {len(all_atoms())}   Молекул: {len(molecules)}   {'ПАУЗА' if paused else ''}"
    SCREEN.blit(FONT.render(status,True,(200,200,200)),(10,10))

def find_atom_at(px,py):
    """Пошук атома під курсором"""
    for m in molecules:
        for a in m.atoms:
            if math.hypot(a.x-px,a.y-py)<=a.R+4: return a,m
    return None,None

def find_button_at(px,py):
    """Перевірка натискання на кнопку елемента"""
    for i,key in enumerate(ATOM_TYPES):
        rect=pygame.Rect(W-PANEL_W+12,20+i*44,PANEL_W-24,36)
        if rect.collidepoint(px,py): return key
    return None

# ------------------ ГОЛОВНИЙ ЦИКЛ ------------------
paused=False; dragging=None; selected_atom=None
mouse_down=(0,0); running=True

while running:
    dt=CLOCK.tick(60)/1000.0
    for e in pygame.event.get():
        if e.type==pygame.QUIT: running=False
        elif e.type==pygame.KEYDOWN:
            if e.key==pygame.K_SPACE: paused=not paused
            elif e.key==pygame.K_r: molecules.clear()
            elif e.key==pygame.K_ESCAPE: running=False

        # керування мишею
        elif e.type==pygame.MOUSEBUTTONDOWN:
            mx,my=e.pos
            if e.button==1:  # ліва кнопка
                btn=find_button_at(mx,my)
                if btn: spawn_atom(btn)
                elif CANVAS_RECT.collidepoint(mx,my):
                    a,m=find_atom_at(mx,my)
                    if a:
                        dragging=(a,mx-a.x,my-a.y,m); a.fixed=True; mouse_down=(mx,my)
                    else: selected_atom=None
            elif e.button==3:  # права кнопка
                a,m=find_atom_at(mx,my)
                if a and m:
                    for nb in list(a.bonds): remove_bond(a,nb)
                    if a in m.atoms: m.atoms.remove(a)
                    if not m.atoms: molecules.remove(m)
                    else: split_disconnected(m)

        elif e.type==pygame.MOUSEBUTTONUP and e.button==1 and dragging:
            # обробка "клацу" для створення зв’язку
            a,ox,oy,m=dragging; a.fixed=False
            dx,dy=e.pos[0]-mouse_down[0],e.pos[1]-mouse_down[1]
            if abs(dx)<6 and abs(dy)<6:
                if selected_atom is None: selected_atom=a
                else:
                    if selected_atom is a: selected_atom=None
                    else: make_bond(selected_atom,a); selected_atom=None
            dragging=None

    # оновлення положення перетягуваного атома
    if dragging:
        a,ox,oy,m=dragging; mx,my=pygame.mouse.get_pos()
        a.x=mx-ox; a.y=my-oy; a.vx=a.vy=0

    # крок симуляції
    if not paused:
        physics_step(dt)
        stability_step()

    # рендеринг
    SCREEN.fill((12,12,16))
    pygame.draw.rect(SCREEN,(18,18,22),CANVAS_RECT)
    for m in molecules: m.draw(SCREEN)
    draw_ui(selected_atom,paused)
    pygame.display.flip()

pygame.quit()
