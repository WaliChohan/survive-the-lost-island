import os
import math
import random
from array import array

import pygame

pygame.init()


# ============================================================
# SCREEN / GAME WORLD
# ============================================================

GAME_WIDTH = 1200
GAME_HEIGHT = 700

screen = pygame.display.set_mode(
    (GAME_WIDTH, GAME_HEIGHT),
    pygame.RESIZABLE
)

pygame.display.set_caption("Survive: The Lost Island")

clock = pygame.time.Clock()

# Fullscreen state
fullscreen = False

# Remember the last windowed size
windowed_size = (GAME_WIDTH, GAME_HEIGHT)


# ============================================================
# GAME SURFACE
# ============================================================

# The game ALWAYS runs internally at 1200 x 700.
# The display can be resized/fullscreen without changing
# world coordinates or collision calculations.

game_surface = pygame.Surface(
    (GAME_WIDTH, GAME_HEIGHT)
)


# ============================================================
# ASSET LOADING
# ============================================================

def load_asset(filename, fallback_size=(64, 64), fallback_color=(160, 160, 160, 255)):
    """Load an asset from the script's aset folder or use a visible fallback."""

    search_paths = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "aset", filename),
        os.path.join("aset", filename),
        filename,
    ]

    for path in search_paths:
        if os.path.exists(path):
            return pygame.image.load(path).convert_alpha()

    fallback = pygame.Surface(fallback_size, pygame.SRCALPHA)
    fallback.fill(fallback_color)
    pygame.draw.rect(
        fallback,
        (255, 255, 255, 180),
        fallback.get_rect(),
        2,
    )
    return fallback


# ============================================================
# SOUND EFFECTS
# ============================================================

try:
    if pygame.mixer.get_init() is None:
        pygame.mixer.init(
            frequency=44100,
            size=-16,
            channels=1,
            buffer=512,
        )
    SOUND_ENABLED = pygame.mixer.get_init() is not None
except Exception:
    # Covers pygame.error and systems where the mixer module is unavailable.
    # The game stays fully playable without audio.
    SOUND_ENABLED = False


def create_generated_sound(effect_name):
    """Create lightweight fallback effects when WAV files are unavailable."""

    if not SOUND_ENABLED:
        return None

    sample_rate = 44100
    effect_settings = {
        "attack": (0.08, 520, 0.20),
        "hit": (0.07, 145, 0.24),
        "enemy_attack": (0.12, 85, 0.24),
        "pickup": (0.13, 760, 0.20),
        "heal": (0.24, 620, 0.20),
        "fahh": (0.48, 180, 0.34),
    }
    duration, base_frequency, volume = effect_settings[effect_name]
    samples = array("h")

    for index in range(int(sample_rate * duration)):
        time_value = index / sample_rate
        progress = time_value / duration
        attack_fade = min(1.0, time_value / 0.015)
        release_fade = max(0.0, 1.0 - (progress * 1.15))
        envelope = attack_fade * release_fade

        if effect_name == "fahh":
            falling_frequency = base_frequency - 75 * progress
            waveform = (
                math.sin(2 * math.pi * falling_frequency * time_value)
                + 0.45 * math.sin(
                    2 * math.pi * falling_frequency * 2 * time_value
                )
                + 0.18 * math.sin(
                    2 * math.pi * falling_frequency * 4 * time_value
                )
            )
        else:
            frequency = base_frequency
            if effect_name == "pickup":
                frequency += 260 * progress
            elif effect_name == "heal":
                frequency += 180 * progress
            waveform = math.sin(2 * math.pi * frequency * time_value)

        sample = int(
            32767
            * volume
            * envelope
            * max(-1.0, min(1.0, waveform / 1.5))
        )
        samples.append(sample)

    return pygame.mixer.Sound(buffer=samples.tobytes())


def load_sound(filename, fallback_effect):
    if not SOUND_ENABLED:
        return None

    search_paths = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "aset", filename),
        os.path.join("aset", filename),
        filename,
    ]
    for path in search_paths:
        if os.path.exists(path):
            try:
                return pygame.mixer.Sound(path)
            except pygame.error:
                break

    return create_generated_sound(fallback_effect)


sound_effects = {
    "attack": load_sound("attack.wav", "attack"),
    "hit": load_sound("hit.wav", "hit"),
    "enemy_attack": load_sound("enemy_attack.wav", "enemy_attack"),
    "pickup": load_sound("pickup.wav", "pickup"),
    "heal": load_sound("heal.wav", "heal"),
    # If aset/fahh.wav is supplied, it is used. Otherwise a generated
    # falling vocal-like "FAHH" effect is used.
    "enemy_death": load_sound("fahh.wav", "fahh"),
}


def play_sound(effect_name):
    sound = sound_effects.get(effect_name)
    if sound is not None:
        sound.play()


# ============================================================
# BACKGROUND MUSIC
# ============================================================

# Drop any of these files into the "aset" folder to enable music.
# No gameplay code needs to change when a track is added.

MUSIC_FILENAMES = (
    "music.ogg",
    "music.mp3",
    "music.wav",
    "background.ogg",
    "background.mp3",
)

MUSIC_VOLUME = 0.35


def find_music_file():
    if not SOUND_ENABLED:
        return None

    base_folder = os.path.dirname(os.path.abspath(__file__))
    for filename in MUSIC_FILENAMES:
        for path in (
            os.path.join(base_folder, "aset", filename),
            os.path.join("aset", filename),
            filename,
        ):
            if os.path.exists(path):
                return path
    return None


music_path = find_music_file()
music_available = False

if music_path is not None:
    try:
        pygame.mixer.music.load(music_path)
        pygame.mixer.music.set_volume(MUSIC_VOLUME)
        music_available = True
    except pygame.error:
        music_available = False

music_playing = False


def start_music():
    """Start the looping gameplay track once for the current run."""

    global music_playing

    if not music_available or music_playing:
        return

    try:
        pygame.mixer.music.set_volume(MUSIC_VOLUME)
        pygame.mixer.music.play(-1)
        music_playing = True
    except pygame.error:
        music_playing = False


def stop_music(fade_ms=600):
    global music_playing

    if not music_available or not music_playing:
        music_playing = False
        return

    try:
        pygame.mixer.music.fadeout(max(0, fade_ms))
    except pygame.error:
        pass

    music_playing = False


def pause_music():
    if music_available and music_playing:
        try:
            pygame.mixer.music.pause()
        except pygame.error:
            pass


def resume_music():
    if music_available and music_playing:
        try:
            pygame.mixer.music.unpause()
        except pygame.error:
            pass


# ============================================================
# DIFFICULTY / ENEMY WAVES
# ============================================================

# Each tuple contains the number of enemies in each wave. Keeping this
# data-driven makes the wave rules explicit and prevents accidental
# duplicate spawns when the difficulty changes.
DIFFICULTY_WAVES = {
    "EASY": (3,),
    "MEDIUM": (3, 2),
    "HARD": (3, 3, 4),
}

selected_difficulty = "EASY"
current_wave = 1
total_waves = len(DIFFICULTY_WAVES[selected_difficulty])
wave_defeated = 0
wave_banner_timer = 0.0
screen_fade_alpha = 0
game_over_fade_alpha = 0


# ============================================================
# PARTICLE EFFECTS (death / pickup feedback)
# ============================================================

class Particle:

    def __init__(self, x, y, color, speed=140, life=0.45, size=5, gravity=90):
        angle = random.uniform(0, math.tau)
        velocity = random.uniform(speed * 0.35, speed)
        self.x = float(x)
        self.y = float(y)
        self.vx = math.cos(angle) * velocity
        self.vy = math.sin(angle) * velocity
        self.color = color
        self.life = life
        self.max_life = life
        self.size = size
        self.gravity = gravity

    def update(self, dt):
        self.life -= dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += self.gravity * dt
        self.vx *= 0.96
        return self.life > 0

    def draw(self, surface):
        progress = max(0.0, self.life / self.max_life)
        radius = max(1, int(self.size * progress))
        alpha = int(235 * progress)
        blob = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(
            blob,
            (*self.color, alpha),
            (radius, radius),
            radius,
        )
        surface.blit(blob, (int(self.x) - radius, int(self.y) - radius))


class FloatingText:

    def __init__(self, x, y, text, color):
        self.x = float(x)
        self.y = float(y)
        self.text = text
        self.color = color
        self.life = 0.9
        self.max_life = 0.9

    def update(self, dt):
        self.life -= dt
        self.y -= 34 * dt
        return self.life > 0

    def draw(self, surface):
        progress = max(0.0, self.life / self.max_life)
        font = pygame.font.Font(None, 26)
        label = font.render(self.text, True, self.color)
        label.set_alpha(int(255 * progress))
        surface.blit(label, label.get_rect(center=(int(self.x), int(self.y))))


particles = []
floating_texts = []


def spawn_particles(x, y, color, amount=12, speed=150, life=0.45, size=5, gravity=90):
    for _ in range(amount):
        particles.append(
            Particle(x, y, color, speed=speed, life=life, size=size, gravity=gravity)
        )


def spawn_floating_text(x, y, text, color=(255, 245, 210)):
    floating_texts.append(FloatingText(x, y, text, color))


def update_effects(dt):
    particles[:] = [p for p in particles if p.update(dt)]
    floating_texts[:] = [t for t in floating_texts if t.update(dt)]


def draw_effects(surface):
    for particle in particles:
        particle.draw(surface)
    for text in floating_texts:
        text.draw(surface)


def clear_effects():
    particles.clear()
    floating_texts.clear()


# ============================================================
# WINDOW -> GAME COORDINATE CONVERSION
# ============================================================

def window_to_game_position(position):
    """Convert a real window position into internal 1200x700 coordinates."""

    display_surface = pygame.display.get_surface()
    if display_surface is None:
        return position

    window_width, window_height = display_surface.get_size()
    scale = min(
        window_width / GAME_WIDTH,
        window_height / GAME_HEIGHT,
    )
    scale = max(scale, 0.001)

    scaled_width = int(GAME_WIDTH * scale)
    scaled_height = int(GAME_HEIGHT * scale)
    offset_x = (window_width - scaled_width) // 2
    offset_y = (window_height - scaled_height) // 2

    return (
        int((position[0] - offset_x) / scale),
        int((position[1] - offset_y) / scale),
    )


def get_game_mouse_position():
    return window_to_game_position(pygame.mouse.get_pos())


def draw_ui_button(surface, rect, label, base_color, hover_color, font, hovered):
    shadow = pygame.Rect(rect.x, rect.y + 4, rect.width, rect.height)
    pygame.draw.rect(surface, (0, 0, 0, 120), shadow, border_radius=12)
    pygame.draw.rect(
        surface,
        hover_color if hovered else base_color,
        rect,
        border_radius=12,
    )
    pygame.draw.rect(
        surface,
        (255, 255, 255) if hovered else (225, 225, 225),
        rect,
        3 if hovered else 2,
        border_radius=12,
    )
    label_surface = font.render(label, True, (255, 255, 255))
    surface.blit(
        label_surface,
        label_surface.get_rect(center=rect.center),
    )


