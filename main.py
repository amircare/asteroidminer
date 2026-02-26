import pygame
import os
import random
import math
import json
import socket
import threading
import subprocess
import sys

# ==================== CONSTANTS ====================
SAVES_DIR = os.path.join(os.path.dirname(__file__), "saves")
SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "settings.json")
DEFAULT_PORT = 5555

# Game states
STATE_MENU = "menu"
STATE_PLAYING = "playing"
STATE_SETTINGS = "settings"
STATE_NEW_WORLD = "new_world"
STATE_LOAD_WORLD = "load_world"
STATE_MULTIPLAYER_MENU = "multiplayer_menu"
STATE_JOIN_GAME = "join_game"
STATE_HOSTING = "hosting"
STATE_HOST_WORLD_SELECT = "host_world_select"
STATE_POWER_SHOP = "power_shop"
STATE_CONFIRM_EXIT = "confirm_exit"

# Cosmetic unlocks from quests
SHIP_COSMETICS = {
    "default": {"name": "Default", "points": [(0, -14), (8.4, 14), (-8.4, 14)]},
    "arrow": {"name": "Arrow", "points": [(0, -16), (6, -8), (10, 14), (-10, 14), (-6, -8)]},
    "wide": {"name": "Wide Wing", "points": [(0, -12), (14, 10), (8, 14), (-8, 14), (-14, 10)]},
    "needle": {"name": "Needle", "points": [(0, -18), (4, 14), (-4, 14)]},
    "delta": {"name": "Delta", "points": [(0, -14), (12, 8), (6, 14), (-6, 14), (-12, 8)]},
}

FIRE_COSMETICS = {
    "default": {"name": "Default Fire", "colors": [(255, 255, 200), (255, 165, 0), (255, 80, 0)]},
    "blue": {"name": "Blue Flame", "colors": [(200, 220, 255), (100, 150, 255), (50, 100, 255)]},
    "green": {"name": "Green Plasma", "colors": [(200, 255, 200), (100, 255, 100), (50, 200, 50)]},
    "purple": {"name": "Purple Energy", "colors": [(255, 200, 255), (200, 100, 255), (150, 50, 255)]},
    "rainbow": {"name": "Rainbow", "colors": [(255, 200, 200), (200, 255, 200), (200, 200, 255)]},
}

# Superpower definitions
SUPERPOWERS = {
    "damage_orbs": {
        "name": "Damage Orbs",
        "description": "Orbs orbit and damage",
        "base_cost": 500,
        "max_level": 5,
        "upgrade_cost_mult": 2.0,
    },
    "bullet_split": {
        "name": "Bullet Split",
        "description": "Bullets split on hit",
        "base_cost": 600,
        "max_level": 3,
        "upgrade_cost_mult": 2.5,
    },
    "auto_aim": {
        "name": "Auto Aim",
        "description": "Bullets track asteroids",
        "base_cost": 800,
        "max_level": 5,
        "upgrade_cost_mult": 2.0,
    },
    "ultra_fire": {
        "name": "Ultra Fire",
        "description": "Extreme fire rate",
        "base_cost": 700,
        "max_level": 5,
        "upgrade_cost_mult": 2.5,
    },
    "magnet": {
        "name": "Loot Magnet",
        "description": "Auto-collect loot",
        "base_cost": 550,
        "max_level": 4,
        "upgrade_cost_mult": 2.0,
    },
    "explosive_shots": {
        "name": "Explosive Shots",
        "description": "Bullets explode",
        "base_cost": 900,
        "max_level": 4,
        "upgrade_cost_mult": 2.5,
    },
    "piercing_shots": {
        "name": "Piercing Shots",
        "description": "Bullets pierce through",
        "base_cost": 1000,
        "max_level": 5,
        "upgrade_cost_mult": 3.0,
    },
}

# Ship color presets
SHIP_COLORS = [
    ("White", (255, 255, 255)),
    ("Red", (255, 80, 80)),
    ("Green", (80, 255, 80)),
    ("Blue", (80, 80, 255)),
    ("Yellow", (255, 255, 80)),
    ("Cyan", (80, 255, 255)),
    ("Magenta", (255, 80, 255)),
    ("Orange", (255, 165, 0)),
]

# ==================== CLASSES ====================
class Asteroid:
    def __init__(self, x, y, dx=None, dy=None, health=None, boss=False, golden=None):
        self.x = x
        self.y = y
        self.dx = dx if dx is not None else random.uniform(5, 30)
        self.dy = dy if dy is not None else random.uniform(5, 30)
        self.boss = boss
        self.golden = golden if golden is not None else (random.random() < 0.08)  # 8% chance
        if boss:
            self.health = health if health is not None else random.randint(40, 80)
            self.max_health = self.health
            self.radius = 32
        else:
            self.health = health if health is not None else random.randint(6, 18)
            self.max_health = self.health
            self.radius = 8
        self.particle_timer = 0.0  # For golden particle effects

    def to_dict(self):
        return {
            "x": self.x, "y": self.y, "dx": self.dx, "dy": self.dy,
            "health": self.health, "max_health": self.max_health,
            "radius": self.radius, "boss": self.boss, "golden": self.golden
        }

    @staticmethod
    def from_dict(d):
        a = Asteroid(d["x"], d["y"], d["dx"], d["dy"], d["health"], d["boss"], d.get("golden", False))
        a.max_health = d["max_health"]
        a.radius = d["radius"]
        return a

class Quest:
    QUEST_TYPES = [
        ("destroy_asteroids", "Destroy {target} asteroids", 5, 15, "ship"),
        ("destroy_boss", "Destroy {target} boss asteroids", 1, 3, "fire"),
        ("destroy_golden", "Destroy {target} golden asteroids", 2, 5, "ship"),
        ("collect_iron", "Collect {target} Iron", 10, 20, "fire"),
        ("collect_gold", "Collect {target} Gold", 5, 12, "ship"),
        ("collect_diamond", "Collect {target} Diamond", 2, 6, "fire"),
        ("earn_coins", "Earn {target} coins", 50, 200, "ship"),
    ]

    def __init__(self, quest_type=None, target=None, progress=0):
        if quest_type is None:
            qtype, desc_template, min_t, max_t, reward_type = random.choice(self.QUEST_TYPES)
            self.quest_type = qtype
            self.target = random.randint(min_t, max_t)
            self.description = desc_template.format(target=self.target)
            self.reward_type = reward_type
        else:
            self.quest_type = quest_type
            self.target = target
            self.reward_type = "ship"  # Default
            for qtype, desc_template, _, _, rtype in self.QUEST_TYPES:
                if qtype == quest_type:
                    self.description = desc_template.format(target=target)
                    self.reward_type = rtype
                    break
        self.progress = progress
        self.completed = False
        self.xp_reward = self.target * 10

    def update_progress(self, amount=1):
        if not self.completed:
            self.progress += amount
            if self.progress >= self.target:
                self.progress = self.target
                self.completed = True
                return True  # Quest just completed
        return False

    def to_dict(self):
        return {
            "quest_type": self.quest_type,
            "target": self.target,
            "progress": self.progress,
            "completed": self.completed,
            "reward_type": self.reward_type
        }

    @staticmethod
    def from_dict(d):
        q = Quest(d["quest_type"], d["target"], d["progress"])
        q.completed = d.get("completed", False)
        q.reward_type = d.get("reward_type", "ship")
        return q

class Player:
    def __init__(self, x, y):
        self.rotation = 0.0

class Button:
    def __init__(self, x, y, w, h, text, color=(80, 80, 120), hover_color=(120, 120, 180), disabled=False):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.disabled = disabled

    def draw(self, screen, font, mouse_pos):
        if self.disabled:
            color = (60, 60, 60)
        elif self.rect.collidepoint(mouse_pos):
            color = self.hover_color
        else:
            color = self.color
        pygame.draw.rect(screen, color, self.rect, border_radius=8)
        pygame.draw.rect(screen, (200, 200, 255), self.rect, 2, border_radius=8)
        text_color = (100, 100, 100) if self.disabled else (255, 255, 255)
        text_surf = font.render(self.text, True, text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def is_clicked(self, mouse_pos, clicked):
        return clicked and self.rect.collidepoint(mouse_pos) and not self.disabled

class NetworkClient:
    def __init__(self):
        self.socket = None
        self.connected = False
        self.my_id = None
        self.other_players = {}  # {id: {name, x, y, rotation, color_index}}
        self.server_addr = None
        self.receive_thread = None
        self.running = False
        self.lock = threading.Lock()

    def connect(self, host, port, player_name, color_index):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setblocking(False)
            self.server_addr = (host, port)
            self.running = True
            
            # Send join message
            join_msg = json.dumps({
                "type": "join",
                "name": player_name,
                "x": 0, "y": 0, "rotation": 0,
                "color_index": color_index
            }).encode()
            self.socket.sendto(join_msg, self.server_addr)
            self.connected = True
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    def send_update(self, x, y, rotation, color_index):
        if not self.connected:
            return
        try:
            msg = json.dumps({
                "type": "update",
                "x": x, "y": y,
                "rotation": rotation,
                "color_index": color_index
            }).encode()
            self.socket.sendto(msg, self.server_addr)
        except:
            pass

    def receive(self):
        if not self.connected:
            return
        try:
            while True:
                data, _ = self.socket.recvfrom(4096)
                msg = json.loads(data.decode())
                
                if msg.get("type") == "joined":
                    self.my_id = msg.get("id")
                elif msg.get("type") == "state":
                    with self.lock:
                        self.other_players = {}
                        for p in msg.get("players", []):
                            if p.get("id") != self.my_id:
                                self.other_players[p["id"]] = p
        except BlockingIOError:
            pass
        except:
            pass

    def get_other_players(self):
        with self.lock:
            return dict(self.other_players)

    def disconnect(self):
        if self.connected and self.socket:
            try:
                msg = json.dumps({"type": "leave"}).encode()
                self.socket.sendto(msg, self.server_addr)
            except:
                pass
        self.connected = False
        self.running = False
        if self.socket:
            self.socket.close()
            self.socket = None
        self.other_players = {}
        self.my_id = None

# ==================== SETTINGS ====================
def load_settings():
    default = {"player_name": "Player", "ship_color_index": 0}
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
                return {**default, **data}
        except:
            pass
    return default

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)

# ==================== WORLD SAVE/LOAD ====================
def get_world_files():
    if not os.path.exists(SAVES_DIR):
        os.makedirs(SAVES_DIR)
    return [f[:-5] for f in os.listdir(SAVES_DIR) if f.endswith(".json")]

def save_world(world_name, game_state):
    filepath = os.path.join(SAVES_DIR, f"{world_name}.json")
    data = {
        "world_name": world_name,
        "worldxposition": game_state["worldxposition"],
        "worldyposition": game_state["worldyposition"],
        "cam_vx": game_state["cam_vx"],
        "cam_vy": game_state["cam_vy"],
        "currency": game_state["currency"],
        "currency_display": game_state.get("currency_display", game_state["currency"]),
        "upgrades": game_state["upgrades"],
        "carried_items": game_state["carried_items"],
        "floating_loot": game_state.get("floating_loot", []),
        "asteroids": [a.to_dict() for a in game_state["asteroids"]],
        "player_rotation": game_state["player"].rotation,
        "xp": game_state.get("xp", 0),
        "level": game_state.get("level", 1),
        "quests": [q.to_dict() for q in game_state.get("quests", [])],
        "powers": game_state.get("powers", {"owned": [], "equipped": None, "levels": {}}),
        "cosmetics": game_state.get("cosmetics", {
            "unlocked_ships": ["default"],
            "unlocked_fires": ["default"],
            "equipped_ship": "default",
            "equipped_fire": "default",
        }),
        "power_shop_materials": game_state.get("power_shop_materials", {"Iron": 0, "Copper": 0, "Titanium": 0, "Uranium": 0, "Power Core": 0}),
    }
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

