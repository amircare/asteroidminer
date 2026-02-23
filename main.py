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
SCREEN_W, SCREEN_H = 1000, 1000
CX, CY = SCREEN_W // 2, SCREEN_H // 2
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
        ("destroy_asteroids", "Destroy {target} asteroids", 5, 15),
        ("destroy_boss", "Destroy {target} boss asteroids", 1, 3),
        ("destroy_golden", "Destroy {target} golden asteroids", 1, 3),
        ("collect_iron", "Collect {target} Iron", 5, 15),
        ("collect_gold", "Collect {target} Gold", 3, 8),
        ("collect_diamond", "Collect {target} Diamond", 1, 4),
        ("earn_coins", "Earn {target} coins", 20, 100),
    ]

    def __init__(self, quest_type=None, target=None, progress=0):
        if quest_type is None:
            qtype, desc_template, min_t, max_t = random.choice(self.QUEST_TYPES)
            self.quest_type = qtype
            self.target = random.randint(min_t, max_t)
            self.description = desc_template.format(target=self.target)
        else:
            self.quest_type = quest_type
            self.target = target
            for qtype, desc_template, _, _ in self.QUEST_TYPES:
                if qtype == quest_type:
                    self.description = desc_template.format(target=target)
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
            "completed": self.completed
        }

    @staticmethod
    def from_dict(d):
        q = Quest(d["quest_type"], d["target"], d["progress"])
        q.completed = d.get("completed", False)
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
        "upgrades": game_state["upgrades"],
        "carried_items": game_state["carried_items"],
        "asteroids": [a.to_dict() for a in game_state["asteroids"]],
        "player_rotation": game_state["player"].rotation,
        "xp": game_state.get("xp", 0),
        "level": game_state.get("level", 1),
        "quests": [q.to_dict() for q in game_state.get("quests", [])],
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
        "upgrades": {"speed": 0, "storage": 0, "shot_damage": 0, "shoot_speed": 0},
        "carried_items": [],
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
    }

def load_game_state_from_data(data):
    state = create_new_game_state()
    state["worldxposition"] = data["worldxposition"]
    state["worldyposition"] = data["worldyposition"]
    state["cam_vx"] = data["cam_vx"]
    state["cam_vy"] = data["cam_vy"]
    state["currency"] = data["currency"]
    state["upgrades"] = data["upgrades"]
    state["carried_items"] = data["carried_items"]
    state["asteroids"] = [Asteroid.from_dict(a) for a in data["asteroids"]]
    state["player"].rotation = data["player_rotation"]
    state["xp"] = data.get("xp", 0)
    state["level"] = data.get("level", 1)
    state["quests"] = [Quest.from_dict(q) for q in data.get("quests", [])]
    if not state["quests"]:
        state["quests"] = [Quest(), Quest(), Quest()]
    return state
