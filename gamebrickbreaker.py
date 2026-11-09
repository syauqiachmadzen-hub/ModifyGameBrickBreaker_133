import io
import math
import os
import random
import struct
import wave
import pygame

# Inisialisasi Pygame & Mixer secara aman
pygame.init()
try:
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
except Exception:
    pass

# Dimensi Layar
WIDTH, HEIGHT = 600, 500

# Palet Warna (Neon Arcade)
BG_DARK = (10, 12, 22)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (40, 240, 120)
RED = (255, 60, 90)
ORANGE = (255, 160, 20)
CYAN = (0, 230, 255)
MAGENTA = (245, 60, 230)
YELLOW = (255, 225, 40)
GRAY = (120, 130, 140)

COLORS = [WHITE, GREEN, RED, ORANGE, CYAN, MAGENTA, YELLOW]

# Font
font = pygame.font.Font(None, 24)
title_font_base = 56
big_font = pygame.font.Font(None, 46)
hint_font = pygame.font.Font(None, 20)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Block Breaker - Deluxe Edition")
clock = pygame.time.Clock()
FPS = 60


# ==========================================================
# PROCEDURAL SOUND MANAGER (SFX Otomatis tanpa file eksternal)
# ==========================================================
class SoundManager:
    """Menghasilkan audio arcade retro langsung di memori RAM."""

    def __init__(self):
        self.sample_rate = 22050
        self.sounds = {}
        self.game_over_sound = None
        self.has_mixer = pygame.mixer.get_init() is not None

        if self.has_mixer:
            self._generate_arcade_sounds()
            self._load_external_audio()

    def _make_sound(self, duration, sample_fn):
        try:
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self.sample_rate)
                n = int(self.sample_rate * duration)
                data = bytearray()
                for i in range(n):
                    t = i / self.sample_rate
                    val = sample_fn(t, i, n)
                    val = max(-32767, min(32767, int(val * 32767)))
                    data.extend(struct.pack("<h", val))
                wf.writeframes(data)
            buf.seek(0)
            return pygame.mixer.Sound(buf)
        except Exception:
            return None

    def _generate_arcade_sounds(self):
        # 1. Paddle Bounce: rising sweep
        def paddle_wave(t, i, n):
            freq = 320 + 380 * (i / n)
            decay = max(0.0, 1.0 - (i / n))
            return math.sin(2 * math.pi * freq * t) * decay * 0.45

        self.sounds["paddle"] = self._make_sound(0.08, paddle_wave)

        # 2. Wall Bounce: short tick
        def wall_wave(t, i, n):
            freq = 240
            decay = max(0.0, 1.0 - (i / n)) ** 2
            return math.sin(2 * math.pi * freq * t) * decay * 0.35

        self.sounds["wall"] = self._make_sound(0.05, wall_wave)

        # 3. Block Hit: bright chime
        def block_hit_wave(t, i, n):
            freq = 650 + 150 * (i / n)
            decay = max(0.0, 1.0 - (i / n)) ** 1.5
            return math.sin(2 * math.pi * freq * t) * decay * 0.4

        self.sounds["block_hit"] = self._make_sound(0.07, block_hit_wave)

        # 4. Block Break: double chime sparkle
        def block_break_wave(t, i, n):
            half = n // 2
            freq = 780 if i < half else 1040
            decay = max(0.0, 1.0 - (i / n))
            s = 0.5 * (1.0 if math.sin(2 * math.pi * freq * t) > 0 else -1.0)
            s += 0.5 * math.sin(2 * math.pi * freq * 1.5 * t)
            return s * decay * 0.4

        self.sounds["block_break"] = self._make_sound(0.14, block_break_wave)

        # 5. Life Lost: descending low tone
        def life_lost_wave(t, i, n):
            freq = max(100, 360 - 240 * (i / n))
            decay = max(0.0, 1.0 - (i / n))
            s = 0.7 if math.sin(2 * math.pi * freq * t) > 0 else -0.7
            return s * decay * 0.45

        self.sounds["life_lost"] = self._make_sound(0.35, life_lost_wave)

        # 6. Game Start Jingle: 4-note ascending fanfare
        def start_jingle_wave(t, i, n):
            notes = [261.63, 329.63, 392.00, 523.25]
            note_idx = min(int((i / n) * len(notes)), len(notes) - 1)
            f = notes[note_idx]
            sub_t = t - (note_idx * (0.4 / len(notes)))
            decay = max(0.0, 1.0 - (sub_t / (0.4 / len(notes)))) ** 1.2
            return math.sin(2 * math.pi * f * sub_t) * decay * 0.35

        self.sounds["game_start"] = self._make_sound(0.4, start_jingle_wave)

        # 7. Game Over Jingle: classic descending defeat melody
        def game_over_wave(t, i, n):
            notes = [311.13, 293.66, 261.63, 196.00]  # Eb4, D4, C4, G3
            note_idx = min(int((i / n) * len(notes)), len(notes) - 1)
            f = notes[note_idx]
            sub_t = t - (note_idx * (1.1 / len(notes)))
            decay = max(0.0, 1.0 - (sub_t / (1.1 / len(notes)))) ** 1.3
            sq = 0.5 if math.sin(2 * math.pi * f * sub_t) > 0 else -0.5
            si = math.sin(2 * math.pi * f * sub_t) * 0.4
            return (sq + si) * decay * 0.4

        self.sounds["game_over_synth"] = self._make_sound(1.1, game_over_wave)

    def _load_external_audio(self):
        try:
            if os.path.exists("bgm.mp3"):
                pygame.mixer.music.load("bgm.mp3")
                pygame.mixer.music.set_volume(0.4)
                pygame.mixer.music.play(-1)
        except Exception:
            pass

        try:
            if os.path.exists("gameover.wav"):
                self.game_over_sound = pygame.mixer.Sound("gameover.wav")
        except Exception:
            self.game_over_sound = None

    def play(self, key):
        if not self.has_mixer:
            return
        sound = self.sounds.get(key)
        if sound:
            try:
                sound.play()
            except Exception:
                pass

    def play_game_over(self):
        if not self.has_mixer:
            return
        if self.game_over_sound:
            try:
                self.game_over_sound.play()
                return
            except Exception:
                pass
        self.play("game_over_synth")

    def stop_game_over(self):
        if self.game_over_sound:
            try:
                self.game_over_sound.stop()
            except Exception:
                pass