def load_world(world_name):
    filepath = os.path.join(SAVES_DIR, f"{world_name}.json")
    with open(filepath, "r") as f:
        data = json.load(f)
    return data

def delete_world(world_name):
    filepath = os.path.join(SAVES_DIR, f"{world_name}.json")
    if os.path.exists(filepath):
        os.remove(filepath)

def create_new_game_state():
    return {
        "worldxposition": 0.0,
        "worldyposition": 0.0,
        "cam_vx": 0.0,
        "cam_vy": 0.0,
        "currency": 0,
        "currency_display": 0.0,  # For smooth animation
        "upgrades": {"speed": 0, "storage": 0, "shot_damage": 0, "shoot_speed": 0, "powers_unlocked": False},
        "carried_items": [],
        "floating_loot": [],  # Loot items floating in space that can be picked up
        "asteroids": [Asteroid(random.randint(0, 1000), random.randint(0, 1000)) for _ in range(10)],
        "player": Player(500, 500),
        "bullets": [],
        "floating_texts": [],
        "time_since_shot": 0.0,
        "spawn_timer": 0.0,
        "xp": 0,
        "level": 1,
        "quests": [Quest(), Quest(), Quest()],  # Start with 3 random quests
        "gold_particles": [],  # For golden asteroid particle effects
        "powers": {
            "owned": [],  # List of owned power IDs
            "equipped": None,  # Currently equipped power ID
            "levels": {},  # {power_id: level}
        },
        "power_effects": [],  # Active power effects (orbs, shields, etc.)
        "cosmetics": {
            "unlocked_ships": ["default"],
            "unlocked_fires": ["default"],
            "equipped_ship": "default",
            "equipped_fire": "default",
        },
        "power_shop_materials": {"Iron": 0, "Copper": 0, "Titanium": 0, "Uranium": 0, "Power Core": 0},
        "coin_animations": [],  # For selling animation
        "drop_cooldown": 0.0,  # Cooldown to prevent instant pickup after drop
    }

def load_game_state_from_data(data):
    state = create_new_game_state()
    state["worldxposition"] = data["worldxposition"]
    state["worldyposition"] = data["worldyposition"]
    state["cam_vx"] = data["cam_vx"]
    state["cam_vy"] = data["cam_vy"]
    state["currency"] = data["currency"]
    state["currency_display"] = data.get("currency_display", data["currency"])
    state["upgrades"] = data["upgrades"]
    # Ensure powers_unlocked exists in upgrades
    if "powers_unlocked" not in state["upgrades"]:
        state["upgrades"]["powers_unlocked"] = False
    state["carried_items"] = data["carried_items"]
    state["floating_loot"] = data.get("floating_loot", [])  # Load floating loot if exists
    state["asteroids"] = [Asteroid.from_dict(a) for a in data["asteroids"]]
    state["player"].rotation = data["player_rotation"]
    state["xp"] = data.get("xp", 0)
    state["level"] = data.get("level", 1)
    state["quests"] = [Quest.from_dict(q) for q in data.get("quests", [])]
    if not state["quests"]:
        state["quests"] = [Quest(), Quest(), Quest()]
    state["powers"] = data.get("powers", {"owned": [], "equipped": None, "levels": {}})
    state["cosmetics"] = data.get("cosmetics", {
        "unlocked_ships": ["default"],
        "unlocked_fires": ["default"],
        "equipped_ship": "default",
        "equipped_fire": "default",
    })
    state["power_shop_materials"] = data.get("power_shop_materials", {"Iron": 0, "Copper": 0, "Titanium": 0, "Uranium": 0, "Power Core": 0})
    return state
# ==================== SCALING UTILITIES ====================
def get_screen_center(screen_w, screen_h):
    """Get center coordinates for current screen"""
    return screen_w // 2, screen_h // 2

def update_power_effects(game_state, dt, CX, CY):
    """Update active power effects"""
    gs = game_state
    powers = gs["powers"]
    equipped = powers.get("equipped")
    
    if not equipped or equipped not in powers["owned"]:
        gs["power_effects"] = []
        return
    
    level = powers["levels"].get(equipped, 1)
    
    # Damage Orbs
    if equipped == "damage_orbs":
        num_orbs = 2 + level  # 3-7 orbs
        orb_radius = 60 + level * 10
        orb_speed = 2.0
        
        # Initialize orbs if needed
        if len(gs["power_effects"]) != num_orbs:
            gs["power_effects"] = []
            for i in range(num_orbs):
                angle = (i / num_orbs) * 2 * math.pi
                gs["power_effects"].append({
                    "type": "orb",
                    "angle": angle,
                    "radius": orb_radius,
                    "damage": 1 + level * 0.5  # Reduced from 2 + level
                })
        
        # Update orb positions and check collisions
        for orb in gs["power_effects"]:
            orb["angle"] += orb_speed * dt
            orb_x = gs["worldxposition"] + math.cos(orb["angle"]) * orb["radius"]
            orb_y = gs["worldyposition"] + math.sin(orb["angle"]) * orb["radius"]
            
            # Check asteroid collisions
            for asteroid in gs["asteroids"][:]:
                dist = math.hypot(asteroid.x - orb_x, asteroid.y - orb_y)
                if dist < asteroid.radius + 8:
                    damage = orb["damage"] * dt * 3  # Reduced from 10 to 3
                    asteroid.health -= damage
                    if asteroid.health <= 0:
                        # Destroy asteroid properly
                        asteroid.health = 0
    
    # Auto Aim
    elif equipped == "auto_aim":
        gs["power_effects"] = [{"type": "auto_aim", "strength": 0.3 + level * 0.15}]
    
    # Magnet - pull loot items toward player
    elif equipped == "magnet":
        magnet_range = 150 + level * 50
        magnet_strength = 200 + level * 100
        gs["power_effects"] = [{"type": "magnet", "range": magnet_range, "strength": magnet_strength}]
    
    # Ultra Fire (handled in shooting code)
    elif equipped == "ultra_fire":
        gs["power_effects"] = [{"type": "ultra_fire", "multiplier": 2 + level}]
    
    # Piercing Shots
    elif equipped == "piercing_shots":
        gs["power_effects"] = [{"type": "piercing", "pierce_count": level}]
    
    else:
        gs["power_effects"] = []

def render_power_effects(screen, game_state, CX, CY, player_rotation):
    """Render visual effects for active powers"""
    gs = game_state
    powers = gs["powers"]
    equipped = powers.get("equipped")
    
    if not equipped:
        return
    
    # Render damage orbs
    if equipped == "damage_orbs":
        for orb in gs["power_effects"]:
            if orb["type"] == "orb":
                orb_x = gs["worldxposition"] + math.cos(orb["angle"]) * orb["radius"]
                orb_y = gs["worldyposition"] + math.sin(orb["angle"]) * orb["radius"]
                screen_x = int(orb_x - gs["worldxposition"] + CX)
                screen_y = int(orb_y - gs["worldyposition"] + CY)
                
                # Draw glowing orb
                pygame.draw.circle(screen, (255, 150, 50), (screen_x, screen_y), 10)
                pygame.draw.circle(screen, (255, 200, 100), (screen_x, screen_y), 6)
                pygame.draw.circle(screen, (255, 255, 150), (screen_x, screen_y), 3)
    
    # Render magnet field
    elif equipped == "magnet":
        if gs["power_effects"] and gs["power_effects"][0]["type"] == "magnet":
            magnet_range = gs["power_effects"][0]["range"]
            magnet_surf = pygame.Surface((magnet_range * 2, magnet_range * 2), pygame.SRCALPHA)
            pygame.draw.circle(magnet_surf, (255, 255, 100, 30), (magnet_range, magnet_range), magnet_range)
            pygame.draw.circle(magnet_surf, (255, 255, 150, 60), (magnet_range, magnet_range), magnet_range, 2)
            screen.blit(magnet_surf, (CX - magnet_range, CY - magnet_range))

