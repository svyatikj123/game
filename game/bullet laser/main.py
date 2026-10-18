import pygame
import random
import sys
import os
import math

# --- НАСТРОЙКИ ЭКРАНА ---
WIDTH, HEIGHT = 800, 600
FPS = 60
PLAYER_SIZE = 40
ENEMY_SIZE = 40
WORLD_WIDTH, WORLD_HEIGHT = 2000, 2000

# --- ЦВЕТА ---
WHITE = (255, 255, 255)
RED = (255, 50, 50)
DARK_RED = (150, 0, 0)
BLACK = (0, 0, 0)
SHIELD_COLOR = (100, 200, 255)
GREEN = (50, 255, 50)
CYAN = (0, 255, 255)
PURPLE = (200, 0, 255)
YELLOW = (255, 255, 0)
ORANGE = (255, 150, 0)
GREY = (180, 180, 180)

# --- НАСТРОЙКИ СЛОЖНОСТИ ---
DIFFICULTIES = {
    "EASY":   {"lives": 5, "max_lives": 5, "speed_mod": 0.8, "spawn_mod": 1.2, "color": GREEN},
    "NORMAL": {"lives": 3, "max_lives": 5, "speed_mod": 1.0, "spawn_mod": 1.0, "color": YELLOW},
    "HARD":   {"lives": 1, "max_lives": 3, "speed_mod": 1.4, "spawn_mod": 0.7, "color": RED}
}

# --- КУЛДАУНЫ ---
CD_DASH = 90
OVERDRIVE_DURATION = 300
AURA_DURATION = 300

# --- ИНИЦИАЛИЗАЦИЯ ---
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Space Shooter: OVERDRIVE")
clock = pygame.time.Clock()
font_small  = pygame.font.SysFont("Arial", 14, bold=True)
font_medium = pygame.font.SysFont("Arial", 24, bold=True)
font_big    = pygame.font.SysFont("Impact", 48)
font_huge   = pygame.font.SysFont("Impact", 72)

# --- ЗАГРУЗКА ГРАФИКИ ---
def load_image(filename, size, fallback_color):
    if os.path.exists(filename):
        try:
            img = pygame.image.load(filename).convert_alpha()
            return pygame.transform.scale(img, size)
        except Exception:
            pass
    surf = pygame.Surface(size, pygame.SRCALPHA)
    surf.fill(fallback_color)
    pygame.draw.rect(surf, WHITE, surf.get_rect(), 2)
    return surf

player1_img = load_image("player.png",  (PLAYER_SIZE, PLAYER_SIZE), (0, 150, 255))
player2_img = load_image("player2.png", (PLAYER_SIZE, PLAYER_SIZE), (200, 30, 30))
enemy_img   = load_image("enemy.png",   (ENEMY_SIZE, ENEMY_SIZE),   (120, 120, 120))
bullet_img  = load_image("bullet.png",  (8, 20),                    (255, 255, 0))
shield_img  = load_image("shield.png",  (50, 50),                   (0, 255, 200))

# Создаем фон
world_surface = pygame.Surface((WORLD_WIDTH, WORLD_HEIGHT))
if os.path.exists("background.png"):
    try:
        bg_img = pygame.image.load("background.png").convert()
        bg_img = pygame.transform.scale(bg_img, (WIDTH, HEIGHT))
        for x in range(0, WORLD_WIDTH, WIDTH):
            for y in range(0, WORLD_HEIGHT, HEIGHT):
                world_surface.blit(bg_img, (x, y))
    except: world_surface.fill((10, 10, 25))
else: world_surface.fill((10, 10, 25))

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def draw_glow(surface, color, pos, radius, intensity=3):
    glow_surf = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
    for i in range(intensity):
        alpha = max(0, 150 - i * 40)
        pygame.draw.circle(glow_surf, (*color, alpha), (radius, radius), radius - i*2)
    surface.blit(glow_surf, (pos[0]-radius, pos[1]-radius), special_flags=pygame.BLEND_RGBA_ADD)

# --- КЛАСС КАМЕРЫ ---
class Camera:
    def __init__(self):
        self.x, self.y = 0, 0
        self.shake_timer, self.shake_intensity = 0, 0

    def update(self, target):
        target_x = target.rect.centerx - WIDTH // 2
        target_y = target.rect.centery - HEIGHT // 2
        target_x = max(0, min(WORLD_WIDTH - WIDTH, target_x))
        target_y = max(0, min(WORLD_HEIGHT - HEIGHT, target_y))
        
        self.x += (target_x - self.x) * 0.1
        self.y += (target_y - self.y) * 0.1

        if self.shake_timer > 0:
            self.shake_timer -= 1

    def get_offset(self):
        off_x, off_y = self.x, self.y
        if self.shake_timer > 0:
            off_x += random.randint(-self.shake_intensity, self.shake_intensity)
            off_y += random.randint(-self.shake_intensity, self.shake_intensity)
        return int(off_x), int(off_y)

    def shake(self, duration, intensity):
        self.shake_timer = max(self.shake_timer, duration)
        self.shake_intensity = max(self.shake_intensity, intensity)