audio = SoundManager()


# ==========================================================
# EFEK PARTIKEL & VISUAL
# ==========================================================
class Particle:
    """Percikan partikel saat tabrakan"""

    def __init__(self, x, y, color, speed_mult=1.0):
        self.x = x
        self.y = y
        self.color = color
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(1.5, 4.5) * speed_mult
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = random.randint(14, 26)
        self.max_life = self.life
        self.radius = random.uniform(2.0, 4.0)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.1
        self.life -= 1

    def display(self, surface):
        if self.life > 0:
            alpha = int(255 * (self.life / self.max_life))
            current_r = max(1.0, self.radius * (self.life / self.max_life))
            glow_surf = pygame.Surface(
                (int(current_r * 4), int(current_r * 4)), pygame.SRCALPHA
            )
            pygame.draw.circle(
                glow_surf,
                (*self.color[:3], alpha),
                (int(current_r * 2), int(current_r * 2)),
                int(current_r),
            )
            surface.blit(
                glow_surf, (self.x - current_r * 2, self.y - current_r * 2)
            )


class FloatingText:
    """Teks skor melayang (+5) saat balok hancur"""

    def __init__(self, x, y, text, color=WHITE):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.life = 35
        self.max_life = 35

    def update(self):
        self.y -= 0.9
        self.life -= 1

    def display(self, surface):
        if self.life > 0:
            alpha = int(255 * (self.life / self.max_life))
            txt_surf = font.render(self.text, True, self.color)
            txt_surf.set_alpha(alpha)
            surface.blit(
                txt_surf, (self.x - txt_surf.get_width() // 2, self.y)
            )


class BackgroundStars:
    """Latar belakang bintang bergerak memberi efek kedalaman visual"""

    def __init__(self, count=45):
        self.stars = []
        for _ in range(count):
            self.stars.append([
                random.uniform(0, WIDTH),
                random.uniform(0, HEIGHT),
                random.uniform(0.3, 1.2),
                random.choice([CYAN, MAGENTA, WHITE, YELLOW]),
                random.uniform(1.0, 2.2),
            ])

    def update(self):
        for star in self.stars:
            star[1] -= star[2]
            if star[1] < 0:
                star[1] = HEIGHT
                star[0] = random.uniform(0, WIDTH)

    def display(self, surface):
        for star in self.stars:
            pygame.draw.circle(
                surface, star[3], (int(star[0]), int(star[1])), int(star[4])
            )


# ==========================================================
# ENTITAS GAME
# ==========================================================
class Striker:
    """Paddle dengan animasi masuk meluncur halus"""

    def __init__(self, posx, posy, width, height, speed, color):
        self.target_y = posy
        self.posx = posx
        self.posy = HEIGHT + 40  # Mulai di luar layar untuk animasi masuk
        self.width = width
        self.height = height
        self.speed = speed
        self.color = color
        self.strikerRect = pygame.Rect(posx, posy, width, height)

    def update_entrance(self, progress):
        t = max(0.0, min(1.0, progress))
        ease = 1.0 - (1.0 - t) ** 3
        self.posy = (HEIGHT + 40) + (self.target_y - (HEIGHT + 40)) * ease
        self.strikerRect.topleft = (int(self.posx), int(self.posy))

    def update(self, xFac):
        self.posx += self.speed * xFac
        if self.posx <= 0:
            self.posx = 0
        elif self.posx + self.width >= WIDTH:
            self.posx = WIDTH - self.width
        self.strikerRect.topleft = (int(self.posx), int(self.posy))

    def display(self):
        pygame.draw.rect(
            screen, (40, 50, 70), self.strikerRect, border_radius=6
        )
        inner_rect = self.strikerRect.inflate(-4, -4)
        pygame.draw.rect(screen, self.color, inner_rect, border_radius=4)
        shine_rect = pygame.Rect(
            self.strikerRect.x + 8, self.strikerRect.y + 2, self.width - 16, 2
        )
        pygame.draw.rect(screen, WHITE, shine_rect, border_radius=1)

    def getRect(self):
        return self.strikerRect


class Block:
    """Balok dengan animasi masuk air terjun (cascading) dan efek retak"""

    def __init__(self, posx, posy, width, height, color, cascade_delay=0.0):
        self.target_x = posx
        self.target_y = posy
        self.cascade_delay = cascade_delay
        self.width = width
        self.height = height
        self.color = color
        self.damage = 100

        if color == WHITE:
            self.health = 200
        else:
            self.health = 100

        self.posx = posx
        self.posy = -60
        self.blockRect = pygame.Rect(posx, self.posy, width, height)
        self.hit_flash = 0

    def update_entrance(self, elapsed_time):
        t = elapsed_time - self.cascade_delay
        if t <= 0:
            self.posy = -60
        else:
            duration = 0.55
            progress = min(1.0, t / duration)
            c1 = 1.70158
            c3 = c1 + 1
            ease = 1 + c3 * ((progress - 1) ** 3) + c1 * ((progress - 1) ** 2)
            ease = min(1.05, max(0.0, ease))
            self.posy = -60 + (self.target_y - (-60)) * ease

        self.blockRect.topleft = (int(self.posx), int(self.posy))

    def display(self):
        if self.health > 0:
            draw_color = WHITE if self.hit_flash > 0 else self.color
            if self.health < 200 and self.color == WHITE and self.hit_flash == 0:
                draw_color = GRAY

            if self.hit_flash > 0:
                self.hit_flash -= 1

            pygame.draw.rect(
                screen, draw_color, self.blockRect, border_radius=3
            )
            inner = self.blockRect.inflate(-4, -4)
            dark_tint = tuple(max(0, c - 45) for c in draw_color)
            pygame.draw.rect(screen, dark_tint, inner, border_radius=2)

            if self.health < 200 and self.color == WHITE:
                cx, cy = self.blockRect.center
                pygame.draw.line(
                    screen, RED, (cx - 8, cy - 3), (cx + 8, cy + 3), 2
                )

    def hit(self):
        self.health -= self.damage
        self.hit_flash = 4

    def getRect(self):
        return self.blockRect

    def getHealth(self):
        return self.health


class Ball:
    """Bola dengan jejak ekor cahaya (trail), squash & stretch, dan pendaran halo"""

    def __init__(self, posx, posy, radius, speed, color):
        self.startx = posx
        self.starty = posy
        self.posx = posx
        self.posy = posy
        self.radius = radius
        self.speed = speed
        self.color = color

        self.xFac = 1.0
        self.yFac = -1.0

        self.scale_x = 1.0
        self.scale_y = 1.0

        self.trail = []
        self.max_trail = 9
        self.docked = True

        self.ballRect = pygame.Rect(
            posx - radius, posy - radius, radius * 2, radius * 2
        )

    def dock_to_striker(self, striker):
        self.docked = True
        self.posx = striker.posx + striker.width // 2
        self.posy = striker.posy - self.radius - 2
        self.ballRect.center = (int(self.posx), int(self.posy))
        self.trail.clear()

    def launch(self, striker_x_fac=0):
        if self.docked:
            self.docked = False
            self.yFac = -1.0
            if striker_x_fac != 0:
                self.xFac = 1.0 if striker_x_fac > 0 else -1.0
            else:
                self.xFac = random.choice([-1.0, 1.0])
            audio.play("paddle")

    def trigger_squash(self, horizontal=False):
        if horizontal:
            self.scale_x = 0.65
            self.scale_y = 1.45
        else:
            self.scale_x = 1.45
            self.scale_y = 0.65

    def update(self):
        if self.docked:
            return False

        # Tambahkan jejak cahaya
        self.trail.append((self.posx, self.posy))
        if len(self.trail) > self.max_trail:
            self.trail.pop(0)

        # Pulihkan bentuk bola secara elastis
        self.scale_x += (1.0 - self.scale_x) * 0.22
        self.scale_y += (1.0 - self.scale_y) * 0.22

        self.posx += self.xFac * self.speed
        self.posy += self.yFac * self.speed

        if self.posx - self.radius <= 0:
            self.posx = self.radius
            self.xFac *= -1
            self.trigger_squash(horizontal=True)
            audio.play("wall")
        elif self.posx + self.radius >= WIDTH:
            self.posx = WIDTH - self.radius
            self.xFac *= -1
            self.trigger_squash(horizontal=True)
            audio.play("wall")

        if self.posy - self.radius <= 0:
            self.posy = self.radius
            self.yFac *= -1
            self.trigger_squash(horizontal=False)
            audio.play("wall")

        self.ballRect.center = (int(self.posx), int(self.posy))

        if self.posy - self.radius >= HEIGHT:
            return True

        return False

    def display(self):
        # 1. Gambar Ekor Cahaya Komet
        if self.trail and not self.docked:
            trail_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            trail_len = len(self.trail)
            for idx, (tx, ty) in enumerate(self.trail):
                ratio = (idx + 1) / trail_len
                trail_alpha = int(140 * ratio)
                trail_r = max(2, int(self.radius * (0.4 + 0.6 * ratio)))
                trail_color = (*CYAN[:3], trail_alpha)
                pygame.draw.circle(
                    trail_surf, trail_color, (int(tx), int(ty)), trail_r
                )
            screen.blit(trail_surf, (0, 0))

        # 2. Gambar Outer Glow Halo
        glow_size = int(self.radius * 2.8)
        glow_surf = pygame.Surface(
            (glow_size * 2, glow_size * 2), pygame.SRCALPHA
        )
        pygame.draw.circle(
            glow_surf, (*CYAN[:3], 60), (glow_size, glow_size), glow_size
        )
        screen.blit(
            glow_surf, (int(self.posx - glow_size), int(self.posy - glow_size))
        )

        # 3. Gambar Bola dengan Squash & Stretch
        rx = max(2, int(self.radius * self.scale_x))
        ry = max(2, int(self.radius * self.scale_y))
        ball_surf = pygame.Surface((rx * 2 + 4, ry * 2 + 4), pygame.SRCALPHA)
        pygame.draw.ellipse(ball_surf, self.color, (2, 2, rx * 2, ry * 2))
        pygame.draw.ellipse(
            ball_surf,
            WHITE,
            (2 + rx // 3, 2 + ry // 4, max(2, rx // 2), max(2, ry // 2)),
        )
        screen.blit(
            ball_surf, (int(self.posx - rx - 2), int(self.posy - ry - 2))
        )

    def reset(self):
        self.posx = self.startx
        self.posy = self.starty
        self.xFac = 1.0
        self.yFac = -1.0
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.trail.clear()
        self.ballRect.center = (int(self.posx), int(self.posy))

    def hit(self, factor=None):
        self.yFac *= -1
        self.trigger_squash(horizontal=False)
        if factor is not None:
            self.xFac = factor

    def getRect(self):
        return self.ballRect


# ==========================================================
# FUNGSI BANTUAN
# ==========================================================
def collisionChecker(rect, ball):
    return rect.colliderect(ball)


def populateBlocks(blockWidth, blockHeight, horizontalGap, verticalGap):
    listOfBlocks = []
    col_idx = 0
    for i in range(10, WIDTH - blockWidth, blockWidth + horizontalGap):
        row_idx = 0
        for j in range(35, HEIGHT // 2, blockHeight + verticalGap):
            color = random.choice(COLORS)
            delay = (row_idx * 0.07) + (col_idx * 0.025)
            listOfBlocks.append(
                Block(i, j, blockWidth, blockHeight, color, cascade_delay=delay)
            )
            row_idx += 1
        col_idx += 1
    return listOfBlocks


def spawn_impact_sparks(particles, x, y, color, count=12, speed_mult=1.0):
    for _ in range(count):
        particles.append(Particle(x, y, color, speed_mult=speed_mult))


# ==========================================================
# SCREEN: WELCOME SCREEN (Animasi Intro Menarik)
# ==========================================================
def welcomeScreen():
    counter = 0.0
    stars = BackgroundStars(50)
    audio.play("game_start")

    while True:
        counter += 0.05
        screen.fill(BG_DARK)
        stars.update()
        stars.display(screen)

        bobbing = math.sin(counter) * 6
        scale_offset = int(math.sin(counter * 1.5) * 4)
        dynamic_font = pygame.font.Font(None, title_font_base + scale_offset)

        # Neon Glow Shadow
        shadow_text = dynamic_font.render(
            "BLOCK BREAKER", True, (20, 100, 150)
        )
        title_text = dynamic_font.render("BLOCK BREAKER", True, CYAN)
        center_x = WIDTH // 2
        center_y = HEIGHT // 2 - 80 + int(bobbing)

        screen.blit(
            shadow_text, shadow_text.get_rect(center=(center_x + 3, center_y + 3))
        )
        screen.blit(
            title_text, title_text.get_rect(center=(center_x, center_y))
        )

        badge = hint_font.render("--- ARCADE DELUXE ---", True, MAGENTA)
        screen.blit(badge, badge.get_rect(center=(center_x, center_y + 35)))

        pulse_alpha = int(160 + 95 * math.sin(counter * 4))
        start_text = big_font.render("Press SPACE to Start", True, WHITE)
        start_text.set_alpha(pulse_alpha)
        screen.blit(
            start_text,
            start_text.get_rect(center=(center_x, HEIGHT // 2 + 35)),
        )

        # Kartu Informasi Kontrol
        box_rect = pygame.Rect(center_x - 180, HEIGHT // 2 + 85, 360, 80)
        pygame.draw.rect(screen, (20, 26, 45), box_rect, border_radius=8)
        pygame.draw.rect(screen, (50, 70, 110), box_rect, 2, border_radius=8)

        ctrl1 = font.render("<-- / --> Arrow Keys : Move Paddle", True, GREEN)
        ctrl2 = font.render("SPACE : Launch Ball", True, YELLOW)
        ctrl3 = hint_font.render(
            "Destroy all blocks to win!", True, (170, 190, 210)
        )

        screen.blit(ctrl1, ctrl1.get_rect(center=(center_x, HEIGHT // 2 + 105)))
        screen.blit(ctrl2, ctrl2.get_rect(center=(center_x, HEIGHT // 2 + 130)))
        screen.blit(ctrl3, ctrl3.get_rect(center=(center_x, HEIGHT // 2 + 152)))

        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    audio.play("paddle")
                    return True
                if event.key == pygame.K_ESCAPE:
                    return False

        clock.tick(FPS)


# ==========================================================
# SCREEN: GAME OVER SCREEN (Animasi & SFX Game Over)
# ==========================================================
def gameOver(final_score):
    audio.play_game_over()
    counter = 0.0

    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((5, 7, 14, 210))
    screen.blit(overlay, (0, 0))

    while True:
        counter += 0.06
        screen.blit(overlay, (0, 0))

        scale_offset = int(math.sin(counter * 2) * 4)
        go_font = pygame.font.Font(None, 60 + scale_offset)

        shadow_go = go_font.render("GAME OVER", True, (120, 10, 20))
        text_go = go_font.render("GAME OVER", True, RED)

        cx, cy = WIDTH // 2, HEIGHT // 2 - 50
        screen.blit(shadow_go, shadow_go.get_rect(center=(cx + 3, cy + 3)))
        screen.blit(text_go, text_go.get_rect(center=(cx, cy)))

        score_surf = big_font.render(
            f"Final Score: {final_score}", True, YELLOW
        )
        screen.blit(score_surf, score_surf.get_rect(center=(cx, cy + 55)))

        pulse_alpha = int(170 + 85 * math.sin(counter * 3))
        restart_text = font.render(
            "Press SPACE to Restart  |  ESC to Exit", True, WHITE
        )
        restart_text.set_alpha(pulse_alpha)
        screen.blit(
            restart_text, restart_text.get_rect(center=(cx, cy + 105))
        )

        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                audio.stop_game_over()
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    audio.stop_game_over()
                    audio.play("game_start")
                    return True
                if event.key == pygame.K_ESCAPE:
                    audio.stop_game_over()
                    return False

        clock.tick(FPS)


# ==========================================================
# GAMEPLAY UTAMA
# ==========================================================
def main():
    if not welcomeScreen():
        return

    running = True
    lives = 3
    score = 0

    striker = Striker(250, HEIGHT - 50, 100, 15, 8, WHITE)
    strikerXFac = 0

    ball = Ball(300, HEIGHT - 100, 7, 5, WHITE)
    ball.dock_to_striker(striker)

    blockWidth = 40
    blockHeight = 15
    horizontalGap = 15
    verticalGap = 15

    listOfBlocks = populateBlocks(
        blockWidth, blockHeight, horizontalGap, verticalGap
    )

    particles = []
    floating_texts = []
    stars = BackgroundStars(35)

    entrance_timer = 0.0
    entrance_duration = 1.3
    in_entrance = True

    while running:
        dt = clock.tick(FPS) / 1000.0
        screen.fill(BG_DARK)

        # Update Animasi Masuk (Cascading Blocks & Paddle)
        if in_entrance:
            entrance_timer += dt
            striker.update_entrance(min(1.0, entrance_timer / 0.8))
            for block in listOfBlocks:
                block.update_entrance(entrance_timer)
            ball.dock_to_striker(striker)
            if entrance_timer >= entrance_duration:
                in_entrance = False

        # Input
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    strikerXFac = -1
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    strikerXFac = 1
                elif event.key in (pygame.K_SPACE, pygame.K_UP):
                    if ball.docked and not in_entrance:
                        ball.launch(strikerXFac)

            if event.type == pygame.KEYUP:
                if event.key in (pygame.K_LEFT, pygame.K_a) and strikerXFac < 0:
                    strikerXFac = 0
                elif event.key in (pygame.K_RIGHT, pygame.K_d) and strikerXFac > 0:
                    strikerXFac = 0

        # Gerakan objek
        if not in_entrance:
            striker.update(strikerXFac)

            if ball.docked:
                ball.dock_to_striker(striker)
                lifeLost = False
            else:
                lifeLost = ball.update()
        else:
            lifeLost = False

        # Tabrakan Striker dengan Kontrol Sudut Pantulan Dinamis
        if not ball.docked and collisionChecker(striker.getRect(), ball.getRect()):
            if ball.yFac > 0:
                offset = (ball.posx - (striker.posx + striker.width / 2)) / (
                    striker.width / 2
                )
                offset = max(-0.9, min(0.9, offset))
                ball.hit(factor=offset * 1.4)
                ball.trigger_squash(horizontal=False)
                audio.play("paddle")
                spawn_impact_sparks(
                    particles, ball.posx, ball.posy, CYAN, count=10
                )

        # Tabrakan Balok
        for block in listOfBlocks[:]:
            if collisionChecker(block.getRect(), ball.getRect()):
                ball.hit()
                block.hit()
                spawn_impact_sparks(
                    particles, ball.posx, ball.posy, block.color, count=12
                )

                if block.getHealth() <= 0:
                    audio.play("block_break")
                    listOfBlocks.remove(block)
                    score += 5
                    spawn_impact_sparks(
                        particles,
                        block.blockRect.centerx,
                        block.blockRect.centery,
                        block.color,
                        count=22,
                        speed_mult=1.3,
                    )
                    floating_texts.append(
                        FloatingText(
                            block.blockRect.centerx,
                            block.blockRect.centery,
                            "+5",
                            YELLOW,
                        )
                    )
                else:
                    audio.play("block_hit")
                break

        # Menangani Kehilangan Nyawa
        if lifeLost:
            lives -= 1
            audio.play("life_lost")
            spawn_impact_sparks(
                particles, ball.posx, HEIGHT - 10, RED, count=25
            )

            if lives <= 0:
                running = gameOver(score)
                if running:
                    lives = 3
                    score = 0
                    listOfBlocks = populateBlocks(
                        blockWidth, blockHeight, horizontalGap, verticalGap
                    )
                    striker.posx = 250
                    striker.posy = HEIGHT - 50
                    ball.dock_to_striker(striker)
                    entrance_timer = 0.0
                    in_entrance = True
            else:
                ball.dock_to_striker(striker)

        # Jika Semua Balok Hancur -> Wave Berikutnya dengan Animasi Masuk
        if not listOfBlocks:
            audio.play("game_start")
            listOfBlocks = populateBlocks(
                blockWidth, blockHeight, horizontalGap, verticalGap
            )
            ball.dock_to_striker(striker)
            entrance_timer = 0.0
            in_entrance = True

        # Render Partikel & Efek
        stars.update()
        stars.display(screen)

        for p in particles[:]:
            p.update()
            p.display(screen)
            if p.life <= 0:
                particles.remove(p)

        for ft in floating_texts[:]:
            ft.update()
            ft.display(screen)
            if ft.life <= 0:
                floating_texts.remove(ft)

        # Render Balok, Pemukul & Bola
        for block in listOfBlocks:
            block.display()

        striker.display()
        ball.display()

        # Render Banner READY atau Petunjuk Luncurkan Bola
        if in_entrance:
            ready_txt = big_font.render("READY...", True, YELLOW)
            screen.blit(
                ready_txt,
                ready_txt.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 40)),
            )
        elif ball.docked:
            pulse = int(180 + 75 * math.sin(pygame.time.get_ticks() * 0.008))
            launch_hint = hint_font.render(
                "Press SPACE or UP to Launch Ball", True, WHITE
            )
            launch_hint.set_alpha(pulse)
            screen.blit(
                launch_hint,
                launch_hint.get_rect(center=(WIDTH // 2, HEIGHT - 75)),
            )

        # UI Bar Skor & Nyawa
        scoreText = font.render(f"Score: {score}", True, WHITE)
        livesText = font.render(
            f"Lives: {lives}", True, GREEN if lives > 1 else RED
        )

        hud_bar = pygame.Surface((WIDTH, 28), pygame.SRCALPHA)
        hud_bar.fill((15, 20, 32, 180))
        screen.blit(hud_bar, (0, HEIGHT - 28))

        screen.blit(scoreText, (15, HEIGHT - 23))
        screen.blit(livesText, (140, HEIGHT - 23))

        pygame.display.update()

if __name__ == "__main__":
    main()
    pygame.quit()