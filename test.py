# chem_sandbox_realistic_v2.py
# Реалістична симуляція атомів із валентністю та стабільністю
# Потрібно: pygame

import pygame, random, math, time
pygame.init()

W, H = 1200, 720
SCREEN = pygame.display.set_mode((W, H))
CLOCK = pygame.time.Clock()
FONT = pygame.font.SysFont(None, 18)
BOLD = pygame.font.SysFont(None, 22)

PANEL_W = 260
PANEL_RECT = pygame.Rect(W - PANEL_W, 0, PANEL_W, H)
CANVAS_RECT = pygame.Rect(0, 0, W - PANEL_W, H)

ELEMENTS = {
    "H":  {"valence": 1, "color": (220,220,255)},
    "O":  {"valence": 2, "color": (255,160,160)},
    "Na": {"valence": 1, "color": (160,200,255)},
    "Cl": {"valence": 1, "color": (160,255,170)},
    "Ca": {"valence": 2, "color": (210,190,140)},
}
ATOM_TYPES = list(ELEMENTS.keys())

DIFFUSE = 0.6
BOND_DIST = 70
BOND_BREAK_DIST = 180
MAX_SPEED = 4.0
UNSTABLE_LIFE = 3.0

# --- хімічні правила через словники складу ---
STABLE_COUNTS = [
    {"H":2}, {"O":2}, {"H":2,"O":1}, {"H":2,"O":2},
    {"Na":1,"Cl":1}, {"Ca":1,"Cl":2}, {"Ca":1,"O":1},
    {"Ca":1,"O":2,"H":2}, {"Na":1,"O":1,"H":1},
    {"Na":2,"O":1}, {"Na":2,"O":2}
]
UNSTABLE_COUNTS = [
    {"Na":1,"O":1}, {"H":1,"O":1,"Cl":1}, {"Ca":1,"Cl":1},
    {"H":1,"Cl":1,"O":3}, {"Na":1,"H":1}, {"Ca":1,"H":2}
]
IMPOSSIBLE_BONDS = {("Na","Na"), ("Ca","Ca"), ("Na","Ca")}

# ------------------ КЛАСИ ------------------
class Atom:
    R = 16
    def __init__(self, x, y, symbol):
        self.x=float(x); self.y=float(y)
        self.vx=self.vy=0.0
        self.symbol=symbol
        self.bonds=[]; self.fixed=False
        self.id=id(self)

    @property
    def valence(self): return ELEMENTS[self.symbol]["valence"]
    def free_valence(self): return max(0, self.valence - len(self.bonds))
    def bond_count_with(self, other): return self.bonds.count(other)

    def draw(self, surf):
        col=ELEMENTS[self.symbol]["color"]
        pygame.draw.circle(surf,(60,60,64),(int(self.x),int(self.y)),self.R+3)
        pygame.draw.circle(surf,col,(int(self.x),int(self.y)),self.R)
        txt=FONT.render(self.symbol,True,(10,10,10))
        surf.blit(txt,(self.x-txt.get_width()/2,self.y-txt.get_height()/2))
        fv=FONT.render(str(self.free_valence()),True,(140,140,140))
        surf.blit(fv,(self.x-6,self.y+self.R-14))

