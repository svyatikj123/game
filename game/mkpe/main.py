import pygame, sys, math, random, os

pygame.init()
pygame.display.set_caption("MORTAL KOMBAT - Pygame Edition")

WIDTH, HEIGHT = 1024, 600
GROUND_Y = 500
GRAVITY = 0.75
FPS = 60
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

font_title = pygame.font.SysFont("impact", 72)
font_big   = pygame.font.SysFont("impact", 48)
font_med   = pygame.font.SysFont("impact", 30)
font_small = pygame.font.SysFont("consolas", 18)

SPRITE_SCALE = 2.2

# --- ТОЧНЫЕ КООРДИНАТЫ КАДРОВ НА СПРАЙТ-ЛИСТАХ (x, y, w, h) ---
SPRITE_RECTS = {
    'idle':    [(0, 0, 48, 112), (48, 0, 48, 112)],
    'walk':    [(420, 0, 48, 112), (468, 0, 48, 112), (516, 0, 48, 112), (564, 0, 48, 112)],
    'punch':   [(0, 160, 48, 112), (48, 160, 48, 112), (96, 160, 48, 112)],
    'kick':    [(0, 310, 48, 112), (48, 310, 48, 112), (96, 310, 48, 112), (144, 310, 48, 112)],
    'block':   [(0, 1010, 48, 112), (48, 1010, 48, 112)],
    'hurt':    [(0, 610, 48, 112), (48, 610, 48, 112)],
    'ko':      [(180, 760, 100, 112)],
    'special': [(0, 1130, 48, 112), (48, 1130, 48, 112), (96, 1130, 48, 112)],
    'jump':    [(0, 450, 48, 112), (48, 450, 48, 112)],
    'win':     [(0, 1500, 48, 112), (48, 1500, 48, 112)],
}

CHARACTERS = {
    "SCORPION": dict(color=(230, 190, 60),  accent=(255, 240, 150),
                     speed=3.4, special="SPEAR",     proj_color=(250, 210, 70),  proj_speed=12),
    "SUB-ZERO": dict(color=(60, 120, 220),  accent=(190, 230, 255),
                     speed=3.1, special="ICE BLAST", proj_color=(150, 220, 255), proj_speed=10),
    "RAIDEN":   dict(color=(235, 235, 250), accent=(120, 180, 255),
                     speed=3.6, special="LIGHTNING", proj_color=(160, 210, 255), proj_speed=15),
    "LIU KANG": dict(color=(200, 45, 45),   accent=(255, 200, 80),
                     speed=3.3, special="FIREBALL",  proj_color=(255, 140, 40),  proj_speed=9),
}
NAMES = list(CHARACTERS.keys())

ATTACKS_BASE = {
    'punch':   dict(startup=4,  active=4, recover=9,  dmg=6,  reach=58, h=34, y_off=118, kb=3, hitstun=14),
    'kick':    dict(startup=7,  active=5, recover=15, dmg=10, reach=74, h=46, y_off=95,  kb=6, hitstun=20),
    'special': dict(startup=12, active=1, recover=24, dmg=0,  reach=0,  h=0,  y_off=110, kb=0, hitstun=0),
}

def lerp(a, b, t): return a + (b - a) * t