# --- ЭФФЕКТЫ ---
class Particle:
    def __init__(self, x, y, color, speed=5, size=3, decay=0.95):
        self.x, self.y = x, y
        angle = random.uniform(0, math.pi * 2)
        self.dx = math.cos(angle) * random.uniform(0.5, speed)
        self.dy = math.sin(angle) * random.uniform(0.5, speed)
        self.life = random.randint(20, 40)
        self.max_life = self.life
        self.color = color
        self.size = size
        self.decay = decay

    def update(self):
        self.x += self.dx
        self.y += self.dy
        self.dx *= self.decay
        self.dy *= self.decay
        self.life -= 1

    def draw(self, surface, off_x, off_y):
        if self.life > 0:
            alpha = int(255 * (self.life / self.max_life))
            c = (*self.color[:3], alpha)
            s = pygame.Surface((self.size*2, self.size*2), pygame.SRCALPHA)
            pygame.draw.circle(s, c, (self.size, self.size), self.size)
            surface.blit(s, (self.x - off_x - self.size, self.y - off_y - self.size))

class Shockwave:
    def __init__(self, x, y, color, max_radius=100):
        self.x, self.y = x, y
        self.color = color
        self.radius = 5
        self.max_radius = max_radius
        self.life = 15

    def update(self):
        self.radius += (self.max_radius - self.radius) * 0.2
        self.life -= 1

    def draw(self, surface, off_x, off_y):
        if self.life > 0:
            alpha = int(255 * (self.life / 15))
            pygame.draw.circle(surface, (*self.color, alpha), (int(self.x - off_x), int(self.y - off_y)), int(self.radius), 2)

class FloatingText:
    def __init__(self, x, y, text, color=WHITE, size="small"):
        self.x, self.y = x, y
        self.text = text
        self.color = color
        self.life = 60
        self.font = font_medium if size == "big" else font_small
        self.dy = -1.5

    def update(self):
        self.y += self.dy
        self.dy *= 0.95
        self.life -= 1

    def draw(self, surface, off_x, off_y):
        if self.life > 0:
            alpha = min(255, self.life * 5)
            text_surf = self.font.render(self.text, True, self.color)
            text_surf.set_alpha(alpha)
            surface.blit(text_surf, (self.x - off_x, self.y - off_y))