class Molecule:
    def __init__(self, atoms=None):
        self.atoms=atoms if atoms else []
        self.unstable_since=None

    def bonds_list(self):
        pairs=[];seen=set()
        for a in self.atoms:
            for b in a.bonds:
                if a is b: continue
                key=tuple(sorted((a.id,b.id)))
                if key in seen: continue
                seen.add(key); pairs.append((a,b))
        return pairs

    def center(self):
        if not self.atoms: return (0,0)
        return (sum(a.x for a in self.atoms)/len(self.atoms),
                sum(a.y for a in self.atoms)/len(self.atoms))

    def formula_counts(self):
        c={}
        for a in self.atoms:
            c[a.symbol]=c.get(a.symbol,0)+1
        return c

    def same_composition(self, comp):
        mine=self.formula_counts()
        return mine==comp

    def is_unstable(self):
        if len(self.atoms)<=1: return False
        mine=self.formula_counts()
        if any(mine==stable for stable in STABLE_COUNTS): return False
        if any(mine==unst for unst in UNSTABLE_COUNTS): return True
        for a in self.atoms:
            if len(a.bonds)>a.valence: return True
        return True

    def update_unstable_timer(self, now):
        if self.is_unstable():
            if self.unstable_since is None: self.unstable_since=now
        else:
            self.unstable_since=None

    def should_disassemble(self, now):
        return self.unstable_since and (now-self.unstable_since>=UNSTABLE_LIFE)

    def disassemble(self):
        cx,cy=self.center()
        for a in self.atoms:
            for b in list(a.bonds):
                while b in a.bonds: a.bonds.remove(b)
                while a in b.bonds: b.bonds.remove(a)
            dx,dy=a.x-cx,a.y-cy
            d=math.hypot(dx,dy)+1e-6
            nx,ny=dx/d,dy/d
            force=5+random.uniform(0,3)
            a.vx+=nx*force; a.vy+=ny*force
        self.unstable_since=None

    def draw(self, surf):
        drawn = set()
        for a, b in self.bonds_list():
            key = tuple(sorted((a.id, b.id)))
            if key in drawn:
                continue
            cnt = a.bond_count_with(b)
            dx, dy = b.x - a.x, b.y - a.y
            d = math.hypot(dx, dy)
            if d == 0:
                continue
            nx, ny = dy / d, -dx / d
            if cnt >= 2:
                off = 5
                pygame.draw.line(surf, (200, 200, 200),
                                 (a.x + nx * off, a.y + ny * off),
                                 (b.x + nx * off, b.y + ny * off), 3)
                pygame.draw.line(surf, (200, 200, 200),
                                 (a.x - nx * off, a.y - ny * off),
                                 (b.x - nx * off, b.y - ny * off), 3)
            else:
                pygame.draw.line(surf, (200, 200, 200), (a.x, a.y), (b.x, b.y), 6)
            drawn.add(key)

        for a in self.atoms:
            a.draw(surf)

        # --- Формула у хімічному вигляді ---
        cx, cy = self.center()
        counts = self.formula_counts()
        order = ["Ca", "Na", "O", "H", "Cl"]  # типовий порядок виводу
        parts = []

        # Реконструкція "Ca(OH)2" замість "CaO2H2"
        if counts == {"Ca": 1, "O": 2, "H": 2}:
            formula_str = "Ca(OH)2"
        elif counts == {"Na": 1, "O": 1, "H": 1}:
            formula_str = "NaOH"
        elif counts == {"Ca": 1, "O": 1, "H": 2}:
            formula_str = "Ca(OH)?"  # рідкісне, залишимо як debug
        else:
            for el in order:
                if el in counts:
                    n = counts[el]
                    parts.append(f"{el}{'' if n == 1 else n}")
            # решта елементів (якщо з’являться інші)
            for el, n in counts.items():
                if el not in order:
                    parts.append(f"{el}{'' if n == 1 else n}")
            formula_str = "".join(parts)

        # Текст формули
        txt = FONT.render(formula_str, True, (255, 255, 150))
        surf.blit(txt, (cx - txt.get_width() / 2, cy - 30))

        # Позначення нестабільності
        if self.is_unstable():
            u = FONT.render("НЕСТАБІЛЬНА", True, (255, 80, 80))
            surf.blit(u, (cx - u.get_width() / 2, cy - 48))

# ------------------ ГЛОБАЛЬНІ ------------------
molecules=[]

def all_atoms(): return [a for m in molecules for a in m.atoms]

def spawn_atom(symbol,x=None,y=None):
    if x is None: x=CANVAS_RECT.w/2+random.randint(-80,80)
    if y is None: y=CANVAS_RECT.h/2+random.randint(-80,80)
    atom=Atom(x,y,symbol)
    molecules.append(Molecule([atom]))
    return atom

# ------------------ ХІМІЯ ------------------
def can_bond(a,b):
    if a is b: return False
    if a.free_valence()<=0 or b.free_valence()<=0: return False
    if (a.symbol,b.symbol) in IMPOSSIBLE_BONDS or (b.symbol,a.symbol) in IMPOSSIBLE_BONDS:
        return False
    if a.bond_count_with(b)>=2: return False
    return True

def make_bond(a,b):
    if not can_bond(a,b): return False
    a.bonds.append(b); b.bonds.append(a)
    merge_molecules_containing(a,b)
    return True

def remove_bond(a,b):
    if b in a.bonds: a.bonds.remove(b)
    if a in b.bonds: b.bonds.remove(a)

def merge_molecules_containing(a,b):
    ma=mb=None
    for m in molecules:
        if a in m.atoms: ma=m
        if b in m.atoms: mb=m
    if ma and mb and ma is not mb:
        ma.atoms=list(set(ma.atoms+mb.atoms))
        molecules.remove(mb)

def split_disconnected(mol):
    atoms=mol.atoms[:]
    if not atoms: return
    comps=[];vis=set()
    for a in atoms:
        if a in vis: continue
        stack=[a];comp=[]
        while stack:
            cur=stack.pop()
            if cur in vis: continue
            vis.add(cur);comp.append(cur)
            for nb in cur.bonds:
                if nb in atoms and nb not in vis:
                    stack.append(nb)
        comps.append(comp)
    if len(comps)<=1: return
    mol.atoms=comps[0]
    for comp in comps[1:]: molecules.append(Molecule(comp))