def draw_limb(surf, color, p1, p2, w):
    p1 = (int(p1[0]), int(p1[1])); p2 = (int(p2[0]), int(p2[1]))
    pygame.draw.line(surf, color, p1, p2, w)
    pygame.draw.circle(surf, color, p1, w // 2)
    pygame.draw.circle(surf, color, p2, w // 2)

# --- Векторные позы (запасной вариант) ---
def get_pose(f):
    s, t = f.state, f.state_timer
    p = {'hip': (0.0, -75.0), 'shoulder': (0.0, -125.0), 'head': (0.0, -146.0),
         'elbow_f': (13.0, -108.0), 'hand_f': (22.0, -94.0), 'elbow_b': (2.0, -106.0), 'hand_b': (10.0, -88.0),
         'knee_f': (13.0, -40.0), 'foot_f': (18.0, 0.0), 'knee_b': (-12.0, -40.0), 'foot_b': (-20.0, 0.0)}
    if s == 'idle':
        b = math.sin(f.anim * 0.10) * 2.0
        for k in ('hip', 'shoulder', 'head', 'elbow_f', 'hand_f', 'elbow_b', 'hand_b'):
            x0, y0 = p[k]; p[k] = (x0, y0 + b * 0.8)
    elif s == 'walk':
        sw = math.sin(f.anim * 0.28)
        p['knee_f'] = (13 + sw * 11, -40); p['foot_f'] = (18 + sw * 20, 0)
        p['knee_b'] = (-12 - sw * 11, -40); p['foot_b'] = (-20 - sw * 20, 0)
        p['hand_f'] = (22 - sw * 7, -94); p['hand_b'] = (10 + sw * 7, -88)
        b = abs(sw) * 2; p['shoulder'] = (0, -125 - b); p['head'] = (0, -146 - b)
    elif s == 'jump':
        p['knee_f'] = (22, -58); p['foot_f'] = (14, -22); p['knee_b'] = (-4, -52); p['foot_b'] = (-16, -28)
        p['elbow_f'] = (20, -116); p['hand_f'] = (30, -128); p['elbow_b'] = (-6, -112); p['hand_b'] = (-16, -124)
    elif s == 'block':
        p['elbow_f'] = (12, -116); p['hand_f'] = (4, -138); p['elbow_b'] = (2, -110); p['hand_b'] = (-4, -132)
        p['knee_f'] = (16, -40); p['foot_f'] = (22, 0); p['knee_b'] = (-14, -40); p['foot_b'] = (-26, 0)
    elif s == 'punch':
        a = f.attacks['punch']; t = f.state_timer
        if t < a['startup']: k = t / a['startup']; p['elbow_f'] = (lerp(13, 2, k), lerp(-108, -112, k)); p['hand_f'] = (lerp(22, -6, k), lerp(-94, -106, k))
        elif t < a['startup'] + a['active']: p['elbow_f'] = (28, -118); p['hand_f'] = (56, -120); p['elbow_b'] = (0, -108); p['hand_b'] = (-8, -96); p['shoulder'] = (4, -125); p['head'] = (6, -146)
        else: k = (t - a['startup'] - a['active']) / a['recover']; p['elbow_f'] = (lerp(28, 13, k), lerp(-118, -108, k)); p['hand_f'] = (lerp(56, 22, k), lerp(-120, -94, k))
    elif s == 'kick':
        a = f.attacks['kick']; t = f.state_timer
        if t < a['startup']: k = t / a['startup']; p['knee_f'] = (lerp(13, 26, k), lerp(-40, -62, k)); p['foot_f'] = (lerp(18, 40, k), lerp(0, -40, k))
        elif t < a['startup'] + a['active']: p['knee_f'] = (28, -64); p['foot_f'] = (66, -52); p['hip'] = (-6, -78); p['shoulder'] = (-10, -125); p['head'] = (-12, -146)
        else: k = (t - a['startup'] - a['active']) / a['recover']; p['knee_f'] = (lerp(28, 13, k), lerp(-64, -40, k)); p['foot_f'] = (lerp(66, 18, k), lerp(-52, 0, k))
    elif s == 'special':
        a = f.attacks['special']; k = min(1.0, f.state_timer / a['startup'])
        p['elbow_f'] = (lerp(13, 24, k), lerp(-108, -112, k)); p['hand_f'] = (lerp(22, 46, k), lerp(-94, -108, k))
        p['elbow_b'] = (lerp(2, 16, k), lerp(-106, -110, k)); p['hand_b'] = (lerp(10, 36, k), lerp(-88, -104, k))
    elif s == 'hurt':
        p['shoulder'] = (-8, -125); p['head'] = (-16, -144); p['elbow_f'] = (2, -112); p['hand_f'] = (4, -118); p['elbow_b'] = (-10, -112); p['hand_b'] = (-6, -120)
    elif s == 'ko':
        p = {'hip': (0, -22), 'shoulder': (-32, -24), 'head': (-48, -26), 'elbow_f': (-20, -16), 'hand_f': (-8, -8),
             'elbow_b': (-24, -20), 'hand_b': (-12, -12), 'knee_f': (22, -18), 'foot_f': (42, -8), 'knee_b': (20, -14), 'foot_b': (38, -2)}
    return p

def draw_vector_fighter(surf, f):
    p = get_pose(f)
    cfg = f.cfg; main = cfg['color']; accent = cfg['accent']; skin = (232, 198, 160); d = f.facing
    def P(pt): return (f.x + pt[0] * d, f.y + pt[1])
    if f.state != 'ko':
        sw = int(30 * max(0.45, 1 - (GROUND_Y - f.y) / 320))
        sh = pygame.Surface((sw * 2, 14), pygame.SRCALPHA); pygame.draw.ellipse(sh, (0, 0, 0, 110), sh.get_rect()); surf.blit(sh, (f.x - sw, GROUND_Y - 7))
    draw_limb(surf, tuple(max(0, c - 60) for c in main), P(p['hip']), P(p['knee_b']), 12); draw_limb(surf, tuple(max(0, c - 60) for c in main), P(p['knee_b']), P(p['foot_b']), 10)
    draw_limb(surf, tuple(max(0, c - 60) for c in main), P(p['shoulder']), P(p['elbow_b']), 9); draw_limb(surf, tuple(max(0, c - 60) for c in main), P(p['elbow_b']), P(p['hand_b']), 7)
    pygame.draw.line(surf, main, P(p['hip']), P(p['shoulder']), 26); pygame.draw.circle(surf, main, (int(P(p['hip'])[0]), int(P(p['hip'])[1])), 13)
    hx, hy = int(P(p['head'])[0]), int(P(p['head'])[1]); pygame.draw.circle(surf, skin, (hx, hy), 15); pygame.draw.rect(surf, main, (hx - 15, hy - 5, 30, 9))
    draw_limb(surf, main, P(p['hip']), P(p['knee_f']), 12); draw_limb(surf, main, P(p['knee_f']), P(p['foot_f']), 10)
    draw_limb(surf, main, P(p['shoulder']), P(p['elbow_f']), 9); draw_limb(surf, main, P(p['elbow_f']), P(p['hand_f']), 7)
    pygame.draw.circle(surf, accent, (int(P(p['hand_f'])[0]), int(P(p['hand_f'])[1])), 6)

def draw_fighter(surf, f):
    if getattr(f, 'sheet', None):
        try:
            rects = SPRITE_RECTS.get(f.state, SPRITE_RECTS['idle'])
            if f.state in ('punch', 'kick', 'special'):
                a = f.attacks[f.state]
                total = a['startup'] + a['active'] + a['recover'] if f.state != 'special' else a['startup'] + a['recover']
                progress = min(1.0, f.state_timer / max(1, total))
                frame_idx = min(len(rects) - 1, int(progress * len(rects)))
            else:
                frame_idx = (f.anim // 6) % len(rects)
            
            r = rects[frame_idx]
            
            # --- МАСШТАБИРОВАНИЕ И ЗАЩИТА ОТ ВЫЛЕТОВ ---
            scaled_w = int(r[2] * SPRITE_SCALE)
            scaled_h = int(r[3] * SPRITE_SCALE)
            scaled_x = int(r[0] * SPRITE_SCALE)
            scaled_y = int(r[1] * SPRITE_SCALE)
            
            # Если координаты вылезают за границы листа, обрезаем их
            if scaled_x >= f.sheet.get_width() or scaled_y >= f.sheet.get_height():
                raise ValueError("Out of bounds")
                
            scaled_w = min(scaled_w, f.sheet.get_width() - scaled_x)
            scaled_h = min(scaled_h, f.sheet.get_height() - scaled_y)
            
            scaled_r = pygame.Rect(scaled_x, scaled_y, scaled_w, scaled_h)
            
            image = f.sheet.subsurface(scaled_r).copy()
            if f.facing == -1:
                image = pygame.transform.flip(image, True, False)
            
            draw_x = f.x - image.get_width() // 2
            draw_y = f.y - image.get_height() + (12 * SPRITE_SCALE)
            
            if f.state != 'ko':
                sw = int(35 * max(0.45, 1 - (GROUND_Y - f.y) / 320))
                sh = pygame.Surface((sw * 2, 16), pygame.SRCALPHA)
                pygame.draw.ellipse(sh, (0, 0, 0, 120), sh.get_rect())
                surf.blit(sh, (f.x - sw, GROUND_Y - 8))
                
            surf.blit(image, (draw_x, draw_y))
            
            if f.frozen > 0:
                ov = pygame.Surface((image.get_width(), image.get_height()), pygame.SRCALPHA)
                ov.fill((150, 220, 255, 90))
                pygame.draw.rect(ov, (200, 240, 255, 150), ov.get_rect(), 2)
                surf.blit(ov, (draw_x, draw_y))
            
            return
        except Exception:
            pass
    draw_vector_fighter(surf, f)

class Fighter:
    def __init__(self, name, x, facing, is_cpu=False):
        self.name = name
        self.cfg = CHARACTERS[name]
        self.x = float(x); self.y = float(GROUND_Y)
        self.vx = 0.0; self.vy = 0.0
        self.facing = facing; self.hp = 100
        self.state = 'idle'; self.state_timer = 0; self.anim = 0
        self.on_ground = True; self.frozen = 0; self.hurt_time = 0
        self.has_hit = False; self.is_cpu = is_cpu
        self.attacks = {k: dict(v) for k, v in ATTACKS_BASE.items()}
        
        self.sheet = None
        
        # --- УЛУЧШЕННЫЙ ПОИСК ФАЙЛОВ ---
        base_filename = name.replace(' ', '').replace('-', '').lower()
        sprite_dir = "sprites"
        
        if not os.path.exists(sprite_dir):
            os.makedirs(sprite_dir)
            print(f"[INFO] Создана папка '{sprite_dir}'. Положите туда картинки!")
            
        # Пробуем разные расширения
        possible_exts = [".png", ".jpg", ".jpeg", ".webp"]
        found_path = None
        
        for ext in possible_exts:
            p = os.path.join(sprite_dir, f"{base_filename}{ext}")
            if os.path.exists(p):
                found_path = p
                break
                
        if found_path:
            try:
                img = pygame.image.load(found_path).convert_alpha()
                self.sheet = pygame.transform.scale(img, (int(img.get_width() * SPRITE_SCALE), int(img.get_height() * SPRITE_SCALE)))
                print(f"[OK] Спрайты загружены: {found_path}")
            except Exception as e:
                print(f"[ERR] Ошибка загрузки {found_path}: {e}")
        else:
            # Если не нашли, выводим список того, что вообще есть в папке
            print(f"[WARN] Не найден файл для {name} (искали {base_filename}.png/.jpg).")
            if os.path.exists(sprite_dir):
                files_in_dir = os.listdir(sprite_dir)
                if files_in_dir:
                    print(f"       В папке '{sprite_dir}' есть файлы: {files_in_dir}")
                    print(f"       Убедитесь, что название совпадает с '{base_filename}'.")
                else:
                    print(f"       Папка '{sprite_dir}' существует, но она пуста!")
            print("       Используется векторная графика.")

    def handle_input(self, inp, opp):
        if self.frozen > 0 or self.state in ('punch', 'kick', 'special', 'hurt', 'ko', 'win'): return
        self.facing = 1 if opp.x > self.x else -1
        if inp['down'] and self.on_ground: self.state = 'block'; self.state_timer = 0; return
        if inp['punch']: self.state = 'punch'; self.state_timer = 0; self.has_hit = False; return
        if inp['kick']: self.state = 'kick'; self.state_timer = 0; self.has_hit = False; return
        if inp['special']: self.state = 'special'; self.state_timer = 0; return
        if inp['up'] and self.on_ground: self.vy = -15; self.on_ground = False; self.state = 'jump'; return
        
        moved = False; sp = self.cfg['speed']
        if inp['left']: self.x -= sp; moved = True
        if inp['right']: self.x += sp; moved = True
        if self.state != 'jump':
            self.state = 'walk' if moved else 'idle'
            if not moved: self.state_timer = 0

    def update(self, opp, game, dt):
        self.anim += dt * 60
        self.vy += GRAVITY * dt * 60
        self.y += self.vy * dt * 60
        if self.y >= GROUND_Y: self.y = GROUND_Y; self.vy = 0; self.on_ground = True
        else: self.on_ground = False
        self.x += self.vx * dt * 60; self.vx *= 0.85
        if abs(self.vx) < 0.1: self.vx = 0
        self.x = max(60, min(WIDTH - 60, self.x))
        
        if self.frozen > 0:
            self.frozen -= dt * 60
            if self.state != 'ko': self.state = 'idle'
            return
        self.state_timer += dt * 60
        if self.state in ('punch', 'kick'):
            a = self.attacks[self.state]
            if self.state_timer >= a['startup'] + a['active'] + a['recover']:
                self.state = 'idle' if self.on_ground else 'jump'; self.state_timer = 0
        elif self.state == 'special':
            a = self.attacks['special']
            if self.state_timer >= a['startup'] and not getattr(self, 'projectile_fired', False):
                game.spawn_projectile(self)
                self.projectile_fired = True
            if self.state_timer >= a['startup'] + a['recover']:
                self.state = 'idle' if self.on_ground else 'jump'; self.state_timer = 0
                self.projectile_fired = False
        elif self.state == 'hurt':
            if self.state_timer >= self.hurt_time: self.state = 'idle'; self.state_timer = 0
        elif self.state in ('idle', 'walk', 'block') and not self.on_ground: self.state = 'jump'
        elif self.state == 'jump' and self.on_ground: self.state = 'idle'

    def body_rect(self):
        h = 140 if self.state == 'block' else 180
        return pygame.Rect(int(self.x) - 30, int(self.y) - h, 60, h)

    def get_hitbox(self):
        a = self.attacks.get(self.state)
        if not a or a['reach'] == 0: return None
        t = self.state_timer
        if a['startup'] <= t < a['startup'] + a['active']:
            w, h = a['reach'], a['h']; y0 = int(self.y) - a['y_off'] - h // 2
            x0 = int(self.x) + 15 if self.facing == 1 else int(self.x) - 15 - w
            return pygame.Rect(x0, y0, w, h)
        return None

class Projectile:
    def __init__(self, x, y, vx, owner, color, kind):
        self.x, self.y, self.vx = x, y, vx
        self.owner = owner; self.color = color; self.kind = kind
        self.dead = False; self.trail = []
    def rect(self): return pygame.Rect(int(self.x) - 14, int(self.y) - 14, 28, 28)
    def update(self, dt):
        self.x += self.vx * dt * 60; self.trail.append((self.x, self.y))
        if len(self.trail) > 8: self.trail.pop(0)
        if self.x < -60 or self.x > WIDTH + 60: self.dead = True
    def draw(self, surf):
        for i, (tx, ty) in enumerate(self.trail):
            c = tuple(min(255, v + i * 12) for v in self.color)
            pygame.draw.circle(surf, c, (int(tx), int(ty)), int(3 + i * 0.9))
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), 13)
        pygame.draw.circle(surf, (255, 255, 255), (int(self.x), int(self.y)), 6)

class Particle:
    def __init__(self, x, y, color):
        self.x, self.y = x, y; a = random.uniform(0, math.tau); s = random.uniform(1.5, 5.5)
        self.vx = math.cos(a) * s; self.vy = math.sin(a) * s
        self.life = random.randint(12, 26); self.max_life = self.life; self.color = color
    def update(self):
        self.x += self.vx; self.y += self.vy; self.vy += 0.25; self.vx *= 0.96; self.life -= 1
    def draw(self, surf):
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), max(1, int(4 * self.life / self.max_life)))