class GlobalText:
    """Текст, который отображается по центру экрана (для пасхалок)"""
    def __init__(self, text, color, size="big", duration=60):
        self.text = text
        self.color = color
        self.font = font_huge if size == "huge" else font_big
        self.life = duration
        self.max_life = duration

    def update(self):
        self.life -= 1

    def draw(self, surface):
        if self.life > 0:
            alpha = min(255, self.life * 10)
            text_surf = self.font.render(self.text, True, self.color)
            text_surf.set_alpha(alpha)
            surface.blit(text_surf, (WIDTH // 2 - text_surf.get_width() // 2, HEIGHT // 2 - 100))

# --- БОНУСЫ ---
class PowerUp:
    def __init__(self, player_x):
        self.x = random.randint(max(0, player_x - 300), min(WORLD_WIDTH - 50, player_x + 300))
        self.y = -50
        self.speed = 3
        self.rect = pygame.Rect(self.x, self.y, 40, 40)

    def update(self):
        self.y += self.speed
        self.rect.y = self.y

    def draw(self, surface, off_x, off_y):
        surface.blit(shield_img, (self.x - off_x, self.y - off_y))

class Spoon:
    """Секретная пасхалка: Ложка (Матрица)"""
    def __init__(self, player_x):
        self.x = random.randint(0, WORLD_WIDTH)
        self.y = -50
        self.speed = 5
        self.rect = pygame.Rect(self.x, self.y, 20, 40)

    def update(self):
        self.y += self.speed
        self.rect.y = self.y

    def draw(self, surface, off_x, off_y):
        dx, dy = self.x - off_x, self.y - off_y
        # Рисуем ложку кодом
        pygame.draw.ellipse(surface, GREY, (dx, dy, 20, 30))
        pygame.draw.ellipse(surface, (100,100,100), (dx+2, dy+2, 16, 26))
        pygame.draw.rect(surface, GREY, (dx + 7, dy + 25, 6, 20))
        draw_glow(surface, WHITE, (int(dx+10), int(dy+15)), 20, 1)

# --- КЛАСС ИГРОКА ---
class Player:
    def __init__(self, max_lives, hero_type):
        self.x = WORLD_WIDTH // 2 - PLAYER_SIZE // 2
        self.y = WORLD_HEIGHT - 200
        self.rect = pygame.Rect(self.x, self.y, PLAYER_SIZE, PLAYER_SIZE)
        self.hero_type = hero_type
        
        self.lives = max_lives
        self.max_lives = max_lives
        self.invincible_timer = 0
        self.weapon_level = 1
        
        self.shoot_timer = 0
        self.shield_active = False
        self.shield_timer = 0
        self.dash_timer = 0
        self.dash_cd = 0
        self.is_dashing = False
        self.dash_dx, self.dash_dy = 0, 0

        self.cd_q, self.cd_w, self.cd_e, self.cd_r = 0, 0, 0, 0
        self.overdrive_timer = 0
        self.aura_timer = 0

    def take_damage(self, amount=1):
        if self.invincible_timer <= 0 and not self.shield_active and not self.is_dashing:
            self.lives -= amount
            self.invincible_timer = 90
            self.weapon_level = max(1, self.weapon_level - 1)
            return True
        return False

    def update(self, global_texts):
        keys = pygame.key.get_pressed()
        speed = 8 if self.overdrive_timer > 0 else 6
        
        if self.dash_cd > 0: self.dash_cd -= 1
        if self.is_dashing:
            self.x += self.dash_dx * 20
            self.y += self.dash_dy * 20
            self.dash_timer -= 1
            if self.dash_timer <= 0:
                self.is_dashing = False
        else:
            if keys[pygame.K_LSHIFT] and self.dash_cd == 0:
                self.is_dashing = True
                self.dash_timer = 10
                self.dash_cd = CD_DASH
                self.invincible_timer = 15
                self.dash_dx = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
                self.dash_dy = (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w])
                if self.dash_dx == 0 and self.dash_dy == 0: self.dash_dy = -1
                
                # ПАСХАЛКА: JoJo's Bizarre Adventure
                if random.random() < 0.3: # 30% шанс при рывке
                    text = "ZA WARUDO!" if random.random() < 0.5 else "TOKI WO TOMARE!"
                    global_texts.append(GlobalText(text, CYAN))
                
            if (keys[pygame.K_LEFT] or keys[pygame.K_a]) and self.x > 0: self.x -= speed
            if (keys[pygame.K_RIGHT] or keys[pygame.K_d]) and self.x < WORLD_WIDTH - PLAYER_SIZE: self.x += speed
            if keys[pygame.K_UP] or keys[pygame.K_w]: self.y -= speed
            if keys[pygame.K_DOWN] or keys[pygame.K_s]: self.y += speed

        self.x = max(0, min(WORLD_WIDTH - PLAYER_SIZE, self.x))
        self.y = max(0, min(WORLD_HEIGHT - PLAYER_SIZE, self.y))
        self.rect.x, self.rect.y = self.x, self.y

        if self.shoot_timer > 0: self.shoot_timer -= 1
        if self.invincible_timer > 0: self.invincible_timer -= 1
        if self.shield_active:
            self.shield_timer -= 1
            if self.shield_timer <= 0: self.shield_active = False
        if self.cd_q > 0: self.cd_q -= 1
        if self.cd_w > 0: self.cd_w -= 1
        if self.cd_e > 0: self.cd_e -= 1
        if self.cd_r > 0: self.cd_r -= 1
        if self.overdrive_timer > 0: self.overdrive_timer -= 1
        if self.aura_timer > 0: self.aura_timer -= 1

    def shoot(self):
        if self.shoot_timer == 0:
            self.shoot_timer = 5 if self.overdrive_timer > 0 else 10
            bullets = []
            cx, cy = self.rect.centerx, self.y - 10
            
            if self.weapon_level == 1:
                bullets.append(Bullet(cx, cy, speed_y=-15))
            elif self.weapon_level == 2:
                bullets.append(Bullet(cx - 8, cy, speed_y=-15))
                bullets.append(Bullet(cx + 8, cy, speed_y=-15))
            elif self.weapon_level == 3:
                bullets.append(Bullet(cx, cy, speed_y=-15))
                bullets.append(Bullet(cx - 12, cy + 10, speed_x=-2, speed_y=-15))
                bullets.append(Bullet(cx + 12, cy + 10, speed_x=2, speed_y=-15))
            elif self.weapon_level >= 4:
                bullets.append(Bullet(cx - 5, cy, speed_y=-15))
                bullets.append(Bullet(cx + 5, cy, speed_y=-15))
                bullets.append(Bullet(cx - 15, cy + 10, speed_x=-3, speed_y=-15))
                bullets.append(Bullet(cx + 15, cy + 10, speed_x=3, speed_y=-15))
                if self.weapon_level == 5:
                    bullets.append(Bullet(cx, cy - 10, speed_y=-20, piercing=True, width=6, height=30))
            return bullets
        return []

    def spread_shot(self):
        if self.cd_q == 0:
            self.cd_q = 120
            cx, cy = self.rect.centerx, self.y - 10
            return [Bullet(cx + dx, cy, speed_x=dx*0.5, speed_y=-15) for dx in range(-30, 31, 10)]
        return []

    def erase_beam(self):
        if self.cd_q == 0:
            self.cd_q = 180
            return Bullet(self.rect.centerx - 20, self.y - 20, speed_y=-25, width=40, height=100, piercing=True, color=CYAN)
        return None

    def draw(self, surface, off_x, off_y, particles_list):
        if self.invincible_timer > 0 and (self.invincible_timer // 4) % 2 == 0:
            return 

        dx, dy = self.x - off_x, self.y - off_y
        
        if self.is_dashing:
            pygame.draw.rect(surface, (0, 255, 255, 100), (dx - 10, dy - 10, PLAYER_SIZE + 20, PLAYER_SIZE + 20), 2)
            for _ in range(3):
                particles_list.append(Particle(self.rect.centerx, self.rect.centery, CYAN, speed=2, decay=0.8))

        img = player1_img if self.hero_type == "INTERCEPTOR" else player2_img
        surface.blit(img, (dx, dy))

        if self.shield_active:
            shield_rect = shield_img.get_rect(center=(dx + PLAYER_SIZE // 2, dy + PLAYER_SIZE // 2))
            surface.blit(shield_img, shield_rect)
            draw_glow(surface, SHIELD_COLOR, (self.rect.centerx - off_x, self.rect.centery - off_y), 40, 2)
            
        if self.aura_timer > 0:
            pygame.draw.circle(surface, RED, (dx + PLAYER_SIZE // 2, dy + PLAYER_SIZE // 2), 150, 3)
            pygame.draw.circle(surface, ORANGE, (dx + PLAYER_SIZE // 2, dy + PLAYER_SIZE // 2), 140, 1)

# --- КЛАСС ПУЛИ ---
class Bullet:
    def __init__(self, x, y, speed_x=0, speed_y=-15, width=8, height=20, piercing=False, color=None):
        self.x, self.y = x, y
        self.speed_x, self.speed_y = speed_x, speed_y
        self.piercing = piercing
        self.color = color
        self.rect = pygame.Rect(x - width//2, y, width, height)
        self.image = pygame.transform.scale(bullet_img, (width, height))

    def update(self):
        self.x += self.speed_x
        self.y += self.speed_y
        self.rect.centerx = self.x
        self.rect.y = self.y

    def draw(self, surface, off_x, off_y):
        dx, dy = self.x - off_x, self.y - off_y
        if self.piercing:
            color = self.color if self.color else RED
            pygame.draw.rect(surface, color, (dx - self.rect.width//2, dy, self.rect.width, self.rect.height))
            draw_glow(surface, color, (int(dx), int(dy + self.rect.height//2)), self.rect.width)
        else:
            surface.blit(self.image, (dx - self.rect.width//2, dy))
            if self.color:
                pygame.draw.rect(surface, self.color, (dx - 2, dy, 4, self.rect.height), border_radius=2)

class EnemyBullet(Bullet):
    def __init__(self, x, y, target_x, target_y, speed=6, color=CYAN):
        angle = math.atan2(target_y - y, target_x - x)
        super().__init__(x, y, math.cos(angle)*speed, math.sin(angle)*speed, 10, 10, color=color)

    def draw(self, surface, off_x, off_y):
        dx, dy = self.x - off_x, self.y - off_y
        draw_glow(surface, self.color, (int(dx), int(dy)), 15, 2)
        pygame.draw.circle(surface, WHITE, (int(dx), int(dy)), 3)

# --- ВРАГИ ---
class Enemy:
    def __init__(self, x, y, hp, speed_x, speed_y):
        self.x, self.y = x, y
        self.hp = hp
        self.max_hp = hp
        self.speed_x, self.speed_y = speed_x, speed_y
        self.rect = pygame.Rect(x, y, ENEMY_SIZE, ENEMY_SIZE)
        self.hit_flash = 0
        self.score_value = 10

    def update(self, player):
        self.x += self.speed_x
        self.y += self.speed_y
        if self.hit_flash > 0: self.hit_flash -= 1
        self.rect.x, self.rect.y = self.x, self.y

    def draw(self, surface, off_x, off_y):
        img = enemy_img
        if self.hit_flash > 0:
            temp = img.copy()
            temp.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGBA_ADD)
            surface.blit(temp, (self.x - off_x, self.y - off_y))
        else:
            surface.blit(img, (self.x - off_x, self.y - off_y))
            
        if self.hp < self.max_hp:
            pygame.draw.rect(surface, RED, (self.x - off_x, self.y - off_y - 10, ENEMY_SIZE, 4))
            pygame.draw.rect(surface, GREEN, (self.x - off_x, self.y - off_y - 10, ENEMY_SIZE * (self.hp/self.max_hp), 4))

class BasicEnemy(Enemy):
    def __init__(self, level, player_x):
        x = random.randint(max(0, player_x - 400), min(WORLD_WIDTH - ENEMY_SIZE, player_x + 400))
        super().__init__(x, -ENEMY_SIZE, 1, random.uniform(-1.5, 1.5), random.uniform(3, 5) + level*0.2)
        self.score_value = 10

class TankEnemy(Enemy):
    def __init__(self, level, player_x):
        x = random.randint(max(0, player_x - 300), min(WORLD_WIDTH - ENEMY_SIZE, player_x + 300))
        super().__init__(x, -ENEMY_SIZE, 5 + level, 0, 1.5 + level*0.1)
        self.score_value = 50
        self.shoot_timer = 60
        self.size = ENEMY_SIZE * 1.5
        self.rect.width, self.rect.height = self.size, self.size

    def update(self, player):
        super().update(player)
        self.shoot_timer -= 1
        if self.shoot_timer <= 0 and self.y > 0:
            self.shoot_timer = 120
            return True 
        return False

    def draw(self, surface, off_x, off_y):
        img = pygame.transform.scale(enemy_img, (int(self.size), int(self.size)))
        if self.hit_flash > 0:
            temp = img.copy()
            temp.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGBA_ADD)
            surface.blit(temp, (self.x - off_x, self.y - off_y))
        else:
            surface.blit(img, (self.x - off_x, self.y - off_y))
        pygame.draw.rect(surface, RED, (self.x - off_x, self.y - off_y - 10, self.size, 5))
        pygame.draw.rect(surface, GREEN, (self.x - off_x, self.y - off_y - 10, self.size * (self.hp/self.max_hp), 5))

class KamikazeEnemy(Enemy):
    def __init__(self, level, player_x, player_y):
        x = random.randint(0, WORLD_WIDTH)
        y = -ENEMY_SIZE
        super().__init__(x, y, 2, 0, 0)
        self.score_value = 20
        self.speed = 5 + level*0.5
        self.target = (player_x, player_y)

    def update(self, player):
        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        dist = math.hypot(dx, dy)
        if dist > 0:
            self.speed_x = (dx / dist) * self.speed
            self.speed_y = (dy / dist) * self.speed
        super().update(player)
        return False

    def draw(self, surface, off_x, off_y):
        dx, dy = self.x - off_x, self.y - off_y
        pygame.draw.polygon(surface, RED, [(dx+20, dy+40), (dx, dy), (dx+40, dy)])
        draw_glow(surface, RED, (int(dx+20), int(dy+20)), 20)

# --- БОСС ---
class Boss(Enemy):
    def __init__(self, level, player_x):
        super().__init__(WORLD_WIDTH//2 - 80, -150, 100 + level*50, 0, 1)
        self.size = 160
        self.rect.width, self.rect.height = self.size, self.size
        self.score_value = 1000
        self.phase = 1
        self.shoot_timer = 60
        self.move_timer = 0

    def update(self, player):
        self.move_timer += 1
        if self.y < 100: self.y += 1.5
        
        if self.y >= 100:
            self.x = (WORLD_WIDTH // 2 - 80) + math.sin(self.move_timer * 0.02) * 300
            
        self.rect.x, self.rect.y = self.x, self.y
        if self.hit_flash > 0: self.hit_flash -= 1
        
        self.shoot_timer -= 1
        if self.shoot_timer <= 0 and self.y >= 100:
            self.shoot_timer = 90 if self.hp > self.max_hp//2 else 45 
            return True
        return False

    def draw(self, surface, off_x, off_y):
        dx, dy = self.x - off_x, self.y - off_y
        pygame.draw.rect(surface, PURPLE, (dx, dy, self.size, self.size), border_radius=20)
        pygame.draw.circle(surface, RED, (int(dx+self.size//2), int(dy+self.size//2)), 40)
        draw_glow(surface, PURPLE, (int(dx+self.size//2), int(dy+self.size//2)), 80)

# --- ИНИЦИАЛИЗАЦИЯ ---
def reset_game(diff_params, hero_type):
    player = Player(diff_params["lives"], hero_type)
    player.max_lives = diff_params["max_lives"]
    camera = Camera()
    camera.x = player.rect.centerx - WIDTH // 2
    camera.y = player.rect.centery - HEIGHT // 2
    return (player, camera, [], [], [], [], [], [], [], 0, 0, 1, 0, 0)

player, camera, enemies, powerups, bullets, enemy_bullets, particles, shockwaves, spoons, score, enemy_spawn_timer, current_level, boss_spawned, combo = reset_game(DIFFICULTIES["NORMAL"], "INTERCEPTOR")
floating_texts = []
global_texts = [] # Для пасхалок на весь экран
game_state = "MENU"
selected_difficulty = "NORMAL"
selected_hero = "INTERCEPTOR"
screen_flash = 0
hit_stop = 0
combo_timer = 0

# --- ГЛАВНЫЙ ЦИКЛ ---
running = True
while running:
    clock.tick(FPS)
    
    # ===================== СОБЫТИЯ =====================
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if game_state == "MENU":
                if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    keys = list(DIFFICULTIES.keys())
                    idx = keys.index(selected_difficulty)
                    idx = (idx - 1) % len(keys) if event.key == pygame.K_LEFT else (idx + 1) % len(keys)
                    selected_difficulty = keys[idx]
                if event.key in (pygame.K_UP, pygame.K_DOWN):
                    heroes = ["INTERCEPTOR", "ANNIHILATOR"]
                    idx = heroes.index(selected_hero)
                    idx = (idx - 1) % len(heroes) if event.key == pygame.K_UP else (idx + 1) % len(heroes)
                    selected_hero = heroes[idx]
                if event.key == pygame.K_SPACE:
                    game_state = "PLAYING"
                    floating_texts.clear()
                    global_texts.clear()
                    player, camera, enemies, powerups, bullets, enemy_bullets, particles, shockwaves, spoons, score, enemy_spawn_timer, current_level, boss_spawned, combo = reset_game(DIFFICULTIES[selected_difficulty], selected_hero)

            elif game_state == "GAME_OVER" and event.key == pygame.K_r:
                game_state = "MENU"

            elif game_state == "PLAYING":
                if event.key == pygame.K_SPACE:
                    bullets.extend(player.shoot())

                if player.hero_type == "INTERCEPTOR":
                    if event.key == pygame.K_q and player.cd_q == 0: bullets.extend(player.spread_shot())
                    if event.key == pygame.K_w and player.cd_w == 0:
                        if player.lives < player.max_lives:
                            player.lives += 1
                            player.cd_w = 900
                            floating_texts.append(FloatingText(player.rect.centerx, player.rect.centery, "+1 HP", GREEN, "big"))
                    if event.key == pygame.K_e and player.cd_e == 0:
                        player.cd_e = 1200
                        camera.shake(20, 10)
                        screen_flash = 10
                        for e in enemies[:]:
                            if not isinstance(e, Boss):
                                score += e.score_value * max(1, combo)
                                for _ in range(10): particles.append(Particle(e.rect.centerx, e.rect.centery, CYAN))
                                enemies.remove(e)
                    if event.key == pygame.K_r and player.cd_r == 0:
                        player.cd_r = 600
                        player.overdrive_timer = OVERDRIVE_DURATION
                        # ПАСХАЛКА: DOOM
                        global_texts.append(GlobalText("RIP AND TEAR!", RED, "big"))
                
                elif player.hero_type == "ANNIHILATOR":
                    if event.key == pygame.K_q and player.cd_q == 0:
                        b = player.erase_beam()
                        if b: bullets.append(b)
                    if event.key == pygame.K_w and player.cd_w == 0:
                        player.cd_w = 900; player.cd_q = 0; player.cd_e = 0; player.cd_r = 0
                        for _ in range(30): particles.append(Particle(player.rect.centerx, player.rect.centery, WHITE))
                    if event.key == pygame.K_e and player.cd_e == 0:
                        player.cd_e = 1200
                        player.aura_timer = AURA_DURATION
                    if event.key == pygame.K_r and player.cd_r == 0:
                        player.cd_r = 600
                        camera.shake(30, 15)
                        screen_flash = 15
                        for e in enemies[:]:
                            if not isinstance(e, Boss):
                                score += e.score_value * max(1, combo)
                                for _ in range(20): particles.append(Particle(e.rect.centerx, e.rect.centery, PURPLE))
                                enemies.remove(e)
                        # ПАСХАЛКА: DOOM
                        global_texts.append(GlobalText("RIP AND TEAR!", RED, "big"))

    # ===================== ОБНОВЛЕНИЕ =====================
    if hit_stop > 0:
        hit_stop -= 1
    elif game_state == "PLAYING":
        player.update(global_texts) # Передаем список для JoJo пасхалки
        camera.update(player)

        if combo_timer > 0:
            combo_timer -= 1
            if combo_timer == 0:
                combo = 0
                floating_texts.append(FloatingText(player.rect.centerx, player.rect.centery - 60, "COMBO LOST", RED))

        new_level = 1 + (score // 1000)
        if new_level > current_level:
            current_level = new_level
            player.weapon_level = min(5, player.weapon_level + 1)
            floating_texts.append(FloatingText(player.rect.centerx, player.rect.centery - 60, f"LEVEL UP! WPN LVL {player.weapon_level}", YELLOW, "big"))
            screen_flash = 5

        if score > 5000 and not boss_spawned and not any(isinstance(e, Boss) for e in enemies):
            enemies.append(Boss(current_level, player.x))
            boss_spawned = True
            camera.shake(60, 5)
            floating_texts.append(FloatingText(WIDTH//2, HEIGHT//2, "WARNING: BOSS INCOMING", RED, "big"))

        enemy_spawn_timer += 1
        diff_params = DIFFICULTIES[selected_difficulty]
        spawn_rate = int(max(10, 40 - current_level * 2) * diff_params["spawn_mod"])

        if enemy_spawn_timer >= spawn_rate and not any(isinstance(e, Boss) for e in enemies):
            enemy_spawn_timer = 0
            roll = random.random()
            if roll < 0.2 and current_level > 1: enemies.append(TankEnemy(current_level, player.x))
            elif roll < 0.4 and current_level > 1: enemies.append(KamikazeEnemy(current_level, player.x, player.y))
            else: enemies.append(BasicEnemy(current_level, player.x))

        # Спавн пасхалки (Ложка)
        if random.random() < 0.0005: 
            spoons.append(Spoon(player.x))
        elif random.random() < 0.003: 
            powerups.append(PowerUp(player.x))

        for b in bullets[:]:
            b.update()
            if b.y < -100 or b.y > WORLD_HEIGHT + 100 or b.x < -100 or b.x > WORLD_WIDTH + 100: bullets.remove(b)

        for eb in enemy_bullets[:]:
            eb.update()
            if eb.y < -100 or eb.y > WORLD_HEIGHT + 100 or eb.x < -100 or eb.x > WORLD_WIDTH + 100:
                enemy_bullets.remove(eb)
            elif player.rect.colliderect(eb.rect) and player.take_damage():
                enemy_bullets.remove(eb)
                camera.shake(15, 10)
                screen_flash = 10
                hit_stop = 5
                if player.lives <= 0: game_state = "GAME_OVER"

        for e in enemies[:]:
            shoot_signal = e.update(player)
            
            if isinstance(e, (TankEnemy, Boss)) and shoot_signal:
                if isinstance(e, Boss):
                    for angle in range(-60, 61, 15):
                        rad = math.radians(angle + 90)
                        enemy_bullets.append(Bullet(e.rect.centerx, e.rect.centery, math.cos(rad)*7, math.sin(rad)*7, color=PURPLE))
                else:
                    enemy_bullets.append(EnemyBullet(e.rect.centerx, e.rect.centery, player.rect.centerx, player.rect.centery))

            if e.y > WORLD_HEIGHT or e.hp <= 0:
                if e.hp <= 0:
                    combo += 1
                    combo_timer = 120
                    points = e.score_value * combo
                    score += points
                    floating_texts.append(FloatingText(e.rect.centerx, e.rect.centery, f"+{points}", YELLOW))
                    
                    shockwaves.append(Shockwave(e.rect.centerx, e.rect.centery, ORANGE if not isinstance(e, Boss) else PURPLE, 100 if isinstance(e, Boss) else 50))
                    for _ in range(15 if not isinstance(e, Boss) else 50): particles.append(Particle(e.rect.centerx, e.rect.centery, ORANGE, speed=8))
                    
                    if isinstance(e, Boss):
                        screen_flash = 20
                        hit_stop = 15
                        camera.shake(40, 15)
                        boss_spawned = False
                        score += 5000 
                enemies.remove(e)
                continue

            if player.hero_type == "ANNIHILATOR" and player.aura_timer > 0:
                if math.hypot(e.rect.centerx - player.rect.centerx, e.rect.centery - player.rect.centery) < 150:
                    e.hp -= 1
                    e.hit_flash = 5
                    if e.hp <= 0:
                        combo += 1; combo_timer = 120
                        score += e.score_value * combo
                        shockwaves.append(Shockwave(e.rect.centerx, e.rect.centery, RED, 40))

            for b in bullets[:]:
                if e.rect.colliderect(b.rect):
                    e.hp -= 1
                    e.hit_flash = 5
                    if not b.piercing: bullets.remove(b)
                    if e.hp <= 0: break

            if e.rect.colliderect(player.rect) and player.take_damage():
                camera.shake(25, 12)
                screen_flash = 15
                hit_stop = 10
                for _ in range(20): particles.append(Particle(player.rect.centerx, player.rect.centery, RED))
                if not isinstance(e, Boss): enemies.remove(e)
                if player.lives <= 0: game_state = "GAME_OVER"

        # Обработка обычных бонусов
        for p in powerups[:]:
            p.update()
            if p.y > WORLD_HEIGHT: powerups.remove(p)
            elif player.rect.colliderect(p.rect):
                player.shield_active = True
                player.shield_timer = 400
                powerups.remove(p)
                floating_texts.append(FloatingText(player.rect.centerx, player.rect.centery, "SHIELD!", SHIELD_COLOR))

        # Обработка Ложки (Матрица)
        for sp in spoons[:]:
            sp.update()
            if sp.y > WORLD_HEIGHT: spoons.remove(sp)
            elif player.rect.colliderect(sp.rect):
                score += 1000
                spoons.remove(sp)
                screen_flash = 10
                global_texts.append(GlobalText("THERE IS NO SPOON", WHITE, "big"))
                floating_texts.append(FloatingText(player.rect.centerx, player.rect.centery, "+1000", CYAN, "big"))

        for p in particles[:]:
            p.update()
            if p.life <= 0: particles.remove(p)
        for s in shockwaves[:]:
            s.update()
            if s.life <= 0: shockwaves.remove(s)
        for ft in floating_texts[:]:
            ft.update()
            if ft.life <= 0: floating_texts.remove(ft)
        for gt in global_texts[:]:
            gt.update()
            if gt.life <= 0: global_texts.remove(gt)

    # ===================== ОТРИСОВКА =====================
    screen.fill(BLACK)
    
    if game_state == "MENU":
        for _ in range(50):
            x, y = random.randint(0, WIDTH), random.randint(0, HEIGHT)
            pygame.draw.circle(screen, WHITE, (x, y), random.randint(1, 2))
            
        title_txt = font_huge.render("OVERDRIVE", True, CYAN)
        screen.blit(title_txt, (WIDTH // 2 - title_txt.get_width() // 2, 50))

        hero_color = CYAN if selected_hero == "INTERCEPTOR" else RED
        hero_txt = font_medium.render(f"HERO: {selected_hero}", True, hero_color)
        screen.blit(hero_txt, (WIDTH // 2 - hero_txt.get_width() // 2, 200))

        desc = ["Q: Spread Shot", "W: Repair (Heal)", "E: EMP Blast", "R: Overdrive", "SHIFT: Dash"] if selected_hero == "INTERCEPTOR" else ["Q: Piercing Beam", "W: Reset Cooldowns", "E: Erase Aura", "R: Annihilation", "SHIFT: Dash"]
        for i, line in enumerate(desc):
            screen.blit(font_small.render(line, True, (200, 200, 200)), (WIDTH // 2 - 80, 250 + i * 25))

        diff_txt = font_medium.render(f"DIFFICULTY: {selected_difficulty}", True, DIFFICULTIES[selected_difficulty]["color"])
        screen.blit(diff_txt, (WIDTH // 2 - diff_txt.get_width() // 2, 420))

        screen.blit(font_small.render("UP/DOWN: Hero | LEFT/RIGHT: Difficulty", True, (150, 150, 150)), (WIDTH // 2 - 150, 470))
        
        pulse = math.sin(pygame.time.get_ticks() * 0.005) * 5
        start_txt = font_medium.render("PRESS SPACE TO START", True, WHITE)
        screen.blit(start_txt, (WIDTH // 2 - start_txt.get_width() // 2, 520 + pulse))

    elif game_state in ("PLAYING", "GAME_OVER"):
        off_x, off_y = camera.get_offset()
        
        screen.blit(world_surface, (-off_x, -off_y))
        
        for i in range(100):
            star_x = (i * 137 + int(off_x * 0.3)) % WIDTH
            star_y = (i * 251 + int(off_y * 0.3)) % HEIGHT
            pygame.draw.circle(screen, (150, 150, 150), (star_x, star_y), 1)

        for p in particles: p.draw(screen, off_x, off_y)
        for s in shockwaves: s.draw(screen, off_x, off_y)
        for p in powerups: p.draw(screen, off_x, off_y)
        for sp in spoons: sp.draw(screen, off_x, off_y)
        for e in enemies: e.draw(screen, off_x, off_y)
        for b in bullets: b.draw(screen, off_x, off_y)
        for eb in enemy_bullets: eb.draw(screen, off_x, off_y)
        for ft in floating_texts: ft.draw(screen, off_x, off_y)
        
        if game_state == "PLAYING":
            player.draw(screen, off_x, off_y, particles)

        if screen_flash > 0:
            flash_surf = pygame.Surface((WIDTH, HEIGHT))
            flash_surf.fill(WHITE)
            flash_surf.set_alpha(screen_flash * 10)
            screen.blit(flash_surf, (0, 0))
            screen_flash -= 1

        # Отрисовка пасхалок по центру экрана
        for gt in global_texts:
            gt.draw(screen)

        if game_state == "PLAYING":
            for i in range(player.max_lives):
                color = RED if i < player.lives else (50, 50, 50)
                pygame.draw.rect(screen, color, (15 + i * 25, 15, 20, 20), border_radius=5)
            
            score_txt = font_medium.render(f"SCORE: {score}", True, WHITE)
            level_txt = font_medium.render(f"WPN LVL: {player.weapon_level}", True, CYAN)
            screen.blit(score_txt, (WIDTH // 2 - 100, 15))
            screen.blit(level_txt, (WIDTH - 180, 15))

            if combo > 1:
                combo_txt = font_big.render(f"x{combo}", True, YELLOW)
                screen.blit(combo_txt, (WIDTH - 100, 50))
                pygame.draw.rect(screen, YELLOW, (WIDTH - 100, 90, 80 * (combo_timer/120), 5))

            abilities = [("Q", player.cd_q, 180, GREEN), ("W", player.cd_w, 900, CYAN), ("E", player.cd_e, 1200, PURPLE), ("R", player.cd_r, 600, YELLOW), ("SHIFT", player.dash_cd, CD_DASH, WHITE)]
            for i, (key, cd, max_cd, color) in enumerate(abilities):
                x, y = 15 + i * 70, HEIGHT - 40
                pygame.draw.rect(screen, (50, 50, 50), (x, y, 60, 15), border_radius=5)
                if cd > 0: pygame.draw.rect(screen, (100, 100, 100), (x, y, int(60 * (1 - cd/max_cd)), 15), border_radius=5)
                else: pygame.draw.rect(screen, color, (x, y, 60, 15), border_radius=5)
                screen.blit(font_small.render(key, True, WHITE), (x + 15, y - 20))

            for e in enemies:
                if isinstance(e, Boss):
                    pygame.draw.rect(screen, (50, 0, 0), (WIDTH//2 - 200, HEIGHT - 80, 400, 20), border_radius=10)
                    pygame.draw.rect(screen, RED, (WIDTH//2 - 200, HEIGHT - 80, int(400 * (e.hp/e.max_hp)), 20), border_radius=10)
                    screen.blit(font_small.render("BOSS", True, WHITE), (WIDTH//2 - 20, HEIGHT - 80))

        elif game_state == "GAME_OVER":
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 200))
            screen.blit(overlay, (0, 0))
            
            # ПАСХАЛКА: Dark Souls
            over_txt = font_huge.render("YOU DIED", True, DARK_RED)
            score_txt = font_medium.render(f"Final Score: {score}", True, WHITE)
            restart_txt = font_medium.render("Press R to Menu", True, WHITE)
            
            screen.blit(over_txt, (WIDTH // 2 - over_txt.get_width() // 2, HEIGHT // 2 - 100))
            screen.blit(score_txt, (WIDTH // 2 - score_txt.get_width() // 2, HEIGHT // 2 + 20))
            screen.blit(restart_txt, (WIDTH // 2 - restart_txt.get_width() // 2, HEIGHT // 2 + 80))
    
    pygame.display.flip()

pygame.quit()
sys.exit()