# ------------------ ФІЗИКА ------------------
def physics_step(dt):
    all_at=all_atoms()
    for a in all_at:
        if a.fixed: continue
        fx=(random.random()*2-1)*DIFFUSE; fy=(random.random()*2-1)*DIFFUSE
        for b in all_at:
            if a is b: continue
            dx=b.x-a.x; dy=b.y-a.y; d2=dx*dx+dy*dy
            if d2<1e-6: continue
            d=math.sqrt(d2)
            if d<Atom.R*2:
                over=(Atom.R*2-d)
                nx,ny=dx/d,dy/d
                fx-=nx*over*0.8; fy-=ny*over*0.8
        for nb in a.bonds:
            dx=nb.x-a.x; dy=nb.y-a.y; d=math.hypot(dx,dy)
            if d==0: continue
            pref=BOND_DIST*0.6; k=0.14
            fx+=(dx/d)*k*(d-pref); fy+=(dy/d)*k*(d-pref)
        a.vx+=fx*dt; a.vy+=fy*dt
        s=math.hypot(a.vx,a.vy)
        if s>MAX_SPEED:
            f=MAX_SPEED/s; a.vx*=f; a.vy*=f
    for a in all_at:
        if a.fixed: continue
        a.x+=a.vx; a.y+=a.vy
        a.x=max(4,min(CANVAS_RECT.w-4,a.x))
        a.y=max(4,min(CANVAS_RECT.h-4,a.y))
    for i in range(len(all_at)):
        for j in range(i+1,len(all_at)):
            a,b=all_at[i],all_at[j]
            dist=math.hypot(a.x-b.x,a.y-b.y)
            if b in a.bonds and dist>BOND_BREAK_DIST:
                remove_bond(a,b)
            elif dist<=BOND_DIST and can_bond(a,b):
                make_bond(a,b)
    for m in molecules[:]: split_disconnected(m)

def stability_step():
    now=time.time()
    for m in molecules: m.update_unstable_timer(now)
    for m in molecules[:]:
        if m.should_disassemble(now):
            m.disassemble(); split_disconnected(m)

# ------------------ UI ------------------
def draw_ui(selected_atom,paused):
    pygame.draw.rect(SCREEN,(28,28,30),PANEL_RECT)
    title=BOLD.render("АТОМИ",True,(230,230,230))
    SCREEN.blit(title,(PANEL_RECT.x+10,6))
    for i,key in enumerate(ATOM_TYPES):
        rect=pygame.Rect(W-PANEL_W+12,20+i*44,PANEL_W-24,36)
        pygame.draw.rect(SCREEN,(45,45,48),rect)
        txt=FONT.render(key,True,(230,230,230))
        SCREEN.blit(txt,(rect.x+8,rect.y+8))
    info=["ЛКМ по кнопці - створити","ЛКМ по атому - взяти/зв’язати",
          "ПКМ - видалити","Пробіл - пауза","R - очистити"]
    for i,s in enumerate(info):
        SCREEN.blit(FONT.render(s,True,(200,200,200)),(PANEL_RECT.x+10,500+i*20))
    if selected_atom:
        SCREEN.blit(FONT.render(f"Обрано: {selected_atom.symbol} ({selected_atom.free_valence()})",
                                True,(255,220,120)),(10,30))
    status=f"Атомів: {len(all_atoms())}   Молекул: {len(molecules)}   {'ПАУЗА' if paused else ''}"
    SCREEN.blit(FONT.render(status,True,(200,200,200)),(10,10))

def find_atom_at(x,y):
    for m in molecules:
        for a in m.atoms:
            if math.hypot(a.x-x,a.y-y)<=Atom.R+4:
                return a,m
    return None,None

def find_button_at(px,py):
    for i,key in enumerate(ATOM_TYPES):
        rect=pygame.Rect(W-PANEL_W+12,20+i*44,PANEL_W-24,36)
        if rect.collidepoint(px,py): return key
    return None

# ------------------ ЦИКЛ ------------------
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
        elif e.type==pygame.MOUSEBUTTONDOWN:
            mx,my=e.pos
            if e.button==1:
                btn=find_button_at(mx,my)
                if btn: spawn_atom(btn)
                elif CANVAS_RECT.collidepoint(mx,my):
                    a,m=find_atom_at(mx,my)
                    if a:
                        dragging=(a,mx-a.x,my-a.y,m); a.fixed=True; mouse_down=(mx,my)
                    else: selected_atom=None
            elif e.button==3:
                a,m=find_atom_at(mx,my)
                if a and m:
                    for nb in list(a.bonds): remove_bond(a,nb)
                    if a in m.atoms: m.atoms.remove(a)
                    if not m.atoms: molecules.remove(m)
                    else: split_disconnected(m)
        elif e.type==pygame.MOUSEBUTTONUP:
            if e.button==1 and dragging:
                a,ox,oy,m=dragging; a.fixed=False
                dx,dy=e.pos[0]-mouse_down[0],e.pos[1]-mouse_down[1]
                if abs(dx)<6 and abs(dy)<6:
                    if selected_atom is None: selected_atom=a
                    else:
                        if selected_atom is a: selected_atom=None
                        else:
                            make_bond(selected_atom,a); selected_atom=None
                dragging=None
    if dragging:
        a,ox,oy,m=dragging; mx,my=pygame.mouse.get_pos()
        a.x=mx-ox; a.y=my-oy; a.vx=a.vy=0
    if not paused:
        physics_step(dt); stability_step()
    SCREEN.fill((12,12,16))
    pygame.draw.rect(SCREEN,(18,18,22),CANVAS_RECT)
    for m in molecules: m.draw(SCREEN)
    draw_ui(selected_atom,paused)
    pygame.display.flip()
pygame.quit()