# ==================== MAIN GAME ====================
def main():
    pygame.init()
    
    # Get display info for fullscreen
    display_info = pygame.display.Info()
    SCREEN_W, SCREEN_H = display_info.current_w, display_info.current_h
    
    # Create fullscreen display at native resolution
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.FULLSCREEN)
    pygame.display.set_caption("Asteroid Miner")
    clock = pygame.time.Clock()
    
    # Center coordinates
    CX, CY = SCREEN_W // 2, SCREEN_H // 2

    # Load textures and fonts
    asteroid_img = pygame.image.load(os.path.join("textures", "asteroid.png")).convert_alpha()
    font = pygame.font.SysFont(None, 24)
    title_font = pygame.font.SysFont(None, 64)
    medium_font = pygame.font.SysFont(None, 36)

    # Game state
    current_state = STATE_MENU
    game_state = None
    current_world_name = None
    settings = load_settings()

    # Input state for text fields
    text_input = ""
    text_input_active = False
    selected_world_index = 0
    world_list = []

    # Color constants
    color_map = {
        "Iron": (150, 150, 150),
        "Copper": (184, 115, 51),
        "Gold": (212, 175, 55),
        "Titanium": (180, 180, 220),
        "Platinum": (200, 200, 255),
        "Uranium": (80, 255, 80),
        "Diamond": (180, 255, 255),
        "Power Core": (100, 255, 100),
    }

    # Game constants
    bullet_speed = 900.0
    bullet_life = 2.0
    base_x = 200.0
    base_y = 200.0
    base_sell_radius = 120.0
    
    # Power shop location (near base)
    power_shop_x = 400.0
    power_shop_y = 200.0
    power_shop_radius = 100.0
    max_asteroids = 28
    spawn_interval = 0.18

    # Multiplayer
    network_client = NetworkClient()
    server_process = None
    server_ip = "localhost"
    server_port = str(DEFAULT_PORT)
    mp_input_field = 0  # 0 = IP, 1 = Port
    mp_status = ""
    network_update_timer = 0.0
    
    # Background asteroids for menu
    bg_asteroids = []
    for _ in range(15):
        bg_asteroids.append({
            "x": random.randint(0, SCREEN_W),
            "y": random.randint(0, SCREEN_H),
            "vx": random.uniform(-50, 50),
            "vy": random.uniform(-50, 50),
            "size": random.randint(20, 60),
            "rotation": random.uniform(0, 360),
            "rot_speed": random.uniform(-30, 30)
        })

    running = True

    # ==================== MOBILE CONTROLS (REMOVED) ====================


    while running:
        dt = clock.tick(60) / 1000.0
        mouse_pos = pygame.mouse.get_pos()
        mouse_clicked = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_clicked = True
            elif event.type == pygame.KEYDOWN:
                if text_input_active:
                    if event.key == pygame.K_BACKSPACE:
                        text_input = text_input[:-1]
                    elif event.key == pygame.K_RETURN:
                        text_input_active = False
                    elif event.key == pygame.K_ESCAPE:
                        text_input_active = False
                        text_input = ""
                    elif len(text_input) < 20 and event.unicode.isprintable():
                        text_input += event.unicode
                elif current_state == STATE_POWER_SHOP and event.key == pygame.K_ESCAPE:
                    current_state = STATE_PLAYING
                elif current_state == STATE_PLAYING and event.key == pygame.K_ESCAPE:
                    current_state = STATE_CONFIRM_EXIT
                elif current_state == STATE_CONFIRM_EXIT and event.key == pygame.K_ESCAPE:
                    current_state = STATE_PLAYING
                elif current_state == STATE_PLAYING and event.key == pygame.K_F11:
                    # Toggle fullscreen (exit to windowed mode)
                    running = False
                elif current_state in [STATE_MULTIPLAYER_MENU, STATE_JOIN_GAME, STATE_HOSTING, STATE_HOST_WORLD_SELECT] and event.key == pygame.K_ESCAPE:
                    if network_client.connected:
                        network_client.disconnect()
                    if server_process:
                        server_process.terminate()
                        server_process = None
                    current_state = STATE_MENU
                    mp_status = ""
                elif current_state == STATE_LOAD_WORLD:
                    if event.key == pygame.K_UP and selected_world_index > 0:
                        selected_world_index -= 1
                    elif event.key == pygame.K_DOWN and selected_world_index < len(world_list) - 1:
                        selected_world_index += 1
                    elif event.key == pygame.K_DELETE and world_list:
                        delete_world(world_list[selected_world_index])
                        world_list = get_world_files()
                        selected_world_index = min(selected_world_index, max(0, len(world_list) - 1))
                    elif event.key == pygame.K_ESCAPE:
                        current_state = STATE_MENU


        screen.fill((10, 10, 30))
        
        # Update and draw background asteroids for menu states
        if current_state in [STATE_MENU, STATE_NEW_WORLD, STATE_LOAD_WORLD, STATE_SETTINGS, STATE_MULTIPLAYER_MENU, STATE_JOIN_GAME, STATE_HOST_WORLD_SELECT]:
            for bg_ast in bg_asteroids:
                bg_ast["x"] += bg_ast["vx"] * dt
                bg_ast["y"] += bg_ast["vy"] * dt
                bg_ast["rotation"] += bg_ast["rot_speed"] * dt
                
                # Wrap around screen
                if bg_ast["x"] < -bg_ast["size"]:
                    bg_ast["x"] = SCREEN_W + bg_ast["size"]
                elif bg_ast["x"] > SCREEN_W + bg_ast["size"]:
                    bg_ast["x"] = -bg_ast["size"]
                if bg_ast["y"] < -bg_ast["size"]:
                    bg_ast["y"] = SCREEN_H + bg_ast["size"]
                elif bg_ast["y"] > SCREEN_H + bg_ast["size"]:
                    bg_ast["y"] = -bg_ast["size"]
                
                # Draw asteroid
                img = pygame.transform.scale(asteroid_img, (bg_ast["size"], bg_ast["size"]))
                img = pygame.transform.rotate(img, bg_ast["rotation"])
                img.set_alpha(80)  # Semi-transparent
                screen.blit(img, (int(bg_ast["x"] - bg_ast["size"]//2), int(bg_ast["y"] - bg_ast["size"]//2)))

        # ==================== MENU STATE ====================
        if current_state == STATE_MENU:
            title = title_font.render("ASTEROID MINER", True, (255, 220, 100))
            screen.blit(title, (CX - title.get_width() // 2, 150))

            name_text = medium_font.render(f"Welcome, {settings['player_name']}!", True, (200, 200, 255))
            screen.blit(name_text, (CX - name_text.get_width() // 2, 230))

            btn_w, btn_h = 250, 50
            btn_x = CX - btn_w // 2
            buttons = [
                Button(btn_x, 320, btn_w, btn_h, "New World"),
                Button(btn_x, 390, btn_w, btn_h, "Load World"),
                Button(btn_x, 460, btn_w, btn_h, "Settings"),
                Button(btn_x, 530, btn_w, btn_h, "Multiplayer"),
                Button(btn_x, 600, btn_w, btn_h, "Quit", color=(120, 60, 60), hover_color=(180, 80, 80)),
            ]

            for btn in buttons:
                btn.draw(screen, font, mouse_pos)

            if mouse_clicked:
                if buttons[0].is_clicked(mouse_pos, True):
                    current_state = STATE_NEW_WORLD
                    text_input = ""
                    text_input_active = True
                elif buttons[1].is_clicked(mouse_pos, True):
                    current_state = STATE_LOAD_WORLD
                    world_list = get_world_files()
                    selected_world_index = 0
                elif buttons[2].is_clicked(mouse_pos, True):
                    current_state = STATE_SETTINGS
                elif buttons[3].is_clicked(mouse_pos, True):
                    current_state = STATE_MULTIPLAYER_MENU
                    mp_status = ""
                elif buttons[4].is_clicked(mouse_pos, True):
                    running = False

        # ==================== NEW WORLD STATE ====================
        elif current_state == STATE_NEW_WORLD:
            title = title_font.render("NEW WORLD", True, (255, 220, 100))
            screen.blit(title, (CX - title.get_width() // 2, 150))

            prompt = medium_font.render("Enter world name:", True, (200, 200, 255))
            screen.blit(prompt, (CX - prompt.get_width() // 2, 300))

            input_rect = pygame.Rect(CX - 150, 360, 300, 40)
            pygame.draw.rect(screen, (40, 40, 80), input_rect, border_radius=5)
            pygame.draw.rect(screen, (100, 100, 200) if text_input_active else (80, 80, 120), input_rect, 2, border_radius=5)
            cursor = "|" if text_input_active and int(pygame.time.get_ticks() / 500) % 2 == 0 else ""
            text_surf = medium_font.render(text_input + cursor, True, (255, 255, 255))
            screen.blit(text_surf, (input_rect.x + 10, input_rect.y + 8))

            if input_rect.collidepoint(mouse_pos) and mouse_clicked:
                text_input_active = True

            create_btn = Button(CX - 130, 450, 120, 45, "Create")
            cancel_btn = Button(CX + 10, 450, 120, 45, "Cancel", color=(120, 60, 60), hover_color=(180, 80, 80))
            create_btn.draw(screen, font, mouse_pos)
            cancel_btn.draw(screen, font, mouse_pos)

            if mouse_clicked:
                if create_btn.is_clicked(mouse_pos, True) and text_input.strip():
                    current_world_name = text_input.strip()
                    game_state = create_new_game_state()
                    save_world(current_world_name, game_state)
                    
                    # Check if we're creating for hosting
                    if mp_status == "hosting_new":
                        mp_status = "Starting server..."
                        try:
                            server_script = os.path.join(os.path.dirname(__file__), "server.py")
                            server_process = subprocess.Popen(
                                [sys.executable, server_script, str(DEFAULT_PORT)],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL
                            )
                            import time
                            time.sleep(0.5)
                            if network_client.connect("localhost", DEFAULT_PORT, settings["player_name"], settings["ship_color_index"]):
                                current_state = STATE_PLAYING
                                mp_status = ""
                            else:
                                mp_status = "Failed to connect"
                                if server_process:
                                    server_process.terminate()
                                    server_process = None
                                current_state = STATE_MULTIPLAYER_MENU
                        except Exception as e:
                            mp_status = f"Error: {str(e)[:30]}"
                            current_state = STATE_MULTIPLAYER_MENU
                    else:
                        current_state = STATE_PLAYING
                    text_input = ""
                elif cancel_btn.is_clicked(mouse_pos, True):
                    if mp_status == "hosting_new":
                        current_state = STATE_HOST_WORLD_SELECT
                        mp_status = ""
                    else:
                        current_state = STATE_MENU
                    text_input = ""

        # ==================== LOAD WORLD STATE ====================
        elif current_state == STATE_LOAD_WORLD:
            title = title_font.render("LOAD WORLD", True, (255, 220, 100))
            screen.blit(title, (CX - title.get_width() // 2, 100))

            if not world_list:
                no_worlds = medium_font.render("No saved worlds found.", True, (180, 180, 180))
                screen.blit(no_worlds, (CX - no_worlds.get_width() // 2, 300))
            else:
                list_y = 200
                for i, world_name in enumerate(world_list):
                    y = list_y + i * 45
                    if y > 500:
                        break
                    rect = pygame.Rect(CX - 200, y, 400, 40)
                    if i == selected_world_index:
                        pygame.draw.rect(screen, (60, 60, 120), rect, border_radius=5)
                    pygame.draw.rect(screen, (100, 100, 200), rect, 2, border_radius=5)
                    text = medium_font.render(world_name, True, (255, 255, 255))
                    screen.blit(text, (rect.x + 15, rect.y + 8))

                    if rect.collidepoint(mouse_pos) and mouse_clicked:
                        selected_world_index = i

                hint = font.render("UP/DOWN to select, DELETE to remove, click Load to play", True, (150, 150, 150))
                screen.blit(hint, (CX - hint.get_width() // 2, 550))

            load_btn = Button(CX - 130, 600, 120, 45, "Load", disabled=len(world_list) == 0)
            back_btn = Button(CX + 10, 600, 120, 45, "Back", color=(120, 60, 60), hover_color=(180, 80, 80))
            load_btn.draw(screen, font, mouse_pos)
            back_btn.draw(screen, font, mouse_pos)

            if mouse_clicked:
                if load_btn.is_clicked(mouse_pos, True) and world_list:
                    current_world_name = world_list[selected_world_index]
                    data = load_world(current_world_name)
                    game_state = load_game_state_from_data(data)
                    current_state = STATE_PLAYING
                elif back_btn.is_clicked(mouse_pos, True):
                    current_state = STATE_MENU

        # ==================== SETTINGS STATE ====================
        elif current_state == STATE_SETTINGS:
            title = title_font.render("SETTINGS", True, (255, 220, 100))
            screen.blit(title, (CX - title.get_width() // 2, 100))

            name_label = medium_font.render("Player Name:", True, (200, 200, 255))
            screen.blit(name_label, (CX - 200, 220))

            name_rect = pygame.Rect(CX - 200, 260, 300, 40)
            pygame.draw.rect(screen, (40, 40, 80), name_rect, border_radius=5)
            pygame.draw.rect(screen, (100, 100, 200) if text_input_active else (80, 80, 120), name_rect, 2, border_radius=5)

            display_text = text_input if text_input_active else settings["player_name"]
            cursor = "|" if text_input_active and int(pygame.time.get_ticks() / 500) % 2 == 0 else ""
            text_surf = medium_font.render(display_text + cursor, True, (255, 255, 255))
            screen.blit(text_surf, (name_rect.x + 10, name_rect.y + 8))

            if name_rect.collidepoint(mouse_pos) and mouse_clicked:
                text_input_active = True
                text_input = settings["player_name"]

            color_label = medium_font.render("Ship Color:", True, (200, 200, 255))
            screen.blit(color_label, (CX - 200, 340))

            color_idx = settings["ship_color_index"]
            color_name, color_rgb = SHIP_COLORS[color_idx]

            preview_rect = pygame.Rect(CX - 200, 380, 60, 60)
            pygame.draw.rect(screen, color_rgb, preview_rect, border_radius=5)
            pygame.draw.rect(screen, (200, 200, 255), preview_rect, 2, border_radius=5)

            color_text = medium_font.render(color_name, True, (255, 255, 255))
            screen.blit(color_text, (CX - 120, 400))

            prev_btn = Button(CX + 50, 385, 50, 50, "<")
            next_btn = Button(CX + 110, 385, 50, 50, ">")
            prev_btn.draw(screen, font, mouse_pos)
            next_btn.draw(screen, font, mouse_pos)

            if mouse_clicked:
                if prev_btn.is_clicked(mouse_pos, True):
                    settings["ship_color_index"] = (color_idx - 1) % len(SHIP_COLORS)
                    save_settings(settings)
                elif next_btn.is_clicked(mouse_pos, True):
                    settings["ship_color_index"] = (color_idx + 1) % len(SHIP_COLORS)
                    save_settings(settings)

            save_name_btn = Button(CX + 120, 260, 80, 40, "Save")
            save_name_btn.draw(screen, font, mouse_pos)

            if mouse_clicked and save_name_btn.is_clicked(mouse_pos, True) and text_input.strip():
                settings["player_name"] = text_input.strip()
                save_settings(settings)
                text_input_active = False
                text_input = ""

            back_btn = Button(CX - 60, 500, 120, 45, "Back", color=(80, 80, 120), hover_color=(120, 120, 180))
            back_btn.draw(screen, font, mouse_pos)

            if mouse_clicked and back_btn.is_clicked(mouse_pos, True):
                if text_input_active and text_input.strip():
                    settings["player_name"] = text_input.strip()
                    save_settings(settings)
                text_input_active = False
                text_input = ""
                current_state = STATE_MENU

        # ==================== MULTIPLAYER MENU STATE ====================
        elif current_state == STATE_MULTIPLAYER_MENU:
            title = title_font.render("MULTIPLAYER", True, (255, 220, 100))
            screen.blit(title, (CX - title.get_width() // 2, 150))

            btn_w, btn_h = 250, 50
            btn_x = CX - btn_w // 2
            host_btn = Button(btn_x, 280, btn_w, btn_h, "Host Game")
            join_btn = Button(btn_x, 350, btn_w, btn_h, "Join Game")
            back_btn = Button(btn_x, 420, btn_w, btn_h, "Back", color=(120, 60, 60), hover_color=(180, 80, 80))

            host_btn.draw(screen, font, mouse_pos)
            join_btn.draw(screen, font, mouse_pos)
            back_btn.draw(screen, font, mouse_pos)

            if mp_status:
                status_surf = font.render(mp_status, True, (255, 200, 100))
                screen.blit(status_surf, (CX - status_surf.get_width() // 2, 500))

            hint = font.render("ESC to go back", True, (150, 150, 150))
            screen.blit(hint, (CX - hint.get_width() // 2, SCREEN_H - 50))

            if mouse_clicked:
                if host_btn.is_clicked(mouse_pos, True):
                    # Go to world selection for hosting
                    current_state = STATE_HOST_WORLD_SELECT
                    world_list = get_world_files()
                    selected_world_index = 0
                    mp_status = ""
                elif join_btn.is_clicked(mouse_pos, True):
                    current_state = STATE_JOIN_GAME
                    server_ip = "localhost"
                    server_port = str(DEFAULT_PORT)
                    mp_input_field = 0
                elif back_btn.is_clicked(mouse_pos, True):
                    current_state = STATE_MENU

        # ==================== HOST WORLD SELECT STATE ====================
        elif current_state == STATE_HOST_WORLD_SELECT:
            title = title_font.render("SELECT WORLD TO HOST", True, (255, 220, 100))
            screen.blit(title, (CX - title.get_width() // 2, 100))

            if not world_list:
                no_worlds = medium_font.render("No saved worlds found.", True, (180, 180, 180))
                screen.blit(no_worlds, (CX - no_worlds.get_width() // 2, 300))
            else:
                list_y = 200
                for i, world_name in enumerate(world_list):
                    y = list_y + i * 45
                    if y > 450:
                        break
                    rect = pygame.Rect(CX - 200, y, 400, 40)
                    if i == selected_world_index:
                        pygame.draw.rect(screen, (60, 60, 120), rect, border_radius=5)
                    pygame.draw.rect(screen, (100, 100, 200), rect, 2, border_radius=5)
                    text = medium_font.render(world_name, True, (255, 255, 255))
                    screen.blit(text, (rect.x + 15, rect.y + 8))

                    if rect.collidepoint(mouse_pos) and mouse_clicked:
                        selected_world_index = i

                hint = font.render("UP/DOWN to select, click Host to start server", True, (150, 150, 150))
                screen.blit(hint, (CX - hint.get_width() // 2, 520))

            # Buttons
            host_existing_btn = Button(CX - 260, 580, 160, 45, "Host Selected", disabled=len(world_list) == 0)
            new_world_btn = Button(CX - 80, 580, 160, 45, "New World")
            back_btn = Button(CX + 100, 580, 160, 45, "Back", color=(120, 60, 60), hover_color=(180, 80, 80))
            
            host_existing_btn.draw(screen, font, mouse_pos)
            new_world_btn.draw(screen, font, mouse_pos)
            back_btn.draw(screen, font, mouse_pos)

            if mp_status:
                status_surf = font.render(mp_status, True, (255, 200, 100))
                screen.blit(status_surf, (CX - status_surf.get_width() // 2, 650))

            if mouse_clicked:
                if host_existing_btn.is_clicked(mouse_pos, True) and world_list:
                    # Load selected world and start server
                    mp_status = "Starting server..."
                    try:
                        server_script = os.path.join(os.path.dirname(__file__), "server.py")
                        server_process = subprocess.Popen(
                            [sys.executable, server_script, str(DEFAULT_PORT)],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                        import time
                        time.sleep(0.5)
                        if network_client.connect("localhost", DEFAULT_PORT, settings["player_name"], settings["ship_color_index"]):
                            current_world_name = world_list[selected_world_index]
                            data = load_world(current_world_name)
                            game_state = load_game_state_from_data(data)
                            current_state = STATE_PLAYING
                            mp_status = ""
                        else:
                            mp_status = "Failed to connect to server"
                            if server_process:
                                server_process.terminate()
                                server_process = None
                    except Exception as e:
                        mp_status = f"Error: {str(e)[:30]}"
                elif new_world_btn.is_clicked(mouse_pos, True):
                    # Create new world for hosting
                    current_state = STATE_NEW_WORLD
                    text_input = ""
                    text_input_active = True
                    # Set flag to start server after world creation
                    mp_status = "hosting_new"
                elif back_btn.is_clicked(mouse_pos, True):
                    current_state = STATE_MULTIPLAYER_MENU
                    mp_status = ""

        # ==================== JOIN GAME STATE ====================
        elif current_state == STATE_JOIN_GAME:
            title = title_font.render("JOIN GAME", True, (255, 220, 100))
            screen.blit(title, (CX - title.get_width() // 2, 150))

            # IP Address input
            ip_label = medium_font.render("Server IP:", True, (200, 200, 255))
            screen.blit(ip_label, (CX - 200, 260))
            ip_rect = pygame.Rect(CX - 200, 300, 250, 40)
            pygame.draw.rect(screen, (40, 40, 80), ip_rect, border_radius=5)
            pygame.draw.rect(screen, (100, 100, 200) if mp_input_field == 0 else (80, 80, 120), ip_rect, 2, border_radius=5)
            cursor_ip = "|" if mp_input_field == 0 and int(pygame.time.get_ticks() / 500) % 2 == 0 else ""
            ip_surf = medium_font.render(server_ip + cursor_ip, True, (255, 255, 255))
            screen.blit(ip_surf, (ip_rect.x + 10, ip_rect.y + 8))

            # Port input
            port_label = medium_font.render("Port:", True, (200, 200, 255))
            screen.blit(port_label, (CX + 70, 260))
            port_rect = pygame.Rect(CX + 70, 300, 100, 40)
            pygame.draw.rect(screen, (40, 40, 80), port_rect, border_radius=5)
            pygame.draw.rect(screen, (100, 100, 200) if mp_input_field == 1 else (80, 80, 120), port_rect, 2, border_radius=5)
            cursor_port = "|" if mp_input_field == 1 and int(pygame.time.get_ticks() / 500) % 2 == 0 else ""
            port_surf = medium_font.render(server_port + cursor_port, True, (255, 255, 255))
            screen.blit(port_surf, (port_rect.x + 10, port_rect.y + 8))

            # Handle text input for IP/Port
            for event in pygame.event.get(pygame.KEYDOWN):
                if event.key == pygame.K_TAB:
                    mp_input_field = 1 - mp_input_field
                elif event.key == pygame.K_BACKSPACE:
                    if mp_input_field == 0:
                        server_ip = server_ip[:-1]
                    else:
                        server_port = server_port[:-1]
                elif event.unicode.isprintable() and len(event.unicode) > 0:
                    if mp_input_field == 0 and len(server_ip) < 45:
                        server_ip += event.unicode
                    elif mp_input_field == 1 and len(server_port) < 5 and event.unicode.isdigit():
                        server_port += event.unicode

            if ip_rect.collidepoint(mouse_pos) and mouse_clicked:
                mp_input_field = 0
            if port_rect.collidepoint(mouse_pos) and mouse_clicked:
                mp_input_field = 1

            # Buttons
            connect_btn = Button(CX - 130, 400, 120, 45, "Connect")
            back_btn = Button(CX + 10, 400, 120, 45, "Back", color=(120, 60, 60), hover_color=(180, 80, 80))
            connect_btn.draw(screen, font, mouse_pos)
            back_btn.draw(screen, font, mouse_pos)

            if mp_status:
                status_surf = font.render(mp_status, True, (255, 200, 100))
                screen.blit(status_surf, (CX - status_surf.get_width() // 2, 480))

            hint = font.render("TAB to switch fields, ESC to go back", True, (150, 150, 150))
            screen.blit(hint, (CX - hint.get_width() // 2, SCREEN_H - 50))

            if mouse_clicked:
                if connect_btn.is_clicked(mouse_pos, True):
                    try:
                        port = int(server_port) if server_port else DEFAULT_PORT
                        mp_status = "Connecting..."
                        if network_client.connect(server_ip, port, settings["player_name"], settings["ship_color_index"]):
                            game_state = create_new_game_state()
                            current_world_name = "Multiplayer"
                            current_state = STATE_PLAYING
                            mp_status = ""
                        else:
                            mp_status = "Connection failed"
                    except Exception as e:
                        mp_status = f"Error: {str(e)[:30]}"
                elif back_btn.is_clicked(mouse_pos, True):
                    current_state = STATE_MULTIPLAYER_MENU
                    mp_status = ""

        # ==================== PLAYING STATE ====================
        elif current_state == STATE_PLAYING and game_state:
            gs = game_state
            player = gs["player"]
            asteroids = gs["asteroids"]
            bullets = gs["bullets"]
            carried_items = gs["carried_items"]
            floating_texts = gs["floating_texts"]
            upgrades = gs["upgrades"]

            for asteroid in asteroids[:]:
                asteroid.x += asteroid.dx * dt
                asteroid.y += asteroid.dy * dt
                dist = math.hypot(asteroid.x - gs["worldxposition"], asteroid.y - gs["worldyposition"])
                if dist > 1200:
                    asteroids.remove(asteroid)

            cam_accel = 1200.0 + 40 * upgrades.get("speed", 0)
            cam_max_speed = 800.0 + 20 * upgrades.get("speed", 0)
            cam_friction = 6.0
            rot_speed = math.radians(180)

            KEY = pygame.key.get_pressed()

            move_x = 0
            move_y = 0

            # ----- KEYBOARD CONTROLS -----
            if KEY[pygame.K_a]:
                move_x -= 1
            if KEY[pygame.K_d]:
                move_x += 1
            if KEY[pygame.K_w]:
                move_y -= 1

            # Apply rotation
            player.rotation += move_x * rot_speed * dt

            # Forward thrust
            fx = math.sin(player.rotation)
            fy = -math.cos(player.rotation)

            if move_y < -0.2:
                gs["cam_vx"] += fx * cam_accel * dt
                gs["cam_vy"] += fy * cam_accel * dt


            gs["cam_vx"] = max(-cam_max_speed, min(cam_max_speed, gs["cam_vx"]))
            gs["cam_vy"] = max(-cam_max_speed, min(cam_max_speed, gs["cam_vy"]))

            gs["cam_vx"] -= gs["cam_vx"] * min(1.0, cam_friction * dt)
            gs["cam_vy"] -= gs["cam_vy"] * min(1.0, cam_friction * dt)

            gs["worldxposition"] += gs["cam_vx"] * dt
            gs["worldyposition"] += gs["cam_vy"] * dt

            gs["time_since_shot"] += dt

            fire_cooldown = max(0.08, 0.8 - 0.08 * upgrades.get("shoot_speed", 0))
            
            # Ultra Fire power
            equipped_power = gs["powers"].get("equipped")
            if equipped_power == "ultra_fire":
                power_level = gs["powers"]["levels"].get(equipped_power, 0)
                fire_cooldown = fire_cooldown / (2 + power_level * 1.5)
            
            # Check for shooting (keyboard only)
            should_fire = KEY[pygame.K_SPACE]
                
            if should_fire and gs["time_since_shot"] >= fire_cooldown:
                gs["time_since_shot"] = 0.0
                nose_offset = 18.0
                bx = gs["worldxposition"] + fx * nose_offset
                by = gs["worldyposition"] + fy * nose_offset
                bvx = fx * bullet_speed + gs["cam_vx"]
                bvy = fy * bullet_speed + gs["cam_vy"]
                bullets.append({"x": bx, "y": by, "vx": bvx, "vy": bvy, "life": bullet_life, "pierce_count": 0})

            for b in bullets[:]:
                # Auto-aim
                if equipped_power == "auto_aim" and gs["power_effects"]:
                    aim_strength = gs["power_effects"][0].get("strength", 0)
                    # Find nearest asteroid
                    nearest_dist = float('inf')
                    nearest_asteroid = None
                    for asteroid in asteroids:
                        dist = math.hypot(asteroid.x - b["x"], asteroid.y - b["y"])
                        if dist < nearest_dist and dist < 400:  # Only track within range
                            nearest_dist = dist
                            nearest_asteroid = asteroid
                    
                    if nearest_asteroid:
                        # Steer bullet towards asteroid
                        dx = nearest_asteroid.x - b["x"]
                        dy = nearest_asteroid.y - b["y"]
                        dist = math.hypot(dx, dy)
                        if dist > 0:
                            target_vx = (dx / dist) * bullet_speed
                            target_vy = (dy / dist) * bullet_speed
                            b["vx"] += (target_vx - b["vx"]) * aim_strength * dt * 5
                            b["vy"] += (target_vy - b["vy"]) * aim_strength * dt * 5
                
                b["x"] += b["vx"] * dt
                b["y"] += b["vy"] * dt
                b["life"] -= dt
                if b["life"] <= 0:
                    bullets.remove(b)

            # Update power effects
            update_power_effects(gs, dt, CX, CY)

            ship_radius = 14
            for asteroid in asteroids:
                pdx = asteroid.x - gs["worldxposition"]
                pdy = asteroid.y - gs["worldyposition"]
                dist = math.hypot(pdx, pdy)
                if dist < ship_radius + asteroid.radius:
                    nx = pdx / (dist + 1e-6)
                    ny = pdy / (dist + 1e-6)
                    dot = asteroid.dx * nx + asteroid.dy * ny
                    asteroid.dx -= 2 * dot * nx
                    asteroid.dy -= 2 * dot * ny
                    dot_player = gs["cam_vx"] * nx + gs["cam_vy"] * ny
                    gs["cam_vx"] -= 2 * dot_player * nx
                    gs["cam_vy"] -= 2 * dot_player * ny
                    
                    # Push asteroid away to prevent sticking
                    overlap = (ship_radius + asteroid.radius) - dist
                    if overlap > 0:
                        asteroid.x += nx * overlap * 1.2
                        asteroid.y += ny * overlap * 1.2

            for i, a1 in enumerate(asteroids):
                for j, a2 in enumerate(asteroids):
                    if i >= j:
                        continue
                    dx = a1.x - a2.x
                    dy = a1.y - a2.y
                    dist = math.hypot(dx, dy)
                    min_dist = a1.radius + a2.radius
                    if dist < min_dist and dist > 0:
                        nx = dx / dist
                        ny = dy / dist
                        dot1 = a1.dx * nx + a1.dy * ny
                        dot2 = a2.dx * nx + a2.dy * ny
                        a1.dx -= dot1 * nx
                        a1.dy -= dot1 * ny
                        a2.dx -= dot2 * nx
                        a2.dy -= dot2 * ny
                        overlap = min_dist - dist
                        a1.x += nx * (overlap / 2)
                        a1.y += ny * (overlap / 2)
                        a2.x -= nx * (overlap / 2)
                        a2.y -= ny * (overlap / 2)

            right_x = math.cos(player.rotation)
            right_y = math.sin(player.rotation)
            k_spring = 6.0
            damping = 2.0
            for item in carried_items:
                a_lat = gs["cam_vx"] * right_x + gs["cam_vy"] * right_y
                ang_acc = -k_spring * (item["rel_angle"] - math.pi) - damping * item["ang_vel"] - (a_lat) * 0.09
                item["ang_vel"] += ang_acc * dt
                item["rel_angle"] += item["ang_vel"] * dt

            # Collision between carried items
            item_radius = 8
            for i, item1 in enumerate(carried_items):
                for j, item2 in enumerate(carried_items):
                    if i >= j:
                        continue
                    # Calculate positions
                    ang1 = player.rotation + item1["rel_angle"]
                    ang2 = player.rotation + item2["rel_angle"]
                    x1 = math.sin(ang1) * item1["length"]
                    y1 = -math.cos(ang1) * item1["length"]
                    x2 = math.sin(ang2) * item2["length"]
                    y2 = -math.cos(ang2) * item2["length"]
                    # Check collision
                    dx = x2 - x1
                    dy = y2 - y1
                    dist = math.hypot(dx, dy)
                    min_dist = item_radius * 2
                    if dist < min_dist and dist > 0:
                        # Push items apart by adjusting angles
                        push = 0.15 * (min_dist - dist) / dist
                        item1["ang_vel"] -= push
                        item2["ang_vel"] += push

            for ft in floating_texts[:]:
                ft["x"] += ft["dx"] * dt
                ft["y"] += ft["dy"] * dt
                ft["timer"] += dt
                ft["alpha"] -= 120 * dt
                if ft["alpha"] <= 0 or ft["timer"] > 2.0:
                    floating_texts.remove(ft)
            
            # Update floating loot
            storage_capacity = 5 + 5 * upgrades.get("storage", 0)
            equipped_power = gs["powers"].get("equipped")
            magnet_active = equipped_power == "magnet" and gs["power_effects"]
            magnet_range = gs["power_effects"][0].get("range", 0) if magnet_active else 0
            magnet_strength = gs["power_effects"][0].get("strength", 0) if magnet_active else 0
            
            # Update drop cooldown
            if gs["drop_cooldown"] > 0:
                gs["drop_cooldown"] -= dt
            
            for loot in gs["floating_loot"][:]:
                # Apply friction
                loot["vx"] *= 0.95
                loot["vy"] *= 0.95
                
                # Magnet attraction
                if magnet_active:
                    dx = gs["worldxposition"] - loot["x"]
                    dy = gs["worldyposition"] - loot["y"]
                    dist = math.hypot(dx, dy)
                    if dist < magnet_range and dist > 1:
                        # Pull toward player
                        pull_force = magnet_strength / (dist + 10)
                        loot["vx"] += (dx / dist) * pull_force * dt
                        loot["vy"] += (dy / dist) * pull_force * dt
                
                # Update position
                loot["x"] += loot["vx"] * dt
                loot["y"] += loot["vy"] * dt
                loot["lifetime"] -= dt
                
                # Check if player picks it up (only if cooldown expired)
                if gs["drop_cooldown"] <= 0:
                    dist_to_player = math.hypot(loot["x"] - gs["worldxposition"], loot["y"] - gs["worldyposition"])
                    if dist_to_player < 30:  # Pickup radius
                        space = max(0, storage_capacity - len(carried_items))
                        if space > 0:
                            carried_items.append({
                                "mat": loot["mat"],
                                "rel_angle": math.pi + random.uniform(-0.8, 0.8),
                                "ang_vel": random.uniform(-1.0, 1.0),
                                "length": 55 + random.uniform(-10, 15),
                                "color": loot["color"],
                            })
                            gs["floating_loot"].remove(loot)
                            continue
                
                # Remove if expired
                if loot["lifetime"] <= 0:
                    gs["floating_loot"].remove(loot)

            # Update coin animations
            for coin in gs["coin_animations"][:]:
                coin["progress"] += dt * 2.5  # Animation speed
                if coin["progress"] >= 1.0:
                    gs["coin_animations"].remove(coin)
                    gs["currency_display"] += coin["value"]
            
            # Smooth currency display animation
            if gs["currency_display"] < gs["currency"]:
                diff = gs["currency"] - gs["currency_display"]
                gs["currency_display"] += min(diff, diff * 5 * dt)
            elif gs["currency_display"] > gs["currency"]:
                gs["currency_display"] = gs["currency"]
            
            # Multiplayer network updates
            if network_client.connected:
                network_client.receive()
                network_update_timer += dt
                if network_update_timer >= 0.05:  # Send updates 20 times per second
                    network_update_timer = 0.0
                    network_client.send_update(
                        gs["worldxposition"],
                        gs["worldyposition"],
                        player.rotation,
                        settings["ship_color_index"]
                    )

            screen.fill((0, 0, 0))

            # Render power effects (behind everything)
            render_power_effects(screen, gs, CX, CY, player.rotation)

            for ft in floating_texts:
                sx = int(ft["x"] - gs["worldxposition"] + CX)
                sy = int(ft["y"] - gs["worldyposition"] + CY)
                text_color = ft.get("color", (255, 255, 80))
                surf = font.render(ft["text"], True, text_color)
                surf.set_alpha(max(0, min(255, int(ft["alpha"]))))
                screen.blit(surf, (sx, sy))
            
            # Render coin animations
            for coin in gs["coin_animations"]:
                t = coin["progress"]
                # Ease out cubic
                t_eased = 1 - pow(1 - t, 3)
                x = coin["x"] + (coin["target_x"] - coin["x"]) * t_eased
                y = coin["y"] + (coin["target_y"] - coin["y"]) * t_eased
                # Draw coin
                alpha = int(255 * (1 - t))
                coin_surf = pygame.Surface((20, 20), pygame.SRCALPHA)
                pygame.draw.circle(coin_surf, (255, 220, 100, alpha), (10, 10), 10)
                pygame.draw.circle(coin_surf, (255, 255, 150, alpha), (10, 10), 7)
                screen.blit(coin_surf, (int(x) - 10, int(y) - 10))

            ship_color = SHIP_COLORS[settings["ship_color_index"]][1]
            cx, cy = CX, CY
            size = 14
            pts = [(0, -size), (size * 0.6, size), (-size * 0.6, size)]
            cosr = math.cos(player.rotation)
            sinr = math.sin(player.rotation)
            rot_pts = []
            for x, y in pts:
                rx = x * cosr - y * sinr + cx
                ry = x * sinr + y * cosr + cy
                rot_pts.append((int(rx), int(ry)))

            # Draw fire particles behind ship when thrusting
            KEY = pygame.key.get_pressed()
            if KEY[pygame.K_w]:
                fx_dir = math.sin(player.rotation)
                fy_dir = -math.cos(player.rotation)
                # Fire base position (behind ship)
                fire_base_x = cx - fx_dir * (size + 2)
                fire_base_y = cy - fy_dir * (size + 2)
                # Draw multiple fire particles with randomness for flickering effect
                for _ in range(8):
                    # Random offset perpendicular to thrust direction
                    perp_x = -fy_dir
                    perp_y = fx_dir
                    spread = random.uniform(-6, 6)
                    length = random.uniform(12, 28)
                    px = fire_base_x + perp_x * spread - fx_dir * length
                    py = fire_base_y + perp_y * spread - fy_dir * length
                    # Color gradient: yellow core, orange mid, red outer
                    t = length / 28.0
                    if t < 0.4:
                        color = (255, 255, int(200 * (1 - t/0.4)))  # Yellow to orange
                    elif t < 0.7:
                        color = (255, int(165 * (1 - (t-0.4)/0.3)), 0)  # Orange to red-orange
                    else:
                        color = (255, int(80 * (1 - (t-0.7)/0.3)), 0)  # Red-orange to red
                    particle_size = int(4 * (1 - t * 0.5))
                    pygame.draw.circle(screen, color, (int(px), int(py)), max(2, particle_size))
                # Draw bright core
                for _ in range(3):
                    spread = random.uniform(-3, 3)
                    core_x = fire_base_x + perp_x * spread - fx_dir * random.uniform(2, 8)
                    core_y = fire_base_y + perp_y * spread - fy_dir * random.uniform(2, 8)
                    pygame.draw.circle(screen, (255, 255, 200), (int(core_x), int(core_y)), 3)

            # Draw ship with outline
            pygame.draw.polygon(screen, ship_color, rot_pts)
            pygame.draw.polygon(screen, (255, 255, 255), rot_pts, 2)  # White outline

            # Draw player nametag above own ship
            own_name_surf = font.render(settings["player_name"], True, (200, 255, 200))
            screen.blit(own_name_surf, (cx - own_name_surf.get_width() // 2, cy - 35))

            # Draw other players (multiplayer)
            if network_client.connected:
                other_players = network_client.get_other_players()
                for pid, pdata in other_players.items():
                    # Calculate screen position relative to our position
                    other_x = pdata.get("x", 0)
                    other_y = pdata.get("y", 0)
                    other_rot = pdata.get("rotation", 0)
                    other_color_idx = pdata.get("color_index", 0)
                    other_name = pdata.get("name", "Player")

                    # Screen position
                    scr_x = int(other_x - gs["worldxposition"] + CX)
                    scr_y = int(other_y - gs["worldyposition"] + CY)

                    # Only draw if on screen (with margin)
                    if -100 < scr_x < SCREEN_W + 100 and -100 < scr_y < SCREEN_H + 100:
                        # Get ship color
                        other_color = SHIP_COLORS[other_color_idx % len(SHIP_COLORS)][1]

                        # Draw other player's ship
                        other_size = 14
                        other_pts = [(0, -other_size), (other_size * 0.6, other_size), (-other_size * 0.6, other_size)]
                        other_cosr = math.cos(other_rot)
                        other_sinr = math.sin(other_rot)
                        other_rot_pts = []
                        for ox, oy in other_pts:
                            orx = ox * other_cosr - oy * other_sinr + scr_x
                            ory = ox * other_sinr + oy * other_cosr + scr_y
                            other_rot_pts.append((int(orx), int(ory)))

                        pygame.draw.polygon(screen, other_color, other_rot_pts)
                        pygame.draw.polygon(screen, (255, 255, 255), other_rot_pts, 2)

                        # Draw nametag above other player
                        name_surf = font.render(other_name, True, (255, 255, 255))
                        name_bg = pygame.Rect(
                            scr_x - name_surf.get_width() // 2 - 4,
                            scr_y - 38,
                            name_surf.get_width() + 8,
                            name_surf.get_height() + 4
                        )
                        pygame.draw.rect(screen, (0, 0, 0, 150), name_bg, border_radius=3)
                        screen.blit(name_surf, (scr_x - name_surf.get_width() // 2, scr_y - 35))

            bx_scr = int(base_x - gs["worldxposition"] + CX)
            by_scr = int(base_y - gs["worldyposition"] + CY)
            base_size = 28
            # Draw base with same style as power shop
            pygame.draw.rect(screen, (80, 100, 255), (bx_scr - base_size//2, by_scr - base_size//2, base_size, base_size), 0, border_radius=5)
            pygame.draw.rect(screen, (150, 180, 255), (bx_scr - base_size//2, by_scr - base_size//2, base_size, base_size), 3, border_radius=5)
            # Add glow effect
            glow_surf = pygame.Surface((base_size + 20, base_size + 20), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf, (150, 180, 255, 50), (0, 0, base_size + 20, base_size + 20), border_radius=10)
            screen.blit(glow_surf, (bx_scr - base_size//2 - 10, by_scr - base_size//2 - 10))
            base_label = font.render("BASE", True, (150, 180, 255))
            screen.blit(base_label, (bx_scr - base_label.get_width()//2, by_scr - 45))
            
            # Draw power shop structure
            if upgrades.get("powers_unlocked", False):
                psx_scr = int(power_shop_x - gs["worldxposition"] + CX)
                psy_scr = int(power_shop_y - gs["worldyposition"] + CY)
                ps_size = 28
                # Draw purple/pink structure
                pygame.draw.rect(screen, (180, 80, 255), (psx_scr - ps_size//2, psy_scr - ps_size//2, ps_size, ps_size), 0, border_radius=5)
                pygame.draw.rect(screen, (255, 150, 255), (psx_scr - ps_size//2, psy_scr - ps_size//2, ps_size, ps_size), 3, border_radius=5)
                # Add glow effect
                glow_surf = pygame.Surface((ps_size + 20, ps_size + 20), pygame.SRCALPHA)
                pygame.draw.rect(glow_surf, (255, 150, 255, 50), (0, 0, ps_size + 20, ps_size + 20), border_radius=10)
                screen.blit(glow_surf, (psx_scr - ps_size//2 - 10, psy_scr - ps_size//2 - 10))
                ps_label = font.render("POWER SHOP", True, (255, 150, 255))
                screen.blit(ps_label, (psx_scr - ps_label.get_width()//2, psy_scr - 45))

            if not (0 <= bx_scr <= SCREEN_W and 0 <= by_scr <= SCREEN_H):
                dir_x = bx_scr - CX
                dir_y = by_scr - CY
                ang = math.atan2(dir_y, dir_x)
                margin = 40
                t_vals = []
                if math.cos(ang) != 0:
                    t_vals.extend([(margin - CX) / math.cos(ang), (SCREEN_W - margin - CX) / math.cos(ang)])
                if math.sin(ang) != 0:
                    t_vals.extend([(margin - CY) / math.sin(ang), (SCREEN_H - margin - CY) / math.sin(ang)])
                t_edge = min([t for t in t_vals if t > 0], default=1)
                arrow_x = int(CX + math.cos(ang) * t_edge)
                arrow_y = int(CY + math.sin(ang) * t_edge)
                arrow_size = 14
                p1 = (int(arrow_x + math.cos(ang) * arrow_size), int(arrow_y + math.sin(ang) * arrow_size))
                p2 = (int(arrow_x + math.cos(ang + 2.5) * arrow_size), int(arrow_y + math.sin(ang + 2.5) * arrow_size))
                p3 = (int(arrow_x + math.cos(ang - 2.5) * arrow_size), int(arrow_y + math.sin(ang - 2.5) * arrow_size))
                pygame.draw.polygon(screen, (255, 140, 0), [p1, p2, p3])

            loot_counter = {}
            for asteroid in asteroids[:]:
                ax = int(asteroid.x - gs["worldxposition"] + CX)
                ay = int(asteroid.y - gs["worldyposition"] + CY)
                size = asteroid.radius * 2
                img = pygame.transform.smoothscale(asteroid_img, (size, size))
                
                # Golden asteroid tint - better visual
                if asteroid.golden:
                    # Create a circular gold overlay instead of square
                    gold_overlay = pygame.Surface((size, size), pygame.SRCALPHA)
                    center = size // 2
                    for r in range(asteroid.radius, 0, -2):
                        alpha = int(80 * (r / asteroid.radius))
                        pygame.draw.circle(gold_overlay, (255, 215, 0, alpha), (center, center), r)
                    img.blit(gold_overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
                
                screen.blit(img, (ax - asteroid.radius, ay - asteroid.radius))
                
                # Golden asteroid sparkle particles
                if asteroid.golden:
                    for _ in range(3):
                        spark_angle = random.uniform(0, 2 * math.pi)
                        spark_dist = random.uniform(0, asteroid.radius * 0.9)
                        spark_x = ax + math.cos(spark_angle) * spark_dist
                        spark_y = ay + math.sin(spark_angle) * spark_dist
                        spark_size = random.randint(2, 4)
                        spark_color = random.choice([(255, 255, 150), (255, 215, 0), (255, 255, 200)])
                        pygame.draw.circle(screen, spark_color, (int(spark_x), int(spark_y)), spark_size)

                barw = 40 if asteroid.boss else 28
                barh = 7 if asteroid.boss else 5
                health_frac = asteroid.health / asteroid.max_health
                bar_x = ax - barw // 2
                bar_y = ay - asteroid.radius - (18 if asteroid.boss else 12)
                pygame.draw.rect(screen, (60, 60, 60), (bar_x, bar_y, barw, barh))
                pygame.draw.rect(screen, (80, 255, 80), (bar_x, bar_y, int(barw * health_frac), barh))
                health_text = font.render(f"{max(0, int(asteroid.health))}", True, (255, 255, 255))
                text_rect = health_text.get_rect(center=(ax, bar_y + barh // 2))
                screen.blit(health_text, text_rect)

                for b in bullets[:]:
                    ddx = asteroid.x - b["x"]
                    ddy = asteroid.y - b["y"]
                    if math.hypot(ddx, ddy) < asteroid.radius + 6:
                        damage = 1 + upgrades.get("shot_damage", 0)
                        asteroid.health -= damage
                        
                        # Power effects on hit
                        equipped_power = gs["powers"].get("equipped")
                        power_level = gs["powers"]["levels"].get(equipped_power, 0)
                        
                        # Bullet Split
                        if equipped_power == "bullet_split":
                            num_splits = 1 + power_level
                            for _ in range(num_splits):
                                angle = random.uniform(0, 2 * math.pi)
                                split_speed = bullet_speed * 0.7
                                bullets.append({
                                    "x": asteroid.x,
                                    "y": asteroid.y,
                                    "vx": math.cos(angle) * split_speed,
                                    "vy": math.sin(angle) * split_speed,
                                    "life": bullet_life * 0.5,
                                    "pierce_count": 0
                                })
                        
                        # Explosive Shots
                        if equipped_power == "explosive_shots":
                            explosion_radius = 50 + power_level * 20
                            explosion_damage = 2 + power_level
                            for other_asteroid in asteroids:
                                if other_asteroid != asteroid:
                                    dist_to_explosion = math.hypot(other_asteroid.x - asteroid.x, other_asteroid.y - asteroid.y)
                                    if dist_to_explosion < explosion_radius:
                                        other_asteroid.health -= explosion_damage
                        
                        # Piercing - only remove bullet if it's out of pierces
                        should_remove = True
                        if equipped_power == "piercing_shots":
                            max_pierce = power_level
                            if b.get("pierce_count", 0) < max_pierce:
                                b["pierce_count"] = b.get("pierce_count", 0) + 1
                                should_remove = False
                        
                        if should_remove:
                            try:
                                bullets.remove(b)
                            except ValueError:
                                pass
                        
                        if asteroid.health <= 0:
                            try:
                                asteroids.remove(asteroid)
                            except ValueError:
                                pass
                            loot_counter.clear()
                            loot_table = [
                                ("Iron", 0.5), ("Copper", 0.2), ("Gold", 0.08), ("Titanium", 0.08),
                                ("Platinum", 0.06), ("Uranium", 0.05), ("Diamond", 0.03)
                            ]
                            if asteroid.boss:
                                loot_table = [
                                    ("Diamond", 0.25), ("Uranium", 0.2), ("Platinum", 0.2),
                                    ("Titanium", 0.15), ("Gold", 0.1), ("Copper", 0.06), ("Iron", 0.04)
                                ]
                            loot_count = max(1, int(asteroid.max_health/6 + asteroid.radius/8))
                            storage_capacity = 5 + 5 * upgrades.get("storage", 0)
                            for _ in range(loot_count):
                                r = random.random()
                                bias = min(1.0, (asteroid.max_health + asteroid.radius) / 120.0)
                                loot_table_biased = []
                                for idx, (mat, prob) in enumerate(loot_table):
                                    if idx >= len(loot_table) - 3:
                                        prob = prob + prob * bias * 2.5
                                    loot_table_biased.append((mat, prob))
                                total_prob = sum(p for _, p in loot_table_biased)
                                loot_table_biased = [(mat, p/total_prob) for mat, p in loot_table_biased]
                                acc = 0.0
                                for mat, prob in loot_table_biased:
                                    acc += prob
                                    if r <= acc:
                                        # Create floating loot instead of directly adding to inventory
                                        angle = random.uniform(0, 2*math.pi)
                                        speed = random.uniform(40, 80)
                                        gs["floating_loot"].append({
                                            "mat": mat,
                                            "x": asteroid.x,
                                            "y": asteroid.y,
                                            "vx": math.cos(angle) * speed,
                                            "vy": math.sin(angle) * speed,
                                            "color": list(color_map.get(mat, (255, 255, 255))),
                                            "lifetime": 15.0  # Loot disappears after 15 seconds
                                        })
                                        loot_counter[mat] = loot_counter.get(mat, 0) + 1
                                        break
                            
                            # Power cores from golden asteroids
                            if asteroid.golden and random.random() < 0.3:  # 30% chance from golden
                                angle = random.uniform(0, 2*math.pi)
                                speed = random.uniform(40, 80)
                                gs["floating_loot"].append({
                                    "mat": "Power Core",
                                    "x": asteroid.x,
                                    "y": asteroid.y,
                                    "vx": math.cos(angle) * speed,
                                    "vy": math.sin(angle) * speed,
                                    "color": [100, 255, 100],  # Green
                                    "lifetime": 15.0
                                })
                                loot_counter["Power Core"] = loot_counter.get("Power Core", 0) + 1
                            
                            for mat, count in loot_counter.items():
                                for _ in range(count):
                                    angle = random.uniform(0, 2*math.pi)
                                    speed = random.uniform(30, 70)
                                    # Green text for power cores
                                    text_color = (100, 255, 100) if mat == "Power Core" else (255, 255, 80)
                                    floating_texts.append({
                                        "text": f"+1 {mat}",
                                        "x": asteroid.x,
                                        "y": asteroid.y,
                                        "dx": math.cos(angle)*speed,
                                        "dy": math.sin(angle)*speed,
                                        "alpha": 255,
                                        "timer": 0.0,
                                        "color": text_color
                                    })

            gs["spawn_timer"] += dt
            if gs["spawn_timer"] >= spawn_interval:
                gs["spawn_timer"] = 0.0
                if len(asteroids) < max_asteroids:
                    # Spawn outside camera view
                    ang = random.random() * 2 * math.pi
                    # Spawn at edge of screen + some distance
                    spawn_distance = max(SCREEN_W, SCREEN_H) // 2 + random.randint(100, 300)
                    rx = gs["worldxposition"] + math.cos(ang) * spawn_distance
                    ry = gs["worldyposition"] + math.sin(ang) * spawn_distance
                    base_dist = math.hypot(rx - base_x, ry - base_y)
                    # Increased spawn chance at far distances
                    spawn_chance = max(0.15, 1.0 * math.exp(-base_dist / 4500))
                    if base_dist > 3000:
                        spawn_chance = min(0.95, spawn_chance * 1.5)  # Much higher chance far away
                    if random.random() <= spawn_chance:
                        # Incremental scaling based on distance
                        # Size scales from 1.0 at base to higher values far away
                        size_scale = 1.0 + (base_dist / 2000.0)  # Gradual increase
                        size_scale = min(size_scale, 10.0)  # Cap at 10x
                        
                        # Boss probability increases with distance
                        boss_prob = min(0.15, 0.02 + (base_dist / 20000.0))
                        is_boss = random.random() < boss_prob and base_dist > 2000
                        
                        # Calculate health based on size scale
                        if is_boss:
                            base_health = 40
                            health = int(base_health * size_scale * random.uniform(0.8, 1.2))
                        else:
                            base_health = random.randint(6, 18)
                            health = int(base_health * size_scale * random.uniform(0.9, 1.1))
                        
                        # Calculate radius based on size scale
                        if is_boss:
                            radius = int((32 + base_dist / 200) * random.uniform(0.9, 1.1))
                        else:
                            radius = int((8 + base_dist / 400) * random.uniform(0.9, 1.1))
                        
                        radius = max(8, min(radius, 80))  # Clamp between 8 and 80
                        
                        asteroids.append(Asteroid(rx, ry, random.uniform(-30, 30), random.uniform(-30, 30), health=health, boss=is_boss))
                        asteroids[-1].radius = radius
                        asteroids[-1].max_health = health

            speed = math.hypot(gs["cam_vx"], gs["cam_vy"])
            sx = int(gs["cam_vx"] * 0.05)
            sy = int(gs["cam_vy"] * 0.05)
            cx, cy = CX, CY
            pygame.draw.line(screen, (0, 255, 0), (cx, cy), (cx + sx, cy + sy), 3)

            for b in bullets:
                bx_scr = int(b["x"] - gs["worldxposition"] + CX)
                by_scr = int(b["y"] - gs["worldyposition"] + CY)
                pygame.draw.circle(screen, (255, 220, 0), (bx_scr, by_scr), 3)
            
            # Draw floating loot
            for loot in gs["floating_loot"]:
                lx_scr = int(loot["x"] - gs["worldxposition"] + CX)
                ly_scr = int(loot["y"] - gs["worldyposition"] + CY)
                # Draw loot with pulsing effect
                pulse = 1.0 + 0.2 * math.sin(pygame.time.get_ticks() / 200.0)
                radius = int(8 * pulse)
                pygame.draw.circle(screen, tuple(loot["color"]), (lx_scr, ly_scr), radius)
                pygame.draw.circle(screen, (255, 255, 255), (lx_scr, ly_scr), radius, 2)
                # Draw glow
                glow_surf = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (*loot["color"], 60), (radius * 2, radius * 2), radius * 2)
                screen.blit(glow_surf, (lx_scr - radius * 2, ly_scr - radius * 2))

            cx, cy = CX, CY
            for i, item in enumerate(carried_items):
                world_angle = player.rotation + item["rel_angle"]
                ix = cx + int(math.sin(world_angle) * item["length"])
                iy = cy + int(-math.cos(world_angle) * item["length"])
                pygame.draw.line(screen, (120, 120, 120), (cx, cy), (ix, iy), 2)
                pygame.draw.circle(screen, tuple(item["color"]), (ix, iy), 6)
                
                # Show resource name on hover and allow dropping by clicking
                if math.hypot(mouse_pos[0] - ix, mouse_pos[1] - iy) < 15:
                    name_surf = font.render(f"{item['mat']} (Click to drop)", True, (255, 255, 255))
                    name_bg = pygame.Rect(mouse_pos[0] + 15, mouse_pos[1] - 10, name_surf.get_width() + 8, name_surf.get_height() + 4)
                    pygame.draw.rect(screen, (40, 40, 60), name_bg, border_radius=4)
                    pygame.draw.rect(screen, (200, 200, 255), name_bg, 1, border_radius=4)
                    screen.blit(name_surf, (mouse_pos[0] + 19, mouse_pos[1] - 8))
                    
                    # Drop resource on click
                    if mouse_clicked:
                        # Create floating loot at player position
                        angle = random.uniform(0, 2*math.pi)
                        speed = random.uniform(100, 150)  # Faster throw speed
                        gs["floating_loot"].append({
                            "mat": item["mat"],
                            "x": gs["worldxposition"],
                            "y": gs["worldyposition"],
                            "vx": math.cos(angle) * speed,
                            "vy": math.sin(angle) * speed,
                            "color": item["color"],
                            "lifetime": 15.0
                        })
                        carried_items.pop(i)
                        gs["drop_cooldown"] = 1.0  # 1 second cooldown before pickup
                        break  # Only drop one per click

            storage_capacity = 5 + 5 * upgrades.get("storage", 0)
            storage_used = len(carried_items)
            
            # Top right - Money display (big and visible with decimals)
            money_font = pygame.font.SysFont(None, 48)
            money_text = money_font.render(f"${gs['currency_display']:.2f}", True, (255, 220, 100))
            money_bg = pygame.Rect(SCREEN_W - money_text.get_width() - 30, 10, money_text.get_width() + 20, money_text.get_height() + 10)
            pygame.draw.rect(screen, (40, 40, 60, 200), money_bg, border_radius=8)
            pygame.draw.rect(screen, (255, 220, 100), money_bg, 2, border_radius=8)
            screen.blit(money_text, (SCREEN_W - money_text.get_width() - 20, 15))
            
            # Top left - Speed and Storage (styled like money)
            info_font = pygame.font.SysFont(None, 36)
            speed_text = info_font.render(f"Speed: {speed:.0f}", True, (100, 255, 255))
            speed_bg = pygame.Rect(15, 15, speed_text.get_width() + 20, speed_text.get_height() + 8)
            pygame.draw.rect(screen, (30, 40, 50, 200), speed_bg, border_radius=6)
            pygame.draw.rect(screen, (100, 255, 255), speed_bg, 2, border_radius=6)
            screen.blit(speed_text, (25, 19))
            
            cargo_text = info_font.render(f"Cargo: {storage_used}/{storage_capacity}", True, (255, 180, 100))
            cargo_bg = pygame.Rect(15, 70, cargo_text.get_width() + 20, cargo_text.get_height() + 8)
            pygame.draw.rect(screen, (30, 40, 50, 200), cargo_bg, border_radius=6)
            pygame.draw.rect(screen, (255, 180, 100), cargo_bg, 2, border_radius=6)
            screen.blit(cargo_text, (25, 74))
            
            screen.blit(font.render("ESC = Menu", True, (150, 150, 150)), (10, SCREEN_H - 30))
            
            pdist = math.hypot(gs["worldxposition"] - base_x, gs["worldyposition"] - base_y)
            if pdist <= base_sell_radius:
                sell_text = font.render("At base: E = sell, click upgrade below", True, (180, 180, 255))
                screen.blit(sell_text, (SCREEN_W//2 - 160, 10))

                # Different base costs and multipliers for each upgrade
                upg_keys = ["speed", "storage", "shot_damage", "shoot_speed"]
                base_costs = [8, 12, 20, 15]  # speed cheapest, damage most expensive
                multipliers = [2.5, 2.8, 3.2, 2.9]
                upg_costs = [base_costs[i] * (multipliers[i] ** upgrades[upg_keys[i]]) for i in range(4)]
                upg_names = ["Speed", "Storage", "Damage", "Shooting Speed"]
                upg_descs = ["Move faster", "Carry more cargo", "Deal more damage", "Shoot faster"]
                button_w = 210
                button_h = 90
                gap = 18
                total_width = 4*button_w + 3*gap
                start_x = max(0, SCREEN_W//2 - total_width//2)
                base_y_btn = SCREEN_H - button_h - 36

                for i in range(4):
                    bx = start_x + i*(button_w+gap)
                    by = base_y_btn
                    rect = pygame.Rect(bx, by, button_w, button_h)
                    color = (60, 60, 120) if gs["currency"] < upg_costs[i] else (80, 180, 255)
                    if rect.collidepoint(mouse_pos):
                        color = (120, 220, 255)
                    pygame.draw.rect(screen, color, rect, border_radius=12)
                    pygame.draw.rect(screen, (200, 200, 255), rect, 2, border_radius=12)
                    name_surf = font.render(f"{upg_names[i]} (Lv {upgrades[list(upgrades.keys())[i]]+1})", True, (255,255,255))
                    cost_surf = font.render(f"Cost: {upg_costs[i]:.2f}", True, (255,255,0) if gs["currency"] >= upg_costs[i] else (180,100,100))
                    desc_surf = font.render(upg_descs[i], True, (200,255,255))
                    screen.blit(name_surf, (bx+12, by+12))
                    screen.blit(cost_surf, (bx+12, by+36))
                    screen.blit(desc_surf, (bx+12, by+60))

                    if rect.collidepoint(mouse_pos) and mouse_clicked and gs["currency"] >= upg_costs[i]:
                        gs["currency"] -= upg_costs[i]
                        upgrades[list(upgrades.keys())[i]] += 1

                # Powers unlock (only at base) - with drop zone
                if not upgrades.get("powers_unlocked", False):
                    powers_btn_y = base_y_btn - 180
                    powers_btn_rect = pygame.Rect(SCREEN_W//2 - 250, powers_btn_y, 500, 150)
                    
                    # Required materials
                    required_mats = {"Iron": 10, "Copper": 5, "Titanium": 3, "Uranium": 2, "Power Core": 1}
                    stored_mats = gs["power_shop_materials"]
                    
                    has_all = all(stored_mats.get(mat, 0) >= qty for mat, qty in required_mats.items())
                    
                    powers_color = (100, 40, 120) if not has_all else (180, 80, 255)
                    if powers_btn_rect.collidepoint(mouse_pos):
                        powers_color = (220, 120, 255) if has_all else (120, 50, 140)
                    pygame.draw.rect(screen, powers_color, powers_btn_rect, border_radius=12)
                    pygame.draw.rect(screen, (255, 150, 255), powers_btn_rect, 3, border_radius=12)
                    powers_title = medium_font.render("BUILD POWER SHOP", True, (255, 255, 255))
                    screen.blit(powers_title, (powers_btn_rect.centerx - powers_title.get_width()//2, powers_btn_rect.y + 10))
                    
                    drop_text = font.render("Drop materials here (click on carried items)", True, (200, 200, 200))
                    screen.blit(drop_text, (powers_btn_rect.centerx - drop_text.get_width()//2, powers_btn_rect.y + 45))
                    
                    # Show requirements in rows
                    y_offset = powers_btn_rect.y + 75
                    row1 = [("Iron", 10), ("Copper", 5), ("Titanium", 3)]
                    row2 = [("Uranium", 2), ("Power Core", 1)]
                    
                    for row_idx, row in enumerate([row1, row2]):
                        x_offset = powers_btn_rect.centerx - (len(row) * 90) // 2
                        for mat, qty in row:
                            have = stored_mats.get(mat, 0)
                            color = (100, 255, 100) if have >= qty else (255, 100, 100)
                            req_surf = font.render(f"{mat}: {have}/{qty}", True, color)
                            screen.blit(req_surf, (x_offset, y_offset + row_idx * 25))
                            x_offset += 90
                    
                    # Check if items are dropped in the zone
                    for i, item in enumerate(carried_items[:]):
                        world_angle = player.rotation + item["rel_angle"]
                        ix = CX + int(math.sin(world_angle) * item["length"])
                        iy = CY + int(-math.cos(world_angle) * item["length"])
                        
                        if powers_btn_rect.collidepoint(ix, iy) and mouse_clicked:
                            if item["mat"] in required_mats:
                                stored_mats[item["mat"]] = stored_mats.get(item["mat"], 0) + 1
                                carried_items.pop(i)
                                break
                    
                    if powers_btn_rect.collidepoint(mouse_pos) and mouse_clicked and has_all:
                        # Clear stored materials
                        for mat in required_mats:
                            stored_mats[mat] = 0
                        upgrades["powers_unlocked"] = True

                if KEY[pygame.K_e] and carried_items:
                    prices = {"Iron": 1.0, "Copper": 2.0, "Gold": 4.0, "Titanium": 6.0, "Platinum": 8.0, "Uranium": 10.0, "Diamond": 14.0, "Power Core": 0}
                    counts = {}
                    # Create coin animations for each item
                    for it in carried_items:
                        counts[it["mat"]] = counts.get(it["mat"], 0) + 1
                        # Create coin animation
                        angle = random.uniform(0, 2*math.pi)
                        gs["coin_animations"].append({
                            "x": CX,
                            "y": CY,
                            "target_x": SCREEN_W - 100,
                            "target_y": 40,
                            "progress": 0.0,
                            "value": prices.get(it["mat"], 0)
                        })
                    total = 0.0
                    for mat, qty in counts.items():
                        total += prices.get(mat, 0) * qty
                    carried_items.clear()
                    gs["currency"] += round(total, 2)
            
            # Check if at power shop
            if upgrades.get("powers_unlocked", False):
                ps_dist = math.hypot(gs["worldxposition"] - power_shop_x, gs["worldyposition"] - power_shop_y)
                if ps_dist <= power_shop_radius:
                    ps_text = font.render("At Power Shop: Press P to enter", True, (255, 150, 255))
                    screen.blit(ps_text, (SCREEN_W//2 - ps_text.get_width()//2, 40))
                    
                    if KEY[pygame.K_p]:
                        current_state = STATE_POWER_SHOP

        # ==================== CONFIRM EXIT STATE ====================
        elif current_state == STATE_CONFIRM_EXIT and game_state:
            # Dim the game screen
            dim_surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            dim_surf.fill((0, 0, 0, 180))
            screen.blit(dim_surf, (0, 0))
            
            # Confirmation dialog
            dialog_w, dialog_h = 500, 250
            dialog_rect = pygame.Rect(CX - dialog_w//2, CY - dialog_h//2, dialog_w, dialog_h)
            pygame.draw.rect(screen, (40, 40, 60), dialog_rect, border_radius=12)
            pygame.draw.rect(screen, (200, 200, 255), dialog_rect, 3, border_radius=12)
            
            title_text = medium_font.render("Save and Exit?", True, (255, 255, 255))
            screen.blit(title_text, (CX - title_text.get_width()//2, CY - 80))
            
            info_text = font.render("Your progress will be saved", True, (200, 200, 200))
            screen.blit(info_text, (CX - info_text.get_width()//2, CY - 30))
            
            # Buttons
            yes_btn = Button(CX - 130, CY + 40, 120, 50, "Yes", color=(80, 180, 80), hover_color=(120, 220, 120))
            no_btn = Button(CX + 10, CY + 40, 120, 50, "No", color=(180, 80, 80), hover_color=(220, 120, 120))
            
            yes_btn.draw(screen, font, mouse_pos)
            no_btn.draw(screen, font, mouse_pos)
            
            if mouse_clicked:
                if yes_btn.is_clicked(mouse_pos, True):
                    if network_client.connected:
                        network_client.disconnect()
                    if server_process:
                        server_process.terminate()
                        server_process = None
                    if current_world_name and game_state:
                        save_world(current_world_name, game_state)
                    current_state = STATE_MENU
                elif no_btn.is_clicked(mouse_pos, True):
                    current_state = STATE_PLAYING

        # ==================== POWER SHOP STATE ====================
        elif current_state == STATE_POWER_SHOP and game_state:
            gs = game_state
            powers = gs["powers"]
            
            title = title_font.render("SUPERPOWER SHOP", True, (255, 150, 255))
            screen.blit(title, (CX - title.get_width() // 2, 50))
            
            coins_text = medium_font.render(f"Coins: ${gs['currency']:.2f}", True, (255, 220, 100))
            screen.blit(coins_text, (CX - coins_text.get_width() // 2, 120))
            
            # Display powers in a grid
            powers_per_row = 3
            power_w, power_h = 280, 180
            gap = 20
            start_y = 180
            
            power_list = list(SUPERPOWERS.items())
            for idx, (power_id, power_data) in enumerate(power_list):
                row = idx // powers_per_row
                col = idx % powers_per_row
                
                total_row_width = powers_per_row * power_w + (powers_per_row - 1) * gap
                start_x = (SCREEN_W - total_row_width) // 2
                
                px = start_x + col * (power_w + gap)
                py = start_y + row * (power_h + gap)
                
                rect = pygame.Rect(px, py, power_w, power_h)
                
                owned = power_id in powers["owned"]
                equipped = powers["equipped"] == power_id
                level = powers["levels"].get(power_id, 0)
                max_level = power_data["max_level"]
                
                # Determine color
                if equipped:
                    color = (80, 255, 120)
                elif owned:
                    color = (80, 180, 255)
                else:
                    color = (60, 60, 120)
                
                if rect.collidepoint(mouse_pos):
                    color = tuple(min(255, c + 40) for c in color)
                
                pygame.draw.rect(screen, color, rect, border_radius=10)
                pygame.draw.rect(screen, (200, 200, 255), rect, 2, border_radius=10)
                
                # Power name
                name_surf = font.render(power_data["name"], True, (255, 255, 255))
                screen.blit(name_surf, (px + 10, py + 10))
                
                # Description
                desc_surf = font.render(power_data["description"], True, (200, 200, 200))
                screen.blit(desc_surf, (px + 10, py + 35))
                
                # Level/Cost info
                if owned:
                    level_surf = font.render(f"Level: {level}/{max_level}", True, (255, 255, 100))
                    screen.blit(level_surf, (px + 10, py + 60))
                    
                    if level < max_level:
                        upgrade_cost = int(power_data["base_cost"] * (power_data["upgrade_cost_mult"] ** level))
                        cost_surf = font.render(f"Upgrade: ${upgrade_cost}", True, (255, 255, 0) if gs["currency"] >= upgrade_cost else (180, 100, 100))
                        screen.blit(cost_surf, (px + 10, py + 85))
                    else:
                        max_surf = font.render("MAX LEVEL", True, (100, 255, 100))
                        screen.blit(max_surf, (px + 10, py + 85))
                    
                    # Equip button
                    if not equipped:
                        equip_btn = pygame.Rect(px + 10, py + 115, 120, 50)
                        equip_color = (100, 200, 100) if equip_btn.collidepoint(mouse_pos) else (60, 150, 60)
                        pygame.draw.rect(screen, equip_color, equip_btn, border_radius=8)
                        equip_text = font.render("EQUIP", True, (255, 255, 255))
                        screen.blit(equip_text, (equip_btn.centerx - equip_text.get_width()//2, equip_btn.centery - equip_text.get_height()//2))
                        
                        if equip_btn.collidepoint(mouse_pos) and mouse_clicked:
                            powers["equipped"] = power_id
                    else:
                        equipped_surf = font.render("EQUIPPED", True, (100, 255, 100))
                        screen.blit(equipped_surf, (px + 10, py + 130))
                    
                    # Upgrade button
                    if level < max_level:
                        upgrade_btn = pygame.Rect(px + 150, py + 115, 120, 50)
                        upgrade_cost = int(power_data["base_cost"] * (power_data["upgrade_cost_mult"] ** level))
                        can_afford = gs["currency"] >= upgrade_cost
                        upgrade_color = (200, 150, 50) if upgrade_btn.collidepoint(mouse_pos) and can_afford else (120, 90, 30) if can_afford else (60, 60, 60)
                        pygame.draw.rect(screen, upgrade_color, upgrade_btn, border_radius=8)
                        upgrade_text = font.render("UPGRADE", True, (255, 255, 255) if can_afford else (120, 120, 120))
                        screen.blit(upgrade_text, (upgrade_btn.centerx - upgrade_text.get_width()//2, upgrade_btn.centery - upgrade_text.get_height()//2))
                        
                        if upgrade_btn.collidepoint(mouse_pos) and mouse_clicked and can_afford:
                            gs["currency"] -= upgrade_cost
                            powers["levels"][power_id] += 1
                else:
                    # Buy button
                    buy_cost = power_data["base_cost"]
                    cost_surf = font.render(f"Cost: ${buy_cost}", True, (255, 255, 0) if gs["currency"] >= buy_cost else (180, 100, 100))
                    screen.blit(cost_surf, (px + 10, py + 60))
                    
                    buy_btn = pygame.Rect(px + 10, py + 115, 260, 50)
                    can_afford = gs["currency"] >= buy_cost
                    buy_color = (180, 80, 255) if buy_btn.collidepoint(mouse_pos) and can_afford else (120, 50, 180) if can_afford else (60, 60, 60)
                    pygame.draw.rect(screen, buy_color, buy_btn, border_radius=8)
                    buy_text = medium_font.render("BUY POWER", True, (255, 255, 255) if can_afford else (120, 120, 120))
                    screen.blit(buy_text, (buy_btn.centerx - buy_text.get_width()//2, buy_btn.centery - buy_text.get_height()//2))
                    
                    if buy_btn.collidepoint(mouse_pos) and mouse_clicked and can_afford:
                        gs["currency"] -= buy_cost
                        powers["owned"].append(power_id)
                        powers["levels"][power_id] = 1
            
            # Back button
            back_btn = Button(CX - 100, SCREEN_H - 80, 200, 50, "Back to Game", color=(120, 60, 60), hover_color=(180, 80, 80))
            back_btn.draw(screen, font, mouse_pos)
            
            if back_btn.is_clicked(mouse_pos, mouse_clicked):
                current_state = STATE_PLAYING

        pygame.display.flip()

    if current_state == STATE_PLAYING and current_world_name and game_state:
        save_world(current_world_name, game_state)

    pygame.quit()

if __name__ == "__main__":
    main()