# ============================================================
# ISLAND SHAPE
# ============================================================

# ---------------- OUTER BEACH ----------------

beach_points = [

    (60, 180),
    (150, 90),
    (350, 65),
    (600, 70),
    (850, 65),
    (1050, 100),
    (1140, 180),

    (1170, 300),
    (1160, 430),

    (1100, 540),
    (1000, 620),
    (800, 650),

    (600, 640),
    (400, 650),
    (220, 620),

    (100, 540),
    (50, 420),
    (45, 280)
]


# ---------------- INNER GRASS ----------------

grass_points = [

    (120, 190),
    (200, 130),
    (370, 110),
    (600, 115),
    (830, 110),
    (1010, 140),
    (1090, 210),

    (1120, 310),
    (1110, 410),

    (1050, 500),
    (960, 570),
    (790, 610),

    (600, 600),
    (410, 610),
    (250, 580),

    (140, 510),
    (100, 410),
    (95, 290)
]


# ============================================================
# BEACH / ISLAND BOUNDARY CHECK
# ============================================================

def point_inside_island(point):

    x, y = point

    inside = False

    j = len(beach_points) - 1

    for i in range(len(beach_points)):

        xi, yi = beach_points[i]
        xj, yj = beach_points[j]

        if ((yi > y) != (yj > y)) and \
           (x < (xj - xi) * (y - yi) / (yj - yi) + xi):

            inside = not inside

        j = i

    return inside

# ============================================================
# SPRITE SHEET
# ============================================================

sprite_sheet = load_asset(
    "player.png",
    fallback_size=(400, 400),
    fallback_color=(70, 150, 220, 255),
)

columns = 4
rows = 4

sheet_width = sprite_sheet.get_width()
sheet_height = sprite_sheet.get_height()

frame_width = sheet_width // columns
frame_height = sheet_height // rows


# ============================================================
# PLAYER ANIMATIONS
# ============================================================

animations = {
    "down": [],
    "right": [],
    "left": [],
    "up": []
}


# ============================================================
# EXTRACT PLAYER FRAMES
# ============================================================

for row in range(rows):

    for column in range(columns):

        frame = sprite_sheet.subsurface(
            pygame.Rect(
                column * frame_width,
                row * frame_height,
                frame_width,
                frame_height
            )
        )

        frame = pygame.transform.scale(
            frame,
            (100, 100)
        )

        # ---------------- ROW MAPPING ----------------

        if row == 0:

            animations["down"].append(frame)

        elif row == 1:

            animations["right"].append(frame)

        elif row == 2:

            animations["left"].append(frame)

        elif row == 3:

            animations["up"].append(frame)


# ============================================================
# ENEMY SPRITE SHEET
# ============================================================

enemy_sheet = load_asset(
    "enemy.png",
    fallback_size=(400, 400),
    fallback_color=(190, 70, 70, 255),
)

enemy_animations = {
    "down": [],
    "right": [],
    "left": [],
    "up": [],
}