# ==================== MAIN GAME ====================
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Asteroid Miner")
    clock = pygame.time.Clock()

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
    }

    # Game constants
    bullet_speed = 900.0
    bullet_life = 2.0
    base_x = 200.0
    base_y = 200.0
    base_sell_radius = 120.0
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

    running = True

    # ==================== MOBILE CONTROLS ====================
    touch_pos = None
    touch_down = False

    joystick_center = (120, SCREEN_H - 120)
    joystick_radius = 90

    fire_button_rect = pygame.Rect(SCREEN_W - 170, SCREEN_H - 170, 140, 140)
    sell_button_rect = pygame.Rect(SCREEN_W - 170, SCREEN_H - 330, 140, 100)


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
                elif current_state == STATE_PLAYING and event.key == pygame.K_ESCAPE:
                    if network_client.connected:
                        network_client.disconnect()
                    if server_process:
                        server_process.terminate()
                        server_process = None
                    if current_world_name and game_state:
                        save_world(current_world_name, game_state)
                    current_state = STATE_MENU
                elif current_state in [STATE_MULTIPLAYER_MENU, STATE_JOIN_GAME, STATE_HOSTING] and event.key == pygame.K_ESCAPE:
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
            # ----- Touch Support -----
            elif event.type == pygame.FINGERDOWN:
                touch_down = True
                touch_pos = (event.x * SCREEN_W, event.y * SCREEN_H)

            elif event.type == pygame.FINGERMOTION:
                touch_pos = (event.x * SCREEN_W, event.y * SCREEN_H)

            elif event.type == pygame.FINGERUP:
                touch_down = False
                touch_pos = None


        screen.fill((10, 10, 30))

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
                    current_state = STATE_PLAYING
                    text_input = ""
                elif cancel_btn.is_clicked(mouse_pos, True):
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
                    # Start server and connect
                    mp_status = "Starting server..."
                    try:
                        server_script = os.path.join(os.path.dirname(__file__), "server.py")
                        server_process = subprocess.Popen(
                            [sys.executable, server_script, str(DEFAULT_PORT)],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                        import time
                        time.sleep(0.5)  # Wait for server to start
                        if network_client.connect("localhost", DEFAULT_PORT, settings["player_name"], settings["ship_color_index"]):
                            game_state = create_new_game_state()
                            current_world_name = "Multiplayer"
                            current_state = STATE_PLAYING
                            mp_status = ""
                        else:
                            mp_status = "Failed to connect to server"
                            if server_process:
                                server_process.terminate()
                                server_process = None
                    except Exception as e:
                        mp_status = f"Error: {str(e)[:30]}"
                elif join_btn.is_clicked(mouse_pos, True):
                    current_state = STATE_JOIN_GAME
                    server_ip = "localhost"
                    server_port = str(DEFAULT_PORT)
                    mp_input_field = 0
                elif back_btn.is_clicked(mouse_pos, True):
                    current_state = STATE_MENU

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

            # ----- KEYBOARD CONTROLS (UNCHANGED) -----
            if KEY[pygame.K_a]:
                move_x -= 1
            if KEY[pygame.K_d]:
              move_x += 1
            if KEY[pygame.K_w]:
             move_y -= 1

            # ----- TOUCH JOYSTICK -----
            if touch_down and touch_pos:
                dx = touch_pos[0] - joystick_center[0]
                dy = touch_pos[1] - joystick_center[1]
                dist = math.hypot(dx, dy)

            if dist < joystick_radius:
                move_x += dx / joystick_radius
                move_y += dy / joystick_radius

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
            if KEY[pygame.K_SPACE] and gs["time_since_shot"] >= fire_cooldown:
                gs["time_since_shot"] = 0.0
                nose_offset = 18.0
                bx = gs["worldxposition"] + fx * nose_offset
                by = gs["worldyposition"] + fy * nose_offset
                bvx = fx * bullet_speed + gs["cam_vx"]
                bvy = fy * bullet_speed + gs["cam_vy"]
                bullets.append({"x": bx, "y": by, "vx": bvx, "vy": bvy, "life": bullet_life})

            for b in bullets[:]:
                b["x"] += b["vx"] * dt
                b["y"] += b["vy"] * dt
                b["life"] -= dt
                if b["life"] <= 0:
                    bullets.remove(b)

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

            for ft in floating_texts:
                sx = int(ft["x"] - gs["worldxposition"] + CX)
                sy = int(ft["y"] - gs["worldyposition"] + CY)
                surf = font.render(ft["text"], True, (255, 255, 80))
                surf.set_alpha(max(0, min(255, int(ft["alpha"]))))
                screen.blit(surf, (sx, sy))

            ship_color = SHIP_COLORS[settings["ship_color_index"]][1]
            cx, cy = 500, 500
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
            base_size = 24
            pygame.draw.rect(screen, (100, 100, 255), (bx_scr - base_size//2, by_scr - base_size//2, base_size, base_size), 2)

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
                
                # Golden asteroid tint
                if asteroid.golden:
                    gold_tint = pygame.Surface((size, size), pygame.SRCALPHA)
                    gold_tint.fill((255, 215, 0, 60))
                    img = img.copy()
                    img.blit(gold_tint, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
                
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
                                        space = max(0, storage_capacity - len(carried_items))
                                        if space > 0:
                                            carried_items.append({
                                                "mat": mat,
                                                "rel_angle": math.pi + random.uniform(-0.8, 0.8),
                                                "ang_vel": random.uniform(-1.0, 1.0),
                                                "length": 55 + random.uniform(-10, 15),
                                                "color": list(color_map.get(mat, (255, 255, 255))),
                                            })
                                            loot_counter[mat] = loot_counter.get(mat, 0) + 1
                                        break
                            for mat, count in loot_counter.items():
                                for _ in range(count):
                                    angle = random.uniform(0, 2*math.pi)
                                    speed = random.uniform(30, 70)
                                    floating_texts.append({
                                        "text": f"+1 {mat}",
                                        "x": asteroid.x,
                                        "y": asteroid.y,
                                        "dx": math.cos(angle)*speed,
                                        "dy": math.sin(angle)*speed,
                                        "alpha": 255,
                                        "timer": 0.0
                                    })

            gs["spawn_timer"] += dt
            if gs["spawn_timer"] >= spawn_interval:
                gs["spawn_timer"] = 0.0
                if len(asteroids) < max_asteroids:
                    ang = random.random() * 2 * math.pi
                    dist = random.randint(250, 600)
                    rx = gs["worldxposition"] + math.cos(ang) * dist
                    ry = gs["worldyposition"] + math.sin(ang) * dist
                    base_dist = math.hypot(rx - base_x, ry - base_y)
                    spawn_chance = max(0.08, 1.0 * math.exp(-base_dist / 3500))
                    if random.random() <= spawn_chance:
                        boss_prob = 0.05
                        is_boss = random.random() < boss_prob and base_dist > 3000
                        if base_dist < 3000:
                            size_scale = 1.0
                        elif base_dist < 6000:
                            size_scale = 2.0
                        elif base_dist < 12000:
                            size_scale = 4.0
                        else:
                            size_scale = 8.0
                        boss_health = int(40 * size_scale) if is_boss else None
                        asteroids.append(Asteroid(rx, ry, random.uniform(-30, 30), random.uniform(-30, 30), health=boss_health, boss=is_boss))
                        if is_boss:
                            asteroids[-1].radius = int(32 * size_scale)
                        else:
                            asteroids[-1].radius = int(8 * size_scale)

            speed = math.hypot(gs["cam_vx"], gs["cam_vy"])
            sx = int(gs["cam_vx"] * 0.05)
            sy = int(gs["cam_vy"] * 0.05)
            cx, cy = 500, 500
            pygame.draw.line(screen, (0, 255, 0), (cx, cy), (cx + sx, cy + sy), 3)

            for b in bullets:
                bx_scr = int(b["x"] - gs["worldxposition"] + CX)
                by_scr = int(b["y"] - gs["worldyposition"] + CY)
                pygame.draw.circle(screen, (255, 220, 0), (bx_scr, by_scr), 3)

            cx, cy = 500, 500
            for item in carried_items:
                world_angle = player.rotation + item["rel_angle"]
                ix = cx + int(math.sin(world_angle) * item["length"])
                iy = cy + int(-math.cos(world_angle) * item["length"])
                pygame.draw.line(screen, (120, 120, 120), (cx, cy), (ix, iy), 2)
                pygame.draw.circle(screen, tuple(item["color"]), (ix, iy), 6)

            storage_capacity = 5 + 5 * upgrades.get("storage", 0)
            storage_used = len(carried_items)
            screen.blit(font.render(f"Speed: {speed:.1f}", True, (255, 255, 255)), (10, 10))
            screen.blit(font.render(f"Cargo: {storage_used}/{storage_capacity}", True, (255, 255, 255)), (10, 36))
            screen.blit(font.render(f"Coins: ${gs['currency']:.2f}", True, (255, 220, 100)), (10, 56))
            screen.blit(font.render(f"World: {current_world_name}", True, (180, 180, 255)), (10, 76))
            screen.blit(font.render(f"{settings['player_name']}", True, (200, 255, 200)), (10, 96))
            screen.blit(font.render("ESC = Save & Menu", True, (150, 150, 150)), (10, SCREEN_H - 30))

            pdist = math.hypot(gs["worldxposition"] - base_x, gs["worldyposition"] - base_y)
            if pdist <= base_sell_radius:
                sell_text = font.render("At base: E = sell, click upgrade below", True, (180, 180, 255))
                screen.blit(sell_text, (SCREEN_W//2 - 160, 10))

                upg_costs = [10 * (2.8 ** upgrades[k]) for k in ["speed", "storage", "shot_damage", "shoot_speed"]]
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

                if KEY[pygame.K_e] and carried_items:
                    prices = {"Iron": 1.0, "Copper": 2.0, "Gold": 4.0, "Titanium": 6.0, "Platinum": 8.0, "Uranium": 10.0, "Diamond": 14.0}
                    counts = {}
                    for it in carried_items:
                        counts[it["mat"]] = counts.get(it["mat"], 0) + 1
                    total = 0.0
                    for mat, qty in counts.items():
                        total += prices.get(mat, 0) * qty
                    carried_items.clear()
                    gs["currency"] += round(total, 2)

        pygame.display.flip()

    if current_state == STATE_PLAYING and current_world_name and game_state:
        save_world(current_world_name, game_state)

    pygame.quit()

if __name__ == "__main__":
    main()