class Game:
    def __init__(self):
        self.state = 'select'; self.sel = [0, 3]; self.ready = [False, False]
        self.cpu = True; self.wins = [0, 0]; self.round_num = 1
        self.projectiles = []; self.particles = []; self.ai_hold = 0; self.ai_decision = {}
        self.result_text = ""; self.f1 = self.f2 = None
        self.last_time = pygame.time.get_ticks()

    def start_round(self):
        self.f1 = Fighter(NAMES[self.sel[0]], WIDTH // 2 - 220, 1)
        self.f2 = Fighter(NAMES[self.sel[1]], WIDTH // 2 + 220, -1, is_cpu=self.cpu)
        self.timer = 60 * 60; self.projectiles = []; self.particles = []; self.state = 'fight'

    def spawn_projectile(self, f):
        self.projectiles.append(Projectile(f.x + 45 * f.facing, f.y - 130, f.cfg['proj_speed'] * f.facing, f, f.cfg['proj_color'], f.cfg['special']))

    def spark(self, x, y, color):
        for _ in range(10): self.particles.append(Particle(x, y, color))

    def blood(self, x, y):
        for _ in range(15): self.particles.append(Particle(x, y, (200, 20, 20)))
        
    def get_ai_input(self):
        keys = ['left', 'right', 'up', 'down', 'punch', 'kick', 'special']
        if self.ai_hold > 0: self.ai_hold -= 1; return self.ai_decision
        f, o = self.f2, self.f1
        inp = dict.fromkeys(keys, False)
        if f.frozen > 0 or f.state in ('punch', 'kick', 'special', 'hurt', 'ko'): self.ai_hold = 4; self.ai_decision = inp; return inp
        dist = abs(f.x - o.x); r = random.random()
        if o.state in ('punch', 'kick', 'special') and dist < 150 and r < 0.40: inp['down'] = True
        elif dist > 260:
            if r < 0.03: inp['special'] = True
            else: inp['right' if f.x < o.x else 'left'] = True
        elif dist > 115:
            if r < 0.45: inp['right' if f.x < o.x else 'left'] = True
            elif r < 0.50: inp['special'] = True
            elif r < 0.53: inp['kick'] = True
            else: inp['down'] = True
        else:
            if r < 0.32: inp['punch'] = True
            elif r < 0.48: inp['kick'] = True
            elif r < 0.56: inp['down'] = True
            elif r < 0.62: inp['up'] = True
            else: inp['left' if f.x < o.x else 'right'] = True
        self.ai_hold = random.randint(7, 16); self.ai_decision = inp; return inp

    def separate(self):
        if abs(self.f1.x - self.f2.x) < 55:
            push = (55 - abs(self.f1.x - self.f2.x)) / 2
            if self.f1.x < self.f2.x: self.f1.x -= push; self.f2.x += push
            else: self.f1.x += push; self.f2.x -= push
            
    def apply_hit(self, a, b, atk):
        if b.state == 'ko': return
        dmg = atk['dmg']
        if b.state == 'block':
            b.hp -= max(1, dmg // 5); b.x += 12 * a.facing; self.spark(b.x, b.y - 110, (120, 200, 255))
        else:
            b.hp -= dmg; b.state = 'hurt'; b.state_timer = 0; b.hurt_time = atk['hitstun']
            b.vx = atk['kb'] * a.facing; b.frozen = 0; self.blood(b.x, b.y - 115)
        b.hp = max(0, b.hp)
        
    def check_hits(self):
        for a, b in ((self.f1, self.f2), (self.f2, self.f1)):
            hb = a.get_hitbox()
            if hb and not a.has_hit and hb.colliderect(b.body_rect()):
                a.has_hit = True; self.apply_hit(a, b, a.attacks[a.state])
                
    def update_projectiles(self, dt):
        for pr in self.projectiles:
            pr.update(dt); target = self.f2 if pr.owner is self.f1 else self.f1
            if not pr.dead and pr.rect().colliderect(target.body_rect()):
                pr.dead = True; self.projectile_hit(pr, target)
        self.projectiles = [p for p in self.projectiles if not p.dead]
        
    def projectile_hit(self, pr, target):
        if target.state == 'ko': return
        dmg = {'SPEAR': 10, 'ICE BLAST': 8, 'LIGHTNING': 14, 'FIREBALL': 11}.get(pr.kind, 10)
        direction = 1 if pr.vx > 0 else -1
        if target.state == 'block':
            target.hp -= max(1, dmg // 5); target.x += 15 * direction; self.spark(target.x, target.y - 110, (120, 200, 255))
        else:
            target.hp -= dmg
            if pr.kind == 'ICE BLAST':
                target.frozen = 55; target.state = 'idle'; target.state_timer = 0
            elif pr.kind == 'SPEAR':
                target.x = pr.owner.x + 70 * direction; target.state = 'hurt'; target.state_timer = 0; target.hurt_time = 28
            else:
                target.state = 'hurt'; target.state_timer = 0; target.hurt_time = 20; target.vx = 6 * direction
            self.blood(target.x, target.y - 110)
        target.hp = max(0, target.hp)
        
    def update_particles(self, dt):
        for p in self.particles: p.update()
        self.particles = [p for p in self.particles if p.life > 0]
        
    def end_round(self):
        loser = winner = None
        if self.f1.hp <= 0 and self.f2.hp <= 0: self.result_text = "DOUBLE K.O."
        elif self.f1.hp <= 0: self.wins[1] += 1; loser, winner = self.f1, self.f2; self.result_text = f"{self.f2.name} WINS"
        elif self.f2.hp <= 0: self.wins[0] += 1; loser, winner = self.f2, self.f1; self.result_text = f"{self.f1.name} WINS"
        else:
            if self.f1.hp > self.f2.hp: self.wins[0] += 1; loser = self.f2; self.result_text = f"{self.f1.name} WINS (TIME)"
            elif self.f2.hp > self.f1.hp: self.wins[1] += 1; loser = self.f1; self.result_text = f"{self.f2.name} WINS (TIME)"
            else: self.result_text = "TIME OVER - DRAW"
        if loser: loser.state = 'ko'; loser.state_timer = 0
        if winner: winner.state = 'win'; winner.state_timer = 0
        self.state = 'round_over'; self.round_over_t = 170

    def update_fight(self, dt, freeze=False):
        if not freeze:
            k = pygame.key.get_pressed()
            inp1 = {'left': k[pygame.K_a], 'right': k[pygame.K_d], 'up': k[pygame.K_w], 'down': k[pygame.K_s], 'punch': k[pygame.K_f], 'kick': k[pygame.K_g], 'special': k[pygame.K_h]}
            inp2 = self.get_ai_input() if self.cpu else {'left': k[pygame.K_LEFT], 'right': k[pygame.K_RIGHT], 'up': k[pygame.K_UP], 'down': k[pygame.K_DOWN], 'punch': k[pygame.K_j], 'kick': k[pygame.K_k], 'special': k[pygame.K_l]}
            self.f1.handle_input(inp1, self.f2); self.f2.handle_input(inp2, self.f1)
        self.f1.update(self.f2, self, dt); self.f2.update(self.f1, self, dt); self.separate()
        self.check_hits(); self.update_projectiles(dt); self.update_particles(dt)
        if not freeze:
            self.timer -= dt * 60
            if self.f1.hp <= 0 or self.f2.hp <= 0 or self.timer <= 0: self.end_round()

    def draw_bg(self, surf):
        for i in range(HEIGHT):
            t = i / HEIGHT
            surf.fill((int(10 + 25 * t), int(5 + 15 * t), int(20 + 40 * t)), (0, i, WIDTH, 1))
        pygame.draw.circle(surf, (200, 210, 230), (WIDTH - 170, 120), 52)
        pygame.draw.circle(surf, (10, 5, 20), (WIDTH - 150, 105), 46)
        for tx in (120, WIDTH - 120):
            pygame.draw.rect(surf, (50, 35, 35), (tx - 12, 210, 24, 290))
            pygame.draw.rect(surf, (70, 50, 50), (tx - 15, 200, 30, 15))
            fy = 200 + math.sin(pygame.time.get_ticks() * 0.012 + tx) * 6
            pygame.draw.circle(surf, (255, 100, 20), (tx, int(fy)), 20)
            pygame.draw.circle(surf, (255, 180, 40), (tx, int(fy)), 12)
            pygame.draw.circle(surf, (255, 255, 200), (tx, int(fy)), 5)
        pygame.draw.rect(surf, (30, 20, 25), (0, GROUND_Y, WIDTH, HEIGHT - GROUND_Y))
        pygame.draw.line(surf, (100, 80, 80), (0, GROUND_Y), (WIDTH, GROUND_Y), 3)
        for i in range(0, WIDTH, 40):
            pygame.draw.line(surf, (45, 35, 35), (i, GROUND_Y), (i + 20, HEIGHT), 2)

    def draw_hud(self, surf):
        bar_w, bar_h = 380, 26
        for i, (f, side) in enumerate(((self.f1, 'L'), (self.f2, 'R'))):
            x = 30 if side == 'L' else WIDTH - 30 - bar_w
            pygame.draw.rect(surf, (55, 20, 20), (x, 30, bar_w, bar_h))
            w = int(bar_w * f.hp / 100)
            if side == 'L': pygame.draw.rect(surf, (230, 45, 45), (x, 30, w, bar_h))
            else: pygame.draw.rect(surf, (230, 45, 45), (x + bar_w - w, 30, w, bar_h))
            pygame.draw.rect(surf, (240, 240, 240), (x, 30, bar_w, bar_h), 3)
            nm = font_med.render(f.name, True, f.cfg['accent'])
            nx = x if side == 'L' else x + bar_w - nm.get_width()
            surf.blit(nm, (nx, 62))
            for k in range(2):
                cx = (x + 12 + k * 22) if side == 'L' else (x + bar_w - 12 - k * 22)
                col = (255, 210, 60) if self.wins[i] > k else (70, 60, 60)
                pygame.draw.circle(surf, col, (cx, 108), 7)
        secs = max(0, int(self.timer // 60))
        ts = font_big.render(f"{secs:02d}", True, (255, 240, 200))
        surf.blit(ts, (WIDTH // 2 - ts.get_width() // 2, 30))

    def draw_select(self, surf):
        surf.fill((15, 15, 22))
        title = font_title.render("MORTAL KOMBAT", True, (200, 30, 30))
        surf.blit(title, (WIDTH // 2 - title.get_width() // 2, 30))
        sub = font_med.render("CHOOSE YOUR FIGHTER", True, (200, 200, 200))
        surf.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 118))
        cw, ch = 180, 250; total = 4 * cw + 3 * 30; start_x = (WIDTH - total) // 2
        for i, name in enumerate(NAMES):
            x = start_x + i * (cw + 30); y = 170; rect = pygame.Rect(x, y, cw, ch); cfg = CHARACTERS[name]
            pygame.draw.rect(surf, (28, 28, 38), rect, border_radius=8)
            hx, hy = x + cw // 2, y + 85
            pygame.draw.circle(surf, (232, 198, 160), (hx, hy), 38)
            pygame.draw.rect(surf, cfg['color'], (hx - 38, hy - 12, 76, 22))
            pygame.draw.circle(surf, cfg['accent'], (hx - 15, hy - 1), 7); pygame.draw.circle(surf, cfg['accent'], (hx + 15, hy - 1), 7)
            pygame.draw.rect(surf, cfg['color'], (hx - 34, y + 130, 68, 80), border_radius=6)
            nm = font_med.render(name, True, (255, 255, 255))
            surf.blit(nm, (x + cw // 2 - nm.get_width() // 2, y + ch - 34))
            if self.sel[0] == i:
                col = (60, 255, 60) if self.ready[0] else (255, 60, 60)
                pygame.draw.rect(surf, col, rect, 5, border_radius=8)
            if self.sel[1] == i:
                col = (60, 255, 60) if self.ready[1] else (60, 160, 255)
                pygame.draw.rect(surf, col, rect.inflate(-14, -14), 4, border_radius=6)
        info = font_small.render("P1: A/D + F | P2: <-/-> + K | TAB: CPU | ESC: quit", True, (170, 170, 180))
        surf.blit(info, (WIDTH // 2 - info.get_width() // 2, HEIGHT - 70))
        mode = "CPU: ON" if self.cpu else "CPU: OFF"
        ms = font_med.render(mode, True, (120, 220, 120) if self.cpu else (220, 180, 120))
        surf.blit(ms, (WIDTH // 2 - ms.get_width() // 2, HEIGHT - 110))

    def draw(self, surf):
        if self.state == 'select': self.draw_select(surf); return
        self.draw_bg(surf)
        for p in self.particles: p.draw(surf)
        for pr in self.projectiles: pr.draw(surf)
        if self.f2.state != 'ko':
            draw_fighter(surf, self.f2); draw_fighter(surf, self.f1)
        else:
            draw_fighter(surf, self.f1); draw_fighter(surf, self.f2)
        self.draw_hud(surf)
        if self.state == 'round_over':
            t = font_big.render(self.result_text, True, (255, 220, 90)); surf.blit(t, (WIDTH // 2 - t.get_width() // 2, HEIGHT // 2 - 100))
        elif self.state == 'match_over':
            t = font_title.render(self.result_text, True, (255, 60, 60)); surf.blit(t, (WIDTH // 2 - t.get_width() // 2, HEIGHT // 2 - 140))
            s = font_med.render("PRESS ENTER TO RETURN TO SELECT", True, (230, 230, 230)); surf.blit(s, (WIDTH // 2 - s.get_width() // 2, HEIGHT // 2 - 40))

    def update(self, dt):
        if self.state == 'fight': self.update_fight(dt)
        elif self.state == 'round_over':
            self.update_fight(dt, freeze=True); self.round_over_t -= dt * 60
            if self.round_over_t <= 0:
                if max(self.wins) >= 2:
                    self.state = 'match_over'
                    champ = self.f1.name if self.wins[0] > self.wins[1] else self.f2.name
                    self.result_text = f"{champ} WINS THE MATCH!"
                else:
                    self.round_num += 1; self.start_round()
        elif self.state == 'match_over': self.update_particles(dt)

def main():
    game = Game()
    while True:
        dt = min(clock.tick(FPS) / 1000.0, 0.05)
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE: pygame.quit(); sys.exit()
                if game.state == 'select':
                    if e.key == pygame.K_TAB: game.cpu = not game.cpu
                    if not game.ready[0]:
                        if e.key == pygame.K_a: game.sel[0] = (game.sel[0] - 1) % 4
                        elif e.key == pygame.K_d: game.sel[0] = (game.sel[0] + 1) % 4
                        elif e.key == pygame.K_f: game.ready[0] = True
                    else:
                        if e.key == pygame.K_a or e.key == pygame.K_d: game.ready[0] = False
                    if not game.ready[1]:
                        if not game.cpu:
                            if e.key == pygame.K_LEFT: game.sel[1] = (game.sel[1] - 1) % 4
                            elif e.key == pygame.K_RIGHT: game.sel[1] = (game.sel[1] + 1) % 4
                            elif e.key == pygame.K_k: game.ready[1] = True
                        else:
                            if e.key == pygame.K_k: game.ready[1] = True
                    else:
                        if not game.cpu and e.key in (pygame.K_LEFT, pygame.K_RIGHT): game.ready[1] = False
                    if game.ready[0] and game.ready[1]: game.wins = [0, 0]; game.round_num = 1; game.start_round()
                elif game.state == 'match_over':
                    if e.key == pygame.K_RETURN: game.state = 'select'; game.ready = [False, False]; game.wins = [0, 0]
        game.update(dt)
        screen.fill((0, 0, 0))
        game.draw(screen)
        pygame.display.flip()

if __name__ == "__main__":
    main()