enemy_frame_width = max(1, enemy_sheet.get_width() // columns)
enemy_frame_height = max(1, enemy_sheet.get_height() // rows)

for row in range(rows):
    for column in range(columns):
        enemy_frame = enemy_sheet.subsurface(
            pygame.Rect(
                column * enemy_frame_width,
                row * enemy_frame_height,
                enemy_frame_width,
                enemy_frame_height,
            )
        ).copy()
        enemy_frame = pygame.transform.scale(enemy_frame, (90, 90))

        if row == 0:
            enemy_animations["down"].append(enemy_frame)
        elif row == 1:
            enemy_animations["right"].append(enemy_frame)
        elif row == 2:
            enemy_animations["left"].append(enemy_frame)
        else:
            enemy_animations["up"].append(enemy_frame)


# ============================================================
# APPLE IMAGE
# ============================================================

apple_image = load_asset(
    "apple.png",
    fallback_size=(40, 40),
    fallback_color=(220, 45, 45, 255),
)


# ============================================================
# ENVIRONMENT IMAGES
# ============================================================

tree_image = load_asset("tree.png")

tree2_image = load_asset("tree 2.png")

tree3_image = load_asset("tree 3.png")

tree4_image = load_asset("tree 4.png")

rock_image = load_asset("rock.png")

# ============================================================
# WEAPON IMAGES
# ============================================================

knife_image = load_asset("knife.png")

sword_image = load_asset("sword.png")

spear_image = load_asset("spear.png")


# ============================================================
# BEACH IMAGE
# ============================================================

beach_image = load_asset("beach.png")


# ============================================================
# GRASS IMAGE
# ============================================================

grass_image = load_asset("grass.png")


# ============================================================
# WATER ANIMATION
# ============================================================

water_sheet = load_asset(
    "water.png",
    fallback_size=(500, 100),
    fallback_color=(40, 120, 200, 255),
).convert()

water_columns = 5

water_width = water_sheet.get_width()
water_height = water_sheet.get_height()

water_frame_width = (
    water_width // water_columns
)

water_frames = []

for i in range(water_columns):

    frame = water_sheet.subsurface(

        pygame.Rect(

            i * water_frame_width,
            0,
            water_frame_width,
            water_height

        )

    )

    water_frames.append(frame)


water_current_frame = 0

water_animation_timer = 0

water_animation_speed = 0.15


# ============================================================
# TEXTURE PREPARATION
# ============================================================

def crop_transparent_area(image):

    """
    Removes completely transparent space around an image.

    This is particularly useful for beach.png because
    the actual sand occupies only part of the image.
    """

    bounding_rect = image.get_bounding_rect(
        min_alpha=1
    )

    if bounding_rect.width == 0 or bounding_rect.height == 0:

        return image

    return image.subsurface(
        bounding_rect
    ).copy()


# ---------------- BEACH TEXTURE ----------------

# Your beach image contains a large transparent area.
# Crop it so we only tile the actual beach/sand portion.

beach_texture = crop_transparent_area(
    beach_image
)


# Make the beach texture smaller while preserving
# its original aspect ratio.

beach_target_width = min(
    360,
    GAME_WIDTH // 3
)

beach_scale = (
    beach_target_width /
    beach_texture.get_width()
)

beach_target_height = max(
    1,
    int(
        beach_texture.get_height()
        * beach_scale
    )
)

beach_texture = pygame.transform.smoothscale(
    beach_texture,
    (
        beach_target_width,
        beach_target_height
    )
)


# ============================================================
# TEXTURE MASK HELPER
# ============================================================

def create_polygon_mask(points):

    mask_surface = pygame.Surface(
        (GAME_WIDTH, GAME_HEIGHT),
        pygame.SRCALPHA
    )

    pygame.draw.polygon(
        mask_surface,
        (255, 255, 255, 255),
        points
    )

    return mask_surface


def create_tiled_texture(
    texture,
    points
):

    """
    Creates a tiled texture and clips it to
    the supplied polygon.
    """

    texture_surface = pygame.Surface(
        (GAME_WIDTH, GAME_HEIGHT),
        pygame.SRCALPHA
    )

    texture_width = texture.get_width()
    texture_height = texture.get_height()

    for x in range(
        0,
        GAME_WIDTH,
        texture_width
    ):

        for y in range(
            0,
            GAME_HEIGHT,
            texture_height
        ):

            texture_surface.blit(
                texture,
                (x, y)
            )


    # Create polygon mask

    polygon_mask = create_polygon_mask(
        points
    )


    # Multiply the texture alpha by the
    # polygon mask.

    texture_surface.blit(
        polygon_mask,
        (0, 0),
        special_flags=pygame.BLEND_RGBA_MULT
    )

    return texture_surface


# ============================================================
# CREATE TERRAIN
# ============================================================

# This is generated ONCE.
#
# We don't recreate these textures every frame.
# This keeps the game more efficient.

terrain_surface = pygame.Surface(
    (GAME_WIDTH, GAME_HEIGHT),
    pygame.SRCALPHA
)


# ============================================================
# BEACH TERRAIN
# ============================================================

beach_surface = create_tiled_texture(
    beach_texture,
    beach_points
)


terrain_surface.blit(
    beach_surface,
    (0, 0)
)


# ============================================================
# GRASS TERRAIN
# ============================================================

grass_surface = create_tiled_texture(
    grass_image,
    grass_points
)


terrain_surface.blit(
    grass_surface,
    (0, 0)
)

# ============================================================
# COMBAT BALANCE
# ============================================================

WEAPON_STATS = {
    "Knife": {
        "damage": 35,
        "range": 82,
        "cooldown": 0.32,
        "duration": 0.18,
    },
    "Sword": {
        "damage": 50,
        "range": 102,
        "cooldown": 0.52,
        "duration": 0.24,
    },
    "Spear": {
        "damage": 70,
        "range": 138,
        "cooldown": 0.75,
        "duration": 0.30,
    },
}

# ============================================================
# WEAPON CLASS
# ============================================================

class Weapon:

    def __init__(
        self,
        x,
        y,
        width,
        height,
        image,
        name
    ):

        self.name = name

        self.image = pygame.transform.smoothscale(
            image,
            (width, height)
        )

        self.rect = pygame.Rect(
            x,
            y,
            width,
            height
        )

    def draw(self, screen):

        screen.blit(
            self.image,
            self.rect
        )


# ============================================================
# PLAYER CLASS
# ============================================================

class Player:

    def __init__(
        self,
        x,
        y,
        animations
    ):

        self.animations = animations


        # ---------------- PLAYER RECT ----------------

        self.rect = pygame.Rect(

            x,
            y,
            100,
            100

        )


        # ---------------- FLOAT POSITION ----------------

        self.x = float(x)
        self.y = float(y)


        # ---------------- MOVEMENT ----------------

        self.speed = 250

        self.direction = pygame.Vector2(

            0,
            0

        )
        
        # ---------------- HEALTH ----------------

        self.max_health = 100
        self.health = self.max_health


        # ---------------- FACING ----------------

        self.facing_direction = "down"
        
        # ========================================================
        # WEAPON HAND OFFSETS
        # ========================================================

        self.weapon_hand_offsets = {
            "down":  (62, 68),
            "up":    (38, 38),
            "left":  (32, 65),
            "right": (68, 65)
        }


        # ---------------- ANIMATION ----------------

        self.current_frame = 0

        self.animation_timer = 0

        self.animation_speed = 0.10

        # ---------------- COMBAT ----------------
        self.attack_timer = 0.0
        self.attack_duration = 0.0
        self.attack_cooldown_timer = 0.0
        self.attack_weapon_name = None
        self.attack_has_hit = False


    # ========================================================
    # KEYBOARD INPUT
    # ========================================================

    def handle_input(self):

        keys = pygame.key.get_pressed()


        self.direction = pygame.Vector2(

            0,
            0

        )


        # ---------------- LEFT ----------------

        if keys[pygame.K_a]:

            self.direction.x -= 1

            self.facing_direction = "left"


        # ---------------- RIGHT ----------------

        if keys[pygame.K_d]:

            self.direction.x += 1

            self.facing_direction = "right"


        # ---------------- UP ----------------

        if keys[pygame.K_w]:

            self.direction.y -= 1

            self.facing_direction = "up"


        # ---------------- DOWN ----------------

        if keys[pygame.K_s]:

            self.direction.y += 1

            self.facing_direction = "down"


        # ---------------- NORMALIZE ----------------

        if self.direction.length() > 0:

            self.direction = (
                self.direction.normalize()
            )


    # ========================================================
    # MOVEMENT
    # ========================================================

    def move(
        self,
        dt,
        obstacles
    ):

        start_x = self.x
        start_y = self.y


        # ====================================================
        # HORIZONTAL MOVEMENT
        # ====================================================

        old_x = self.x

        self.x += (

            self.direction.x
            * self.speed
            * dt

        )

        self.rect.x = int(
            self.x
        )


        # ---------------- COLLISION ----------------

        for obstacle in obstacles:

            if self.rect.colliderect(
                obstacle.rect
            ):

                self.x = old_x

                self.rect.x = int(
                    self.x
                )


        # ====================================================
        # VERTICAL MOVEMENT
        # ====================================================

        old_y = self.y

        self.y += (

            self.direction.y
            * self.speed
            * dt

        )

        self.rect.y = int(
            self.y
        )


        # ---------------- COLLISION ----------------

        for obstacle in obstacles:

            if self.rect.colliderect(
                obstacle.rect
            ):

                self.y = old_y

                self.rect.y = int(
                    self.y
                )


        # ====================================================
        # ISLAND BOUNDARY
        # ====================================================

        player_center = self.rect.center


        if not point_inside_island(
            player_center
        ):

            self.x = start_x
            self.y = start_y

            self.rect.x = int(
                self.x
            )

            self.rect.y = int(
                self.y
            )
            
            
    # ========================================================
    # TAKE DAMAGE
    # ========================================================

    def take_damage(self, amount):
        
        self.health = max(
            0,
            self.health - max(0, amount)
        )

    def heal(self, amount):
        self.health = min(
            self.max_health,
            self.health + max(0, amount)
        )

    def update_attack(self, dt):
        self.attack_cooldown_timer = max(
            0.0,
            self.attack_cooldown_timer - dt
        )
        self.attack_timer = max(
            0.0,
            self.attack_timer - dt
        )

    def start_attack(self, weapon_name):
        stats = WEAPON_STATS.get(weapon_name)
        if stats is None or self.attack_cooldown_timer > 0:
            return False

        self.attack_weapon_name = weapon_name
        self.attack_duration = stats["duration"]
        self.attack_timer = stats["duration"]
        self.attack_cooldown_timer = stats["cooldown"]
        self.attack_has_hit = False
        return True

    def get_attack_hitbox(self):
        if not self.attack_weapon_name:
            return None

        stats = WEAPON_STATS[self.attack_weapon_name]
        center_x, center_y = self.rect.center
        attack_range = stats["range"]
        hit_width = 56
        hit_height = 56

        if self.facing_direction == "left":
            hitbox = pygame.Rect(
                center_x - attack_range,
                center_y - hit_height // 2,
                attack_range,
                hit_height,
            )
        elif self.facing_direction == "right":
            hitbox = pygame.Rect(
                center_x,
                center_y - hit_height // 2,
                attack_range,
                hit_height,
            )
        elif self.facing_direction == "up":
            hitbox = pygame.Rect(
                center_x - hit_width // 2,
                center_y - attack_range,
                hit_width,
                attack_range,
            )
        else:
            hitbox = pygame.Rect(
                center_x - hit_width // 2,
                center_y,
                hit_width,
                attack_range,
            )

        return hitbox

        # Prevent health from going below 0

        if self.health < 0:
            self.health = 0


    # ========================================================
    # ANIMATION
    # ========================================================

    def animate(self, dt):

        # ---------------- MOVING ----------------

        if self.direction.length() > 0:

            self.animation_timer += dt


            if (
                self.animation_timer
                >= self.animation_speed
            ):

                self.current_frame += 1


                # Loop through frames

                if self.current_frame >= 4:

                    self.current_frame = 0


                self.animation_timer = 0


        # ---------------- STANDING ----------------

        else:

            self.current_frame = 0

            self.animation_timer = 0


    def draw(self, screen):

    # ========================================================
    # DRAW PLAYER
    # ========================================================

        current_image = self.animations[
            self.facing_direction
        ][
            self.current_frame
        ]
        
        screen.blit(
            current_image,
            self.rect
        )

# ========================================================
# DRAW SELECTED WEAPON
# ========================================================

        if inventory["weapons"]:

    # ----------------------------------------------------
    # MAKE SURE SELECTED WEAPON IS VALID
    # ----------------------------------------------------

            if selected_weapon >= len(inventory["weapons"]):
                return
            
            weapon_name = inventory["weapons"][selected_weapon]

    # ----------------------------------------------------
    # GET WEAPON IMAGE
    # ----------------------------------------------------

            weapon_image = get_weapon_image(
                weapon_name
            )
            
            if weapon_image is None:
                return

    # ----------------------------------------------------
    # SCALE WEAPON
    # ----------------------------------------------------

            weapon_image = pygame.transform.smoothscale(
                weapon_image,
                (50, 50)
                    )

    # ----------------------------------------------------
    # ROTATE WEAPON
    #
    # The original weapon images are diagonal.
    # We rotate them depending on player direction.
    # ----------------------------------------------------

            if self.facing_direction == "right":

        # Vertical - blade pointing upward
                weapon_image = pygame.transform.rotate(
                    weapon_image,
                    45
                )

            elif self.facing_direction == "left":

        # Vertical - blade pointing upward
                weapon_image = pygame.transform.rotate(
                    weapon_image,
                    45
                )

            elif self.facing_direction == "up":

        # Horizontal - pointing forward
                weapon_image = pygame.transform.rotate(
                    weapon_image,
                    -45
                )

            elif self.facing_direction == "down":

        # Horizontal - pointing forward
                weapon_image = pygame.transform.rotate(
                    weapon_image,
                    -45
                )

    # ----------------------------------------------------
    # GET HAND POSITION
    # ----------------------------------------------------

            offset_x, offset_y = self.weapon_hand_offsets[
                self.facing_direction
            ]

            hand_x = self.rect.x + offset_x
            hand_y = self.rect.y + offset_y

    # ----------------------------------------------------
    # POSITION WEAPON IN HAND
    # ----------------------------------------------------

            weapon_rect = weapon_image.get_rect(
                center=(hand_x, hand_y)
            )

            # Sweep the weapon forward during the short attack window
            # while keeping it anchored to the player's hand.
            if self.attack_timer > 0:
                progress = 1 - (
                    self.attack_timer / max(0.001, self.attack_duration)
                )
                swing_amount = math.sin(progress * math.pi) * 24
                direction_vectors = {
                    "down": (0, swing_amount),
                    "up": (0, -swing_amount),
                    "left": (-swing_amount, 0),
                    "right": (swing_amount, 0),
                }
                offset_x, offset_y = direction_vectors[
                    self.facing_direction
                ]
                weapon_rect.x += int(offset_x)
                weapon_rect.y += int(offset_y)

    # ----------------------------------------------------
    # DRAW WEAPON
    # ----------------------------------------------------

            screen.blit(
                weapon_image,
                weapon_rect
            )


# ============================================================
# OBSTACLE CLASS
# ============================================================

class Obstacle:

    def __init__(
        self,
        x,
        y,
        width,
        height,
        image
    ):

        # ---------------- IMAGE ----------------

        self.image = pygame.transform.scale(

            image,

            (
                width,
                height
            )

        )


        # ---------------- COLLISION ----------------

        self.rect = pygame.Rect(

            x + int(width * 0.10),

            y + int(height * 0.45),

            int(width * 0.80),

            int(height * 0.55)

        )


        # ---------------- IMAGE POSITION ----------------

        self.image_rect = pygame.Rect(

            x,
            y,

            width,
            height

        )


        # ====================================================
        # CREATE SHADOW ONCE
        # ====================================================

        shadow_width = max(
            1,
            int(
                self.image_rect.width
                * 0.80
            )
        )

        shadow_height = max(
            1,
            int(
                self.image_rect.height
                * 0.20
            )
        )


        self.shadow_surface = pygame.Surface(

            (
                shadow_width,
                shadow_height
            ),

            pygame.SRCALPHA

        )


        pygame.draw.ellipse(

            self.shadow_surface,

            (
                20,
                30,
                20,
                75
            ),

            self.shadow_surface.get_rect()

        )


    # ========================================================
    # DRAW TREE
    # ========================================================

    def draw(self, screen):

        # ---------------- TREE SHADOW ----------------

        screen.blit(

            self.shadow_surface,

            (

                self.image_rect.x
                + int(
                    self.image_rect.width
                    * 0.10
                ),

                self.image_rect.bottom
                - int(
                    self.shadow_surface.get_height()
                    * 0.60
                )

            )

        )


        # ---------------- TREE IMAGE ----------------

        screen.blit(

            self.image,

            self.image_rect

        )

# ============================================================
# WEAPON PICKUP CLASS
# ============================================================

class WeaponPickup:

    PICKUP_DISTANCE = 90

    def __init__(
        self,
        x,
        y,
        weapon_name
    ):

        self.weapon_name = weapon_name

        # ====================================================
        # POSITION
        # ====================================================

        self.rect = pygame.Rect(
            x,
            y,
            45,
            45
        )

        # Original ground position.
        # The weapon floats around this position.

        self.base_y = y

        # ====================================================
        # FLOATING ANIMATION
        # ====================================================

        self.animation_time = 0

        self.float_speed = 3.0
        self.float_height = 5

        # ====================================================
        # WEAPON IMAGE
        # ====================================================

        if weapon_name == "Knife":

            image = knife_image

        elif weapon_name == "Sword":

            image = sword_image

        elif weapon_name == "Spear":

            image = spear_image

        else:

            image = None

        # ====================================================
        # PREPARE IMAGE
        # ====================================================

        if image is not None:

            self.image = pygame.transform.smoothscale(
                image,
                (
                    45,
                    45
                )
            )

        else:

            # Fallback image if the weapon image
            # cannot be found.

            self.image = pygame.Surface(
                (
                    45,
                    45
                ),
                pygame.SRCALPHA
            )

            self.image.fill(
                (
                    120,
                    120,
                    120
                )
            )

        # ====================================================
        # WEAPON SHADOW
        # ====================================================

        self.shadow_surface = pygame.Surface(
            (
                34,
                10
            ),
            pygame.SRCALPHA
        )

        pygame.draw.ellipse(
            self.shadow_surface,
            (
                20,
                25,
                20,
                90
            ),
            self.shadow_surface.get_rect()
        )


    # ========================================================
    # UPDATE WEAPON FLOATING ANIMATION
    # ========================================================

    def update(self, dt):

        self.animation_time += dt

        float_offset = (
            math.sin(
                self.animation_time
                * self.float_speed
            )
            * self.float_height
        )

        self.rect.y = int(
            self.base_y
            + float_offset
        )


    # ========================================================
    # DRAW WEAPON PICKUP
    # ========================================================

    def draw(self, screen):

        # ====================================================
        # DRAW SHADOW
        # ====================================================

        shadow_x = (
            self.rect.centerx
            - self.shadow_surface.get_width() // 2
        )

        shadow_y = (
            self.base_y
            + self.rect.height
            - 3
        )

        screen.blit(
            self.shadow_surface,
            (
                shadow_x,
                shadow_y
            )
        )

        # ====================================================
        # DRAW WEAPON
        # ====================================================

        screen.blit(
            self.image,
            self.rect
        )

# ============================================================
# GET WEAPON IMAGE
# ============================================================

def get_weapon_image(weapon_name):

    if weapon_name == "Knife":
        return knife_image

    elif weapon_name == "Sword":
        return sword_image

    elif weapon_name == "Spear":
        return spear_image

    return None
# ============================================================
# FIND NEARBY WEAPON
# ============================================================

def get_nearby_weapon(
    player,
    weapons
):

    for weapon in weapons:

        distance = pygame.Vector2(
            player.rect.center
        ).distance_to(
            weapon.rect.center
        )

        if distance <= WeaponPickup.PICKUP_DISTANCE:

            return weapon

    return None

# ============================================================
# ROCK CLASS
# ============================================================

class Rock:

    def __init__(
        self,
        x,
        y,
        width,
        height
    ):

        # ---------------- IMAGE ----------------

        self.image = pygame.transform.scale(

            rock_image,

            (
                width,
                height
            )

        )


        # ---------------- COLLISION ----------------

        self.rect = pygame.Rect(

            x + int(width * 0.10),

            y + int(height * 0.40),

            int(width * 0.80),

            int(height * 0.60)

        )


        # ---------------- IMAGE POSITION ----------------

        self.image_rect = pygame.Rect(

            x,
            y,

            width,
            height

        )


        # ====================================================
        # CREATE ROCK SHADOW ONCE
        # ====================================================

        shadow_width = max(
            1,
            int(
                self.image_rect.width
                * 0.90
            )
        )

        shadow_height = max(
            1,
            int(
                self.image_rect.height
                * 0.35
            )
        )


        self.shadow_surface = pygame.Surface(

            (
                shadow_width,
                shadow_height
            ),

            pygame.SRCALPHA

        )


        pygame.draw.ellipse(

            self.shadow_surface,

            (
                20,
                30,
                20,
                70
            ),

            self.shadow_surface.get_rect()

        )


    # ========================================================
    # DRAW ROCK
    # ========================================================

    def draw(self, screen):

        # ---------------- ROCK SHADOW ----------------

        screen.blit(

            self.shadow_surface,

            (

                self.image_rect.x
                + int(
                    self.image_rect.width
                    * 0.05
                ),

                self.image_rect.bottom
                - int(
                    self.shadow_surface.get_height()
                    * 0.65
                )

            )

        )


        # ---------------- ROCK IMAGE ----------------

        screen.blit(

            self.image,

            self.image_rect

        )


# ============================================================
# ENEMY CLASS
# ============================================================

class Enemy:

    DETECTION_RANGE = 320
    ATTACK_RANGE = 78
    ATTACK_DAMAGE = 10
    ATTACK_COOLDOWN = 1.00

    def __init__(self, x, y):
        self.animations = enemy_animations
        self.rect = pygame.Rect(x, y, 90, 90)
        self.x = float(x)
        self.y = float(y)
        # Deliberately slower than the player so combat has readable spacing.
        self.speed = 92
        self.facing_direction = "down"
        self.direction = pygame.Vector2()
        self.current_frame = 0
        self.animation_timer = 0.0
        self.animation_speed = 0.14
        self.max_health = 100
        self.health = self.max_health
        self.attack_cooldown_timer = 0.0
        self.wander_timer = 0.0
        self.wander_direction = pygame.Vector2()
        self.dead = False
        self.death_duration = 0.45
        self.death_timer = self.death_duration
        self.hit_flash_timer = 0.0

    def take_damage(self, amount):
        if self.dead:
            return False

        self.health = max(0, self.health - max(0, amount))
        self.hit_flash_timer = 0.10

        if self.health == 0:
            self.dead = True
            self.direction = pygame.Vector2()
            self.death_timer = self.death_duration
            play_sound("enemy_death")
            spawn_particles(
                self.rect.centerx,
                self.rect.centery,
                (210, 60, 55),
                amount=18,
                speed=210,
                life=0.5,
                size=6,
            )
            spawn_particles(
                self.rect.centerx,
                self.rect.centery,
                (255, 190, 120),
                amount=8,
                speed=120,
                life=0.4,
                size=4,
            )
            spawn_floating_text(
                self.rect.centerx,
                self.rect.top - 4,
                "DEFEATED",
                (255, 210, 120),
            )
        else:
            play_sound("hit")
            spawn_particles(
                self.rect.centerx,
                self.rect.centery,
                (200, 80, 75),
                amount=5,
                speed=110,
                life=0.28,
                size=4,
            )

        return True

    def _move_with_collisions(self, dt, obstacles, other_enemies):
        old_x = self.x
        self.x += self.direction.x * self.speed * dt
        self.rect.x = int(self.x)

        if (
            not point_inside_island(self.rect.center)
            or any(self.rect.colliderect(obstacle.rect) for obstacle in obstacles)
            or any(
                other is not self
                and not other.dead
                and self.rect.colliderect(other.rect)
                for other in other_enemies
            )
        ):
            self.x = old_x
            self.rect.x = int(self.x)

        old_y = self.y
        self.y += self.direction.y * self.speed * dt
        self.rect.y = int(self.y)

        if (
            not point_inside_island(self.rect.center)
            or any(self.rect.colliderect(obstacle.rect) for obstacle in obstacles)
            or any(
                other is not self
                and not other.dead
                and self.rect.colliderect(other.rect)
                for other in other_enemies
            )
        ):
            self.y = old_y
            self.rect.y = int(self.y)

    def _choose_wander_direction(self):
        angle = random.uniform(0, math.tau)
        self.wander_direction = pygame.Vector2(
            math.cos(angle),
            math.sin(angle),
        )
        self.wander_timer = random.uniform(0.8, 2.4)

    def update(self, dt, player, obstacles, other_enemies, allow_attack=True):
        if self.dead:
            self.death_timer = max(0.0, self.death_timer - dt)
            return False

        self.attack_cooldown_timer = max(
            0.0,
            self.attack_cooldown_timer - dt,
        )
        self.hit_flash_timer = max(0.0, self.hit_flash_timer - dt)

        distance = pygame.Vector2(self.rect.center).distance_to(
            player.rect.center
        )

        if distance <= self.ATTACK_RANGE:
            self.direction = pygame.Vector2()
            if allow_attack and self.attack_cooldown_timer <= 0:
                player.take_damage(self.ATTACK_DAMAGE)
                self.attack_cooldown_timer = self.ATTACK_COOLDOWN
                play_sound("enemy_attack")
                return True
        elif distance <= self.DETECTION_RANGE:
            to_player = pygame.Vector2(
                player.rect.center
            ) - pygame.Vector2(self.rect.center)
            self.direction = (
                to_player.normalize()
                if to_player.length_squared() > 0
                else pygame.Vector2()
            )
        else:
            self.wander_timer -= dt
            if self.wander_timer <= 0:
                self._choose_wander_direction()
            self.direction = self.wander_direction

        if self.direction.length_squared() > 0:
            if abs(self.direction.x) > abs(self.direction.y):
                self.facing_direction = (
                    "right" if self.direction.x > 0 else "left"
                )
            else:
                self.facing_direction = (
                    "down" if self.direction.y > 0 else "up"
                )

        self._move_with_collisions(dt, obstacles, other_enemies)
        self.animation_timer += dt
        if self.direction.length_squared() > 0:
            if self.animation_timer >= self.animation_speed:
                self.current_frame = (
                    self.current_frame + 1
                ) % len(self.animations[self.facing_direction])
                self.animation_timer = 0
        else:
            self.current_frame = 0

        return False

    def draw(self, screen):
        if self.dead and self.death_timer <= 0:
            return

        image = self.animations[self.facing_direction][self.current_frame]
        if self.hit_flash_timer > 0:
            image = image.copy()
            image.fill(
                (255, 150, 150, 150),
                special_flags=pygame.BLEND_RGBA_ADD,
            )

        if self.dead:
            progress = max(0.0, self.death_timer / self.death_duration)

            # Short "collapse + fade" death effect.
            width = max(1, int(self.rect.width * (0.55 + 0.45 * progress)))
            height = max(1, int(self.rect.height * (0.25 + 0.75 * progress)))
            image = pygame.transform.smoothscale(image, (width, height))
            image.set_alpha(int(255 * progress))

            death_rect = image.get_rect(
                midbottom=(self.rect.centerx, self.rect.bottom)
            )
            screen.blit(image, death_rect)
            return

        screen.blit(image, self.rect)

        if not self.dead:
            bar_width = 72
            bar_height = 8
            bar_x = self.rect.centerx - bar_width // 2
            bar_y = self.rect.top - 14
            pygame.draw.rect(
                screen,
                (35, 20, 20),
                (bar_x - 2, bar_y - 2, bar_width + 4, bar_height + 4),
                border_radius=3,
            )
            pygame.draw.rect(
                screen,
                (115, 35, 35),
                (bar_x, bar_y, bar_width, bar_height),
                border_radius=2,
            )
            pygame.draw.rect(
                screen,
                (235, 70, 65),
                (
                    bar_x,
                    bar_y,
                    int(bar_width * self.health / self.max_health),
                    bar_height,
                ),
                border_radius=2,
            )


# ============================================================
# APPLE PICKUP CLASS
# ============================================================

class ApplePickup:

    PICKUP_DISTANCE = 72

    def __init__(self, x, y):
        self.base_y = y
        self.rect = pygame.Rect(x, y, 42, 42)
        self.image = pygame.transform.smoothscale(
            apple_image,
            (42, 42),
        )
        self.animation_time = random.uniform(0, math.tau)

    def update(self, dt):
        self.animation_time += dt * 3.2
        self.rect.y = int(
            self.base_y + math.sin(self.animation_time) * 5
        )

    def draw(self, screen):
        shadow_rect = pygame.Rect(
            self.rect.centerx - 16,
            self.base_y + 34,
            32,
            8,
        )
        pygame.draw.ellipse(
            screen,
            (20, 25, 20, 90),
            shadow_rect,
        )
        screen.blit(self.image, self.rect)


# ============================================================
# PLAYER
# ============================================================

player = Player(

    550,
    300,

    animations

)
# ============================================================
# INVENTORY
# ============================================================

inventory = {

    "weapons": [],

    "food": 3,
}

# Currently selected weapon
selected_weapon = 0

# Inventory open/closed
inventory_open = False

# Apple healing inventory
apple_count = 0


# ============================================================
# TREES / ENVIRONMENT
# ============================================================

obstacles = [

    # ========================================================
    # TOP-LEFT FOREST
    # ========================================================

    Obstacle(
        180,
        140,
        90,
        110,
        tree_image
    ),

    Obstacle(
        260,
        160,
        100,
        120,
        tree2_image
    ),

    Obstacle(
        190,
        240,
        90,
        110,
        tree3_image
    ),

    Obstacle(
        290,
        250,
        90,
        110,
        tree4_image
    ),


    # ========================================================
    # TOP-RIGHT FOREST
    # ========================================================

    Obstacle(
        820,
        140,
        100,
        120,
        tree3_image
    ),

    Obstacle(
        900,
        160,
        90,
        110,
        tree_image
    ),

    Obstacle(
        980,
        200,
        90,
        110,
        tree2_image
    ),

    Obstacle(
        900,
        250,
        80,
        100,
        tree4_image
    ),


    # ========================================================
    # LEFT FOREST
    # ========================================================

    Obstacle(
        120,
        300,
        90,
        110,
        tree4_image
    ),

    Obstacle(
        160,
        390,
        100,
        120,
        tree_image
    ),

    Obstacle(
        210,
        470,
        90,
        110,
        tree3_image
    ),


    # ========================================================
    # RIGHT FOREST
    # ========================================================

    Obstacle(
        1000,
        300,
        90,
        110,
        tree_image
    ),

    Obstacle(
        960,
        390,
        90,
        110,
        tree2_image
    ),

    Obstacle(
        900,
        470,
        100,
        120,
        tree3_image
    ),


    # ========================================================
    # BOTTOM-LEFT FOREST
    # ========================================================

    Obstacle(
        300,
        500,
        90,
        110,
        tree2_image
    ),

    Obstacle(
        380,
        530,
        100,
        120,
        tree4_image
    ),


    # ========================================================
    # BOTTOM-RIGHT FOREST
    # ========================================================

    Obstacle(
        780,
        520,
        90,
        110,
        tree3_image
    ),

    Obstacle(
        870,
        500,
        90,
        110,
        tree2_image
    )

]

# ============================================================
# WEAPON PICKUPS
# ============================================================

weapon_pickups = [

    WeaponPickup(
        450,
        250,
        "Knife"
    ),

    WeaponPickup(
        700,
        250,
        "Sword"
    ),

    WeaponPickup(
        600,
        500,
        "Spear"
    )

]
nearby_weapon = None

# ============================================================
# ORIGINAL WEAPON SPAWN DATA (used to respawn on Play Again)
# ============================================================

weapon_spawn_data = [
    (450, 250, "Knife"),
    (700, 250, "Sword"),
    (600, 500, "Spear")
]


# ============================================================
# COASTAL ROCKS
# ============================================================

rocks = [

    # ---------------- TOP ----------------

    Rock(
        400,
        85,
        60,
        45
    ),

    Rock(
        700,
        90,
        60,
        45
    ),


    # ---------------- LEFT ----------------

    Rock(
        80,
        220,
        60,
        45
    ),

    Rock(
        95,
        470,
        60,
        45
    ),


    # ---------------- RIGHT ----------------

    Rock(
        1060,
        220,
        60,
        45
    ),

    Rock(
        1050,
        450,
        60,
        45
    ),


    # ---------------- BOTTOM ----------------

    Rock(
        500,
        575,
        60,
        45
    ),

    Rock(
        750,
        570,
        60,
        45
    )

]


# ============================================================
# GRASS DECORATIONS
# ============================================================

grass_decorations = [

    (400, 190),

    (760, 190),

    (350, 400),

    (820, 400),

    (470, 480),

    (730, 480)

]


def draw_grass(screen):

    for x, y in grass_decorations:

        # ---------------- LEFT BLADE ----------------

        pygame.draw.line(

            screen,

            (35, 120, 45),

            (x, y + 15),

            (x - 5, y),

            3

        )


        # ---------------- RIGHT BLADE ----------------

        pygame.draw.line(

            screen,

            (35, 120, 45),

            (x, y + 15),

            (x + 5, y),

            3

        )


        # ---------------- CENTER BLADE ----------------

        pygame.draw.line(

            screen,

            (35, 120, 45),

            (x, y + 15),

            (x, y - 2),

            3

        )
        
# ============================================================
# DRAW WEAPON PICKUP PROMPT
# ============================================================

def draw_weapon_pickup_prompt(screen, weapon):

    if weapon is None:
        return

    prompt_font = pygame.font.Font(
        None,
        24
    )

    prompt_text = prompt_font.render(
        f"[E] Pick up {weapon.weapon_name}",
        True,
        (255, 255, 255)
    )

    prompt_background = pygame.Surface(
        (
            prompt_text.get_width() + 20,
            prompt_text.get_height() + 10
        ),
        pygame.SRCALPHA
    )

    pygame.draw.rect(
        prompt_background,
        (0, 0, 0, 170),
        prompt_background.get_rect(),
        border_radius=8
    )

    prompt_rect = prompt_text.get_rect(
        center=(
            weapon.rect.centerx,
            weapon.rect.top - 30
        )
    )

    background_rect = prompt_background.get_rect(
        center=prompt_rect.center
    )

    screen.blit(
        prompt_background,
        background_rect
    )

    screen.blit(
        prompt_text,
        prompt_rect
    )
        
# ============================================================
# DRAW INVENTORY
# ============================================================

def draw_inventory(screen):
    
    global selected_weapon

    # ========================================================
    # INVENTORY PANEL
    # ========================================================

    panel_width = 500
    panel_height = 500

    panel_x = (
        GAME_WIDTH - panel_width
    ) // 2

    panel_y = (
        GAME_HEIGHT - panel_height
    ) // 2

    # ---------------- BACKGROUND ----------------

    panel = pygame.Surface(
        (
            panel_width,
            panel_height
        ),
        pygame.SRCALPHA
    )

    panel.fill(
        (20, 25, 30, 235)
    )

    screen.blit(
        panel,
        (
            panel_x,
            panel_y
        )
    )

    # ---------------- BORDER ----------------

    pygame.draw.rect(
        screen,
        (220, 220, 220),
        (
            panel_x,
            panel_y,
            panel_width,
            panel_height
        ),
        3,
        border_radius=12
    )

    # ========================================================
    # FONTS
    # ========================================================

    title_font = pygame.font.Font(
        None,
        48
    )

    section_font = pygame.font.Font(
        None,
        32
    )

    item_font = pygame.font.Font(
        None,
        27
    )

    # ========================================================
    # TITLE
    # ========================================================

    title = title_font.render(
        "INVENTORY",
        True,
        (255, 255, 255)
    )

    title_rect = title.get_rect(
        center=(
            GAME_WIDTH // 2,
            panel_y + 55
        )
    )

    screen.blit(
        title,
        title_rect
    )

    # ========================================================
    # WEAPONS SECTION
    # ========================================================

    weapons_title = section_font.render(
        "WEAPONS",
        True,
        (255, 210, 80)
    )

    screen.blit(
        weapons_title,
        (
            panel_x + 40,
            panel_y + 110
        )
    )

    # ========================================================
    # WEAPON LIST
    # ========================================================

    for i, weapon in enumerate(
        inventory["weapons"]
    ):

        weapon_y = (
            panel_y
            + 160
            + i * 55
        )

        # Selected weapon background

        if i == selected_weapon:

            pygame.draw.rect(
                screen,
                (65, 100, 65),
                (
                    panel_x + 30,
                    weapon_y - 5,
                    440,
                    45
                ),
                border_radius=8
            )

        weapon_text = item_font.render(
            f"{i + 1}. {weapon}",
            True,
            (255, 255, 255)
        )

        screen.blit(
            weapon_text,
            (
                panel_x + 50,
                weapon_y
            )
        )

    # ========================================================
    # APPLES SECTION
    # ========================================================

    food_title = section_font.render(
        "APPLES",
        True,
        (255, 150, 100),
    )

    screen.blit(
        food_title,
        (
            panel_x + 40,
            panel_y + 335
        )
    )

    food_text = item_font.render(
        f"Apples: {apple_count}",
        True,
        (255, 255, 255),
    )

    screen.blit(
        food_text,
        (
            panel_x + 50,
            panel_y + 380
        )
    )

    # ========================================================
    # SELECTED WEAPON
    # ========================================================

    if inventory["weapons"]:

        # Make sure selected_weapon is valid

        if selected_weapon >= len(inventory["weapons"]):
            selected_weapon = 0

        selected_text = item_font.render(
            f"Selected: {inventory['weapons'][selected_weapon]}",
            True,
            (180, 220, 180)
        )

    else:
        selected_text = item_font.render(
            "Selected: None",
            True,
            (180, 220, 180)
        )


    screen.blit(
        selected_text,
        (
            panel_x + 50,
            panel_y + 425
        )
    )
    
# ============================================================
# HEALTH BAR
# ============================================================

def draw_health_bar(screen, player):

    # ---------------- POSITION ----------------

    x = 20
    y = 20

    width = 250
    height = 25

    # ---------------- BORDER ----------------

    pygame.draw.rect(
        screen,
        (0, 0, 0),
        (
            x - 3,
            y - 3,
            width + 6,
            height + 6
        )
    )

    # ---------------- BACKGROUND ----------------

    pygame.draw.rect(
        screen,
        (100, 30, 30),
        (
            x,
            y,
            width,
            height
        )
    )

    # ---------------- CURRENT HEALTH ----------------

    health_ratio = (
        player.health /
        player.max_health
    )

    health_width = int(
        width * health_ratio
    )

    pygame.draw.rect(
        screen,
        (40, 190, 60),
        (
            x,
            y,
            health_width,
            height
        )
    )


# ============================================================
# ALL COLLIDERS
# ============================================================

colliders = obstacles + rocks


# ============================================================
# COMBAT / PICKUP HELPERS
# ============================================================

enemies = []
apples = []
nearby_apple = None
nearby_weapon = None
defeated_enemies = 0
enemy_attack_lock_timer = 0.0


def get_selected_weapon_name():
    if not inventory["weapons"]:
        return None
    if selected_weapon >= len(inventory["weapons"]):
        return None
    return inventory["weapons"][selected_weapon]


def spawn_position_is_valid(rect, occupied_rects):
    if not point_inside_island(rect.center):
        return False
    if any(rect.colliderect(collider.rect) for collider in colliders):
        return False
    return not any(rect.colliderect(other) for other in occupied_rects)


def find_spawn_position(size, occupied_rects, attempts=4000):
    width, height = size
    for _ in range(attempts):
        candidate = pygame.Rect(
            random.randint(120, GAME_WIDTH - width - 120),
            random.randint(120, GAME_HEIGHT - height - 100),
            width,
            height,
        )
        if spawn_position_is_valid(candidate, occupied_rects):
            return candidate.topleft

    # Deterministic fallbacks keep restart reliable even with an unusually
    # crowded obstacle layout.
    fallback_positions = [
        (480, 170),
        (690, 170),
        (520, 430),
        (720, 430),
        (350, 330),
        (850, 330),
    ]
    for x, y in fallback_positions:
        candidate = pygame.Rect(x, y, width, height)
        if spawn_position_is_valid(candidate, occupied_rects):
            return candidate.topleft
    return None


def spawn_enemies(enemy_count=None):
    """Spawn exactly one wave in safe, non-overlapping positions."""
    enemies.clear()
    occupied = [player.rect.copy()]
    occupied.extend(weapon.rect.copy() for weapon in weapon_pickups)
    occupied.extend(apple.rect.copy() for apple in apples)

    if enemy_count is None:
        enemy_count = DIFFICULTY_WAVES[selected_difficulty][current_wave - 1]

    while len(enemies) < enemy_count:
        position = find_spawn_position((90, 90), occupied)
        if position is None:
            raise RuntimeError("Unable to find valid spawn positions for enemies")
        enemy = Enemy(*position)
        enemies.append(enemy)
        occupied.append(enemy.rect.copy())


def spawn_apples():
    apples.clear()
    occupied = [player.rect.copy()]
    occupied.extend(weapon.rect.copy() for weapon in weapon_pickups)
    occupied.extend(enemy.rect.copy() for enemy in enemies)

    while len(apples) < 8:
        position = find_spawn_position((42, 42), occupied)
        if position is None:
            raise RuntimeError("Unable to find valid spawn positions for apples")
        apple = ApplePickup(*position)
        apples.append(apple)
        occupied.append(apple.rect.copy())


def get_nearby_apple(player, apple_pickups):
    for apple in apple_pickups:
        distance = pygame.Vector2(
            player.rect.center
        ).distance_to(apple.rect.center)
        if distance <= ApplePickup.PICKUP_DISTANCE:
            return apple
    return None


def draw_apple_pickup_prompt(screen, apple):
    if apple is None:
        return

    prompt_font = pygame.font.Font(None, 24)
    prompt_text = prompt_font.render(
        "[E] Pick up apple",
        True,
        (255, 255, 255),
    )
    prompt_background = pygame.Surface(
        (prompt_text.get_width() + 20, prompt_text.get_height() + 10),
        pygame.SRCALPHA,
    )
    pygame.draw.rect(
        prompt_background,
        (0, 0, 0, 170),
        prompt_background.get_rect(),
        border_radius=8,
    )
    prompt_rect = prompt_text.get_rect(
        center=(apple.rect.centerx, apple.rect.top - 24)
    )
    screen.blit(
        prompt_background,
        prompt_background.get_rect(center=prompt_rect.center),
    )
    screen.blit(prompt_text, prompt_rect)


def perform_player_attack():
    global defeated_enemies
    global wave_defeated

    hitbox = player.get_attack_hitbox()
    weapon_name = player.attack_weapon_name
    if hitbox is None or weapon_name is None or player.attack_has_hit:
        return

    player.attack_has_hit = True
    damage = WEAPON_STATS[weapon_name]["damage"]
    for enemy in enemies:
        if not enemy.dead and hitbox.colliderect(enemy.rect):
            if enemy.take_damage(damage) and enemy.dead:
                defeated_enemies += 1
                wave_defeated += 1


def draw_apples_hud(screen):
    font = pygame.font.Font(None, 30)
    hint_font = pygame.font.Font(None, 22)

    enemies_remaining = sum(1 for enemy in enemies if not enemy.dead)
    text = font.render(
        (
            f"Difficulty: {selected_difficulty}    "
            f"Wave: {current_wave}/{total_waves}    "
            f"Enemies Remaining: {enemies_remaining}"
        ),
        True,
        (255, 245, 210),
    )
    inventory_text = font.render(
        f"Apples: {apple_count}    Defeated: {defeated_enemies}",
        True,
        (235, 245, 225),
    )
    hint = hint_font.render(
        "ESC pause   •   H heal   •   I inventory",
        True,
        (185, 200, 195),
    )

    panel_width = max(
        text.get_width(),
        inventory_text.get_width(),
        hint.get_width(),
    ) + 28
    panel_height = (
        text.get_height()
        + inventory_text.get_height()
        + hint.get_height()
        + 28
    )
    background = pygame.Surface(
        (panel_width, panel_height),
        pygame.SRCALPHA,
    )
    pygame.draw.rect(
        background,
        (16, 26, 22, 195),
        background.get_rect(),
        border_radius=10,
    )
    pygame.draw.rect(
        background,
        (95, 130, 110, 190),
        background.get_rect(),
        2,
        border_radius=10,
    )
    screen.blit(background, (18, 58))
    screen.blit(text, (32, 66))
    screen.blit(
        inventory_text,
        (32, 68 + text.get_height() + 4),
    )
    screen.blit(
        hint,
        (
            32,
            70
            + text.get_height()
            + inventory_text.get_height(),
        ),
    )


def draw_wave_banner(screen):
    if wave_banner_timer <= 0 or menu_active or game_over:
        return

    banner_font = pygame.font.Font(None, 48)
    detail_font = pygame.font.Font(None, 25)
    progress = min(1.0, wave_banner_timer / 0.35)
    alpha = int(255 * min(1.0, progress))

    title = banner_font.render(
        f"WAVE {current_wave} / {total_waves}",
        True,
        (255, 235, 155),
    )
    detail = detail_font.render(
        (
            f"{selected_difficulty}  •  "
            f"{DIFFICULTY_WAVES[selected_difficulty][current_wave - 1]} "
            "enemies incoming"
        ),
        True,
        (225, 240, 230),
    )
    panel_rect = pygame.Rect(
        GAME_WIDTH // 2 - 225,
        82,
        450,
        88,
    )
    panel = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
    pygame.draw.rect(
        panel,
        (15, 28, 27, max(0, alpha - 30)),
        panel.get_rect(),
        border_radius=14,
    )
    pygame.draw.rect(
        panel,
        (225, 190, 95, alpha),
        panel.get_rect(),
        2,
        border_radius=14,
    )
    screen.blit(panel, panel_rect.topleft)
    title.set_alpha(alpha)
    detail.set_alpha(alpha)
    screen.blit(title, title.get_rect(center=(GAME_WIDTH // 2, 112)))
    screen.blit(detail, detail.get_rect(center=(GAME_WIDTH // 2, 145)))


# ============================================================
# GAME OVER SCREEN
# ============================================================

def get_game_over_buttons():
    return {
        "play_again": pygame.Rect(GAME_WIDTH // 2 - 170, 350, 340, 68),
        "main_menu": pygame.Rect(GAME_WIDTH // 2 - 170, 432, 340, 68),
        "quit": pygame.Rect(GAME_WIDTH // 2 - 170, 514, 340, 68),
    }


def draw_game_over(screen, won=False):

    # ========================================================
    # DARK OVERLAY
    # ========================================================

    overlay = pygame.Surface(
        (GAME_WIDTH, GAME_HEIGHT),
        pygame.SRCALPHA
    )

    overlay.fill(
        (0, 0, 0, 175)
    )

    screen.blit(
        overlay,
        (0, 0)
    )

    # ========================================================
    # FONTS
    # ========================================================

    title_font = pygame.font.Font(
        None,
        90
    )

    subtitle_font = pygame.font.Font(
        None,
        36
    )

    button_font = pygame.font.Font(
        None,
        38
    )

    # ========================================================
    # GAME OVER TITLE
    # ========================================================

    title = title_font.render(
        "YOU WIN!" if won else "YOU LOST!",
        True,
        (255, 235, 120) if won else (255, 150, 150),
    )

    title_rect = title.get_rect(
        center=(
            GAME_WIDTH // 2,
            210
        )
    )

    screen.blit(
        title,
        title_rect
    )

    # ========================================================
    # YOU DIED TEXT
    # ========================================================

    subtitle = subtitle_font.render(
        (
            "All waves defeated!"
            if won
            else "LOL , SKILL ISSUE."
        ),
        True,
        (220, 220, 220)
    )

    subtitle_rect = subtitle.get_rect(
        center=(
            GAME_WIDTH // 2,
            285
        )
    )

    screen.blit(
        subtitle,
        subtitle_rect
    )

    # ========================================================
    # BUTTONS
    # ========================================================

    game_mouse_x, game_mouse_y = get_game_mouse_position()

    buttons = get_game_over_buttons()

    button_style = (
        ("play_again", "PLAY AGAIN", (45, 150, 65), (70, 190, 90)),
        ("main_menu", "MAIN MENU", (45, 90, 145), (70, 125, 195)),
        ("quit", "QUIT", (150, 45, 45), (205, 70, 70)),
    )

    for key, label, base_color, hover_color in button_style:
        button_rect = buttons[key]
        draw_ui_button(
            screen,
            button_rect,
            label,
            base_color,
            hover_color,
            button_font,
            button_rect.collidepoint(game_mouse_x, game_mouse_y),
        )


# ============================================================
# MAIN MENU
# ============================================================

def get_menu_buttons():
    return {
        "difficulty_easy": pygame.Rect(GAME_WIDTH // 2 - 270, 338, 160, 58),
        "difficulty_medium": pygame.Rect(GAME_WIDTH // 2 - 80, 338, 160, 58),
        "difficulty_hard": pygame.Rect(GAME_WIDTH // 2 + 110, 338, 160, 58),
        "play": pygame.Rect(GAME_WIDTH // 2 - 170, 426, 340, 68),
        "quit": pygame.Rect(GAME_WIDTH // 2 - 170, 510, 340, 68),
    }


def get_pause_buttons():
    return {
        "resume": pygame.Rect(GAME_WIDTH // 2 - 160, 250, 320, 62),
        "restart": pygame.Rect(GAME_WIDTH // 2 - 160, 326, 320, 62),
        "main_menu": pygame.Rect(GAME_WIDTH // 2 - 160, 402, 320, 62),
        "quit": pygame.Rect(GAME_WIDTH // 2 - 160, 478, 320, 62),
    }


def draw_pause_menu(screen):
    overlay = pygame.Surface(
        (GAME_WIDTH, GAME_HEIGHT),
        pygame.SRCALPHA,
    )
    overlay.fill((6, 14, 20, 195))
    screen.blit(overlay, (0, 0))

    panel = pygame.Rect(GAME_WIDTH // 2 - 220, 130, 440, 430)
    panel_surface = pygame.Surface(panel.size, pygame.SRCALPHA)
    pygame.draw.rect(
        panel_surface,
        (18, 32, 30, 225),
        panel_surface.get_rect(),
        border_radius=18,
    )
    pygame.draw.rect(
        panel_surface,
        (120, 160, 140, 220),
        panel_surface.get_rect(),
        2,
        border_radius=18,
    )
    screen.blit(panel_surface, panel.topleft)

    title_font = pygame.font.Font(None, 64)
    button_font = pygame.font.Font(None, 36)
    hint_font = pygame.font.Font(None, 24)

    title = title_font.render("PAUSED", True, (245, 225, 150))
    screen.blit(
        title,
        title.get_rect(center=(GAME_WIDTH // 2, 190)),
    )

    game_mouse_x, game_mouse_y = get_game_mouse_position()
    buttons = get_pause_buttons()

    for key, label, base_color, hover_color in (
        ("resume", "RESUME", (45, 150, 65), (70, 190, 90)),
        ("restart", "RESTART", (145, 105, 40), (195, 145, 60)),
        ("main_menu", "MAIN MENU", (45, 90, 145), (70, 125, 195)),
        ("quit", "QUIT", (145, 50, 50), (205, 70, 70)),
    ):
        button_rect = buttons[key]
        draw_ui_button(
            screen,
            button_rect,
            label,
            base_color,
            hover_color,
            button_font,
            button_rect.collidepoint(game_mouse_x, game_mouse_y),
        )

    hint = hint_font.render(
        "Press ESC to resume",
        True,
        (175, 195, 190),
    )
    screen.blit(
        hint,
        hint.get_rect(center=(GAME_WIDTH // 2, 540)),
    )


def draw_menu(screen):
    overlay = pygame.Surface(
        (GAME_WIDTH, GAME_HEIGHT),
        pygame.SRCALPHA,
    )
    overlay.fill((5, 18, 28, 220))
    screen.blit(overlay, (0, 0))

    title_font = pygame.font.Font(None, 86)
    button_font = pygame.font.Font(None, 42)
    hint_font = pygame.font.Font(None, 28)

    title = title_font.render(
        "SURVIVE: THE LOST ISLAND",
        True,
        (245, 225, 150),
    )
    screen.blit(
        title,
        title.get_rect(center=(GAME_WIDTH // 2, 190)),
    )

    subtitle = hint_font.render(
        "Do you have what it takes?",
        True,
        (210, 230, 225),
    )
    screen.blit(
        subtitle,
        subtitle.get_rect(center=(GAME_WIDTH // 2, 260)),
    )

    game_mouse_x, game_mouse_y = get_game_mouse_position()

    buttons = get_menu_buttons()

    difficulty_label = hint_font.render(
        "DIFFICULTY",
        True,
        (245, 225, 150),
    )
    screen.blit(
        difficulty_label,
        difficulty_label.get_rect(center=(GAME_WIDTH // 2, 320)),
    )

    for key, label in (
        ("difficulty_easy", "EASY"),
        ("difficulty_medium", "MEDIUM"),
        ("difficulty_hard", "HARD"),
    ):
        button_rect = buttons[key]
        is_selected = label == selected_difficulty
        base_color = (
            (175, 125, 45) if is_selected else (40, 90, 100)
        )
        hover_color = (
            (215, 160, 65) if is_selected else (65, 135, 145)
        )
        draw_ui_button(
            screen,
            button_rect,
            label,
            base_color,
            hover_color,
            button_font,
            button_rect.collidepoint(game_mouse_x, game_mouse_y),
        )
        if is_selected:
            pygame.draw.rect(
                screen,
                (255, 235, 150),
                button_rect.inflate(8, 8),
                2,
                border_radius=14,
            )

    for key, label, base_color, hover_color in (
        ("play", "START GAME", (45, 150, 65), (70, 190, 90)),
        ("quit", "QUIT", (145, 50, 50), (205, 70, 70)),
    ):
        button_rect = buttons[key]
        draw_ui_button(
            screen,
            button_rect,
            label,
            base_color,
            hover_color,
            button_font,
            button_rect.collidepoint(game_mouse_x, game_mouse_y),
        )

    hint = hint_font.render(
        "WASD move  •  SPACE attack  •  E interact  •  H heal  •  I inventory  •  ESC pause",
        True,
        (190, 205, 205),
    )
    screen.blit(
        hint,
        hint.get_rect(center=(GAME_WIDTH // 2, 600)),
    )

    start_hint = hint_font.render(
        "Press ENTER or SPACE to start",
        True,
        (150, 170, 170),
    )
    screen.blit(
        start_hint,
        start_hint.get_rect(center=(GAME_WIDTH // 2, 640)),
    )


# ============================================================
# RESET PLAYER
# ============================================================

def reset_player():

    player.x = 550
    player.y = 300

    player.rect.x = 550
    player.rect.y = 300

    player.health = player.max_health

    player.direction = pygame.Vector2(
        0,
        0
    )

    player.facing_direction = "down"

    player.current_frame = 0

    player.animation_timer = 0

    player.attack_timer = 0
    player.attack_duration = 0
    player.attack_cooldown_timer = 0
    player.attack_weapon_name = None
    player.attack_has_hit = False
    

def respawn_weapons():

    weapon_pickups.clear()

    for x, y, name in weapon_spawn_data:

        weapon_pickups.append(
            WeaponPickup(x, y, name)
        )


def reset_game():
    global apple_count
    global paused
    global selected_weapon
    global inventory_open
    global nearby_weapon
    global nearby_apple
    global defeated_enemies
    global enemy_attack_lock_timer
    global game_over
    global game_won
    global menu_active
    global current_wave
    global total_waves
    global wave_defeated
    global wave_banner_timer
    global screen_fade_alpha
    global game_over_fade_alpha

    reset_player()
    respawn_weapons()
    enemies.clear()
    apples.clear()

    inventory["weapons"].clear()
    inventory["food"] = 3
    apple_count = 0
    selected_weapon = 0
    inventory_open = False
    nearby_weapon = None
    nearby_apple = None
    defeated_enemies = 0
    current_wave = 1
    total_waves = len(DIFFICULTY_WAVES[selected_difficulty])
    wave_defeated = 0
    wave_banner_timer = 1.8
    enemy_attack_lock_timer = 0.0
    game_over = False
    game_won = False
    menu_active = False
    paused = False
    screen_fade_alpha = 255
    game_over_fade_alpha = 0

    clear_effects()

    spawn_enemies()
    spawn_apples()

    # Reset the single mixer stream before starting a fresh run. Waves
    # themselves never call start_music, so the track continues naturally.
    stop_music(0)
    start_music()


def start_from_menu():
    reset_game()


def return_to_main_menu():
    global menu_active
    global paused
    global game_over
    global game_won
    global screen_fade_alpha
    global game_over_fade_alpha

    stop_music(400)
    clear_effects()
    paused = False
    game_over = False
    game_won = False
    menu_active = True
    screen_fade_alpha = 255
    game_over_fade_alpha = 0
        
        


# ============================================================
# GAME STATE
# ============================================================

running = True
game_over = False
game_won = False
menu_active = True
paused = False

while running:

    # ========================================================
    # DELTA TIME
    # ========================================================

    dt = clock.tick(60) / 1000


    # Prevent extremely large delta time values
    # after switching/resizing the window.

    if dt > 0.05:

        dt = 0.05

    if screen_fade_alpha > 0:
        screen_fade_alpha = max(0, screen_fade_alpha - int(420 * dt))

    if game_over:
        game_over_fade_alpha = min(
            140,
            game_over_fade_alpha + int(520 * dt),
        )

    if not paused and wave_banner_timer > 0:
        wave_banner_timer = max(0.0, wave_banner_timer - dt)


    # ========================================================
    # WATER ANIMATION
    # ========================================================

    if paused or menu_active or game_over:
        # Freeze ambient animation while the game is not actively running.
        water_animation_timer += 0
    else:
        water_animation_timer += dt


    if water_animation_timer >= water_animation_speed:

        water_current_frame += 1


        if water_current_frame >= 5:

            water_current_frame = 0


        water_animation_timer = 0


    # ========================================================
    # EVENTS
    # ========================================================

    for event in pygame.event.get():

        # ---------------- QUIT ----------------

        if event.type == pygame.QUIT:

            running = False


        # ====================================================
        # MAIN MENU BUTTONS
        # ====================================================

        elif (
            menu_active
            and event.type == pygame.KEYDOWN
            and event.key in (pygame.K_1, pygame.K_KP1)
        ):
            selected_difficulty = "EASY"

        elif (
            menu_active
            and event.type == pygame.KEYDOWN
            and event.key in (pygame.K_2, pygame.K_KP2)
        ):
            selected_difficulty = "MEDIUM"

        elif (
            menu_active
            and event.type == pygame.KEYDOWN
            and event.key in (pygame.K_3, pygame.K_KP3)
        ):
            selected_difficulty = "HARD"

        elif (
            menu_active
            and event.type == pygame.KEYDOWN
            and event.key in (pygame.K_RETURN, pygame.K_SPACE)
        ):
            start_from_menu()

        elif menu_active and event.type == pygame.MOUSEBUTTONDOWN:
            game_mouse_x, game_mouse_y = window_to_game_position(event.pos)
            buttons = get_menu_buttons()

            if buttons["difficulty_easy"].collidepoint(
                game_mouse_x,
                game_mouse_y,
            ):
                selected_difficulty = "EASY"
            elif buttons["difficulty_medium"].collidepoint(
                game_mouse_x,
                game_mouse_y,
            ):
                selected_difficulty = "MEDIUM"
            elif buttons["difficulty_hard"].collidepoint(
                game_mouse_x,
                game_mouse_y,
            ):
                selected_difficulty = "HARD"
            elif buttons["play"].collidepoint(game_mouse_x, game_mouse_y):
                start_from_menu()
            elif buttons["quit"].collidepoint(game_mouse_x, game_mouse_y):
                running = False


        # ====================================================
        # PAUSE / UNPAUSE
        # ====================================================

        elif (
            event.type == pygame.KEYDOWN
            and event.key == pygame.K_ESCAPE
            and not menu_active
            and not game_over
        ):
            paused = not paused

            if paused:
                inventory_open = False
                pause_music()
            else:
                resume_music()


        # ====================================================
        # PAUSE MENU BUTTONS
        # ====================================================

        elif paused and event.type == pygame.MOUSEBUTTONDOWN:
            game_mouse_x, game_mouse_y = window_to_game_position(event.pos)
            buttons = get_pause_buttons()

            if buttons["resume"].collidepoint(game_mouse_x, game_mouse_y):
                paused = False
                resume_music()
            elif buttons["restart"].collidepoint(game_mouse_x, game_mouse_y):
                reset_game()
            elif buttons["main_menu"].collidepoint(game_mouse_x, game_mouse_y):
                return_to_main_menu()
            elif buttons["quit"].collidepoint(game_mouse_x, game_mouse_y):
                running = False


        # ====================================================
        # IGNORE OTHER INPUT WHILE PAUSED
        # ====================================================

        elif (
            paused
            and event.type == pygame.KEYDOWN
            and event.key != pygame.K_F11
        ):
            # All other gameplay keys are ignored while paused.
            pass


        # ====================================================
        # GAME OVER BUTTONS
        # ====================================================

        elif game_over and event.type == pygame.MOUSEBUTTONDOWN:

            game_mouse_x, game_mouse_y = window_to_game_position(event.pos)
            buttons = get_game_over_buttons()

            if buttons["play_again"].collidepoint(game_mouse_x, game_mouse_y):
                reset_game()
            elif buttons["main_menu"].collidepoint(game_mouse_x, game_mouse_y):
                return_to_main_menu()
            elif buttons["quit"].collidepoint(game_mouse_x, game_mouse_y):
                running = False


        # ====================================================
        # FULLSCREEN TOGGLE
        # ====================================================

        elif (
            event.type == pygame.KEYDOWN
            and event.key == pygame.K_F11
        ):

            if not fullscreen:

                # Save current window size

                windowed_size = screen.get_size()

                screen = pygame.display.set_mode(
                    (0, 0),
                    pygame.FULLSCREEN
                )

                fullscreen = True

            else:

                screen = pygame.display.set_mode(
                    windowed_size,
                    pygame.RESIZABLE
                )

                fullscreen = False


        # ====================================================
        # WINDOW RESIZE
        # ====================================================

        elif (
            event.type == pygame.VIDEORESIZE
            and not fullscreen
        ):

            new_width = max(
                800,
                event.w
            )

            new_height = max(
                500,
                event.h
            )

            windowed_size = (
                new_width,
                new_height
            )

            screen = pygame.display.set_mode(
                windowed_size,
                pygame.RESIZABLE
            )


        # ====================================================
        # TEST DAMAGE
        # ====================================================

        elif (
            event.type == pygame.KEYDOWN
            and event.key == pygame.K_h
            and not game_over
            and not menu_active
            and not paused
        ):

            if apple_count > 0 and player.health < player.max_health:
                apple_count -= 1
                player.heal(30)
                play_sound("heal")
                spawn_particles(
                    player.rect.centerx,
                    player.rect.centery,
                    (110, 235, 130),
                    amount=14,
                    speed=120,
                    life=0.5,
                    size=5,
                    gravity=-40,
                )
                spawn_floating_text(
                    player.rect.centerx,
                    player.rect.top + 10,
                    "+30 HP",
                    (150, 255, 170),
                )


        # ====================================================
        # PLAYER ATTACK
        # ====================================================

        elif (
            event.type == pygame.KEYDOWN
            and event.key == pygame.K_SPACE
            and not game_over
            and not menu_active
            and not paused
        ):
            selected_name = get_selected_weapon_name()
            if selected_name and player.start_attack(selected_name):
                play_sound("attack")
                perform_player_attack()


        # ====================================================
        # WEAPON PICKUP
        # ====================================================

        elif (
            event.type == pygame.KEYDOWN
            and event.key == pygame.K_e
            and not game_over
            and not menu_active
            and not paused
        ):

            if nearby_weapon is not None:

                # --------------------------------------------
                # Check inventory space
                # --------------------------------------------

                if len(inventory["weapons"]) < 3:

                    # Add weapon to inventory

                    inventory["weapons"].append(
                        nearby_weapon.weapon_name
                    )

                    # Remove weapon from island

                    weapon_pickups.remove(
                        nearby_weapon
                    )

                    # Automatically select newly picked weapon

                    selected_weapon = (
                        len(inventory["weapons"]) - 1
                    )

                    # Pickup feedback

                    play_sound("pickup")
                    spawn_particles(
                        nearby_weapon.rect.centerx,
                        nearby_weapon.rect.centery,
                        (240, 225, 160),
                        amount=14,
                        speed=150,
                        life=0.45,
                        size=5,
                        gravity=-25,
                    )
                    spawn_floating_text(
                        nearby_weapon.rect.centerx,
                        nearby_weapon.rect.top,
                        nearby_weapon.weapon_name.upper() + " EQUIPPED",
                        (255, 235, 165),
                    )

                    # Clear nearby weapon

                    nearby_weapon = None

            elif nearby_apple is not None:
                apple_count += 1
                play_sound("pickup")
                spawn_particles(
                    nearby_apple.rect.centerx,
                    nearby_apple.rect.centery,
                    (225, 70, 70),
                    amount=12,
                    speed=130,
                    life=0.4,
                    size=4,
                    gravity=-20,
                )
                spawn_floating_text(
                    nearby_apple.rect.centerx,
                    nearby_apple.rect.top,
                    "+1 APPLE",
                    (255, 200, 190),
                )
                apples.remove(nearby_apple)
                nearby_apple = None


        # ====================================================
        # INVENTORY CONTROLS
        # ====================================================

        elif (
            not menu_active
            and not game_over
            and not paused
            and event.type == pygame.KEYDOWN
        ):

            # ------------------------------------------------
            # OPEN / CLOSE INVENTORY
            # ------------------------------------------------

            if event.key == pygame.K_i:

                inventory_open = not inventory_open


            # ------------------------------------------------
            # WEAPON 1
            # ------------------------------------------------

            elif event.key == pygame.K_1:

                if len(inventory["weapons"]) > 0:

                    selected_weapon = 0


            # ------------------------------------------------
            # WEAPON 2
            # ------------------------------------------------

            elif event.key == pygame.K_2:

                if len(inventory["weapons"]) > 1:

                    selected_weapon = 1


            # ------------------------------------------------
            # WEAPON 3
            # ------------------------------------------------

            elif event.key == pygame.K_3:

                if len(inventory["weapons"]) > 2:

                    selected_weapon = 2


    # ========================================================
    # PLAYER INPUT / MOVEMENT / ANIMATION
    # ========================================================

    if not game_over and not menu_active and not paused:
        
        player.handle_input()

        player.move(
            dt,
            colliders
        )

        player.animate(
            dt
        )

        player.update_attack(dt)
        if player.attack_timer > 0:
            perform_player_attack()
        
        # ====================================================
        # UPDATE ENEMIES
        # ====================================================

        for enemy in enemies:
            enemy.update(
                dt,
                player,
                colliders,
                enemies,
            )

        enemies[:] = [
            enemy
            for enemy in enemies
            if not (enemy.dead and enemy.death_timer <= 0)
        ]

        if not enemies:
            if current_wave < total_waves:
                current_wave += 1
                wave_defeated = 0
                wave_banner_timer = 1.8
                spawn_enemies()
            else:
                game_over = True
                game_won = True
                game_over_fade_alpha = 0
                stop_music(800)

        # ====================================================
        # UPDATE APPLES
        # ====================================================

        for apple in apples:
            apple.update(dt)

        nearby_weapon = get_nearby_weapon(
            player,
            weapon_pickups
        )
        nearby_apple = get_nearby_apple(
            player,
            apples
        )

        update_effects(dt)
        
    # ========================================================
    # CHECK PLAYER DEATH / WIN
    # ========================================================

    if not menu_active and not game_over and player.health <= 0:
        
        game_over = True
        game_won = False
        paused = False
        game_over_fade_alpha = 0
        stop_music(800)
        spawn_particles(
            player.rect.centerx,
            player.rect.centery,
            (220, 90, 90),
            amount=16,
            speed=170,
            life=0.5,
            size=5,
        )


    # ========================================================
    # CLEAR GAME SURFACE
    # ========================================================

    game_surface.fill(

        (
            40,
            120,
            200
        )

    )


    # ========================================================
    # DRAW WATER
    # ========================================================

    water_frame = water_frames[

        water_current_frame

    ]


    current_water_width = (
        water_frame.get_width()
    )

    current_water_height = (
        water_frame.get_height()
    )


    for x in range(

        0,

        GAME_WIDTH,

        current_water_width

    ):

        for y in range(

            0,

            GAME_HEIGHT,

            current_water_height

        ):

            game_surface.blit(

                water_frame,

                (x, y)

            )


    # ========================================================
    # DRAW BEACH + GRASS
    # ========================================================

    game_surface.blit(

        terrain_surface,

        (0, 0)

    )
    
    # ========================================================
    # UPDATE + DRAW WEAPON PICKUPS
    # ========================================================

    for weapon in weapon_pickups:

        if not paused and not game_over and not menu_active:
            weapon.update(dt)
        
        weapon.draw(
            game_surface
        )
        
    draw_weapon_pickup_prompt(
        game_surface,
        nearby_weapon
    )

    # ========================================================
    # DRAW APPLES
    # ========================================================

    for apple in apples:
        apple.draw(game_surface)

    draw_apple_pickup_prompt(
        game_surface,
        nearby_apple
    )
        
        
    # ========================================================
    # DRAW GRASS DETAILS
    # ========================================================

    draw_grass(

        game_surface

    )


    # ========================================================
    # DRAW TREES
    # ========================================================

    for obstacle in obstacles:

        obstacle.draw(

            game_surface

        )


    # ========================================================
    # DRAW ROCKS
    # ========================================================

    for rock in rocks:

        rock.draw(

            game_surface

        )


    # ========================================================
    # DRAW ENEMIES
    # ========================================================

    for enemy in enemies:
        enemy.draw(game_surface)


    # ========================================================
    # DRAW PLAYER
    # ========================================================

    player.draw(
        game_surface
    )


    # ========================================================
    # DRAW PARTICLE / TEXT EFFECTS
    # ========================================================

    draw_effects(game_surface)
    
    # ========================================================
    # DRAW INVENTORY
    # ========================================================

    if inventory_open:
        
        draw_inventory(
            game_surface
        )


    # ========================================================
    # DRAW HUD
    # ========================================================

    if not game_over and not menu_active:
        
        draw_health_bar(
            game_surface,
            player
        )
        draw_apples_hud(game_surface)
        draw_wave_banner(game_surface)


    # ========================================================
    # PAUSE MENU
    # ========================================================

    if paused and not game_over and not menu_active:
        draw_pause_menu(game_surface)


    # ========================================================
    # GAME OVER SCREEN
    # ========================================================

    if game_over:
        draw_game_over(
            game_surface,
            game_won,
        )
    elif menu_active:
        draw_menu(game_surface)

    if screen_fade_alpha > 0:
        fade_overlay = pygame.Surface(
            (GAME_WIDTH, GAME_HEIGHT),
            pygame.SRCALPHA,
        )
        fade_overlay.fill(
            (0, 0, 0, min(255, screen_fade_alpha))
        )
        game_surface.blit(fade_overlay, (0, 0))

    if game_over_fade_alpha > 0:
        ending_overlay = pygame.Surface(
            (GAME_WIDTH, GAME_HEIGHT),
            pygame.SRCALPHA,
        )
        ending_overlay.fill(
            (0, 0, 0, game_over_fade_alpha)
        )
        game_surface.blit(ending_overlay, (0, 0))

    # ========================================================
    # DISPLAY / FULLSCREEN SCALING
    # ========================================================

    window_width, window_height = (
        screen.get_size()
    )


    # --------------------------------------------------------
    # Keep the original 1200x700 aspect ratio.
    # --------------------------------------------------------

    scale_x = (
        window_width / GAME_WIDTH
    )

    scale_y = (
        window_height / GAME_HEIGHT
    )


    scale = min(
        scale_x,
        scale_y
    )


    scaled_width = max(
        1,
        int(
            GAME_WIDTH * scale
        )
    )

    scaled_height = max(
        1,
        int(
            GAME_HEIGHT * scale
        )
    )


    scaled_surface = pygame.transform.scale(

        game_surface,

        (
            scaled_width,
            scaled_height
        )

    )


    # ========================================================
    # CLEAR DISPLAY
    # ========================================================

    screen.fill(
        (0, 0, 0)
    )


    # ========================================================
    # CENTER GAME
    # ========================================================

    display_x = (
        window_width - scaled_width
    ) // 2

    display_y = (
        window_height - scaled_height
    ) // 2


    screen.blit(

        scaled_surface,

        (
            display_x,
            display_y
        )

    )


    # ========================================================
    # UPDATE DISPLAY
    # ========================================================

    pygame.display.flip()


# ============================================================
# QUIT
# ============================================================

pygame.quit()
