import pygame
import cv2
import sys
import glob
import socket
import json
import threading
import time
import random

# Initialize Pygame
pygame.init()

# Constants
WIDTH, HEIGHT = 1280, 720
FPS = 60
WHITE = (255, 255, 255)
CYAN = (0, 255, 255)
DARK_BG = (10, 10, 30)
FONT_PATH = pygame.font.match_font('couriernew', bold=True)

# Network settings
SERVER_HOST = 'localhost'
SERVER_PORT = 5555

class Network:
    def __init__(self):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server = SERVER_HOST
        self.port = SERVER_PORT
        self.addr = (self.server, self.port)
        self.connect()
        
    def connect(self):
        try:
            self.client.connect(self.addr)
            return True
        except:
            return False
            
    def send(self, data):
        try:
            self.client.send(json.dumps(data).encode('utf-8'))
            return True
        except:
            return False
            
    def receive(self):
        try:
            data = self.client.recv(1024).decode('utf-8')
            return json.loads(data)
        except:
            return None

# Set up display
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Tetris Lobby")
clock = pygame.time.Clock()

def show_loading_screen():
    cap = cv2.VideoCapture(r"TETRISBG1.mp4")
    if not cap.isOpened():
        print("Failed to load loading video.")
        return

    pressed_to_continue = False

    while not pressed_to_continue:
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

        frame = cv2.resize(frame, (WIDTH, HEIGHT))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        surface = pygame.surfarray.make_surface(frame.swapaxes(0, 1))

        screen.blit(surface, (0, 0))
        pygame.display.flip()
        clock.tick(30)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                cap.release()
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                pressed_to_continue = True

    cap.release()

def run_login_screen():
    font = pygame.font.Font(FONT_PATH, 40)
    input_font = pygame.font.Font(FONT_PATH, 32)

    username = ""
    password = ""
    input_active = "username"  # or "password"
    done = False
    error_message = ""
    error_timer = 0

    cap = cv2.VideoCapture(r"LOGIN.mp4")
    bg_frame_timer = 0
    bg_fps = 15
    bg_frame_surface = None

    def update_bg():
        nonlocal bg_frame_surface, bg_frame_timer
        now = pygame.time.get_ticks()
        if now - bg_frame_timer > 1000 // bg_fps:
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = cap.read()
            if ret:
                frame = cv2.resize(frame, (WIDTH, HEIGHT))
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                bg_frame_surface = pygame.surfarray.make_surface(frame.swapaxes(0, 1))
            bg_frame_timer = now

    def check_credentials(username, password):
        try:
            with open('players.txt', 'r') as file:
                for line in file:
                    if line.strip() and not line.startswith('#'):
                        stored_username, stored_password = line.strip().split(':')
                        if stored_username == username:
                            return stored_password == password
            return False
        except FileNotFoundError:
            return False

    def save_credentials(username, password):
        try:
            with open('players.txt', 'a') as file:
                file.write(f"{username}:{password}\n")
            return True
        except Exception as e:
            print(f"Error saving credentials: {e}")
            return False

    while not done:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                cap.release()
                pygame.quit()
                sys.exit()

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_TAB:
                    input_active = "password" if input_active == "username" else "username"
                elif event.key == pygame.K_RETURN:
                    if username and password:
                        if check_credentials(username, password):
                            done = True
                        else:
                            # Try to register new user
                            if save_credentials(username, password):
                                done = True
                            else:
                                error_message = "Error creating account"
                                error_timer = pygame.time.get_ticks()
                    else:
                        error_message = "Please enter both username and password"
                        error_timer = pygame.time.get_ticks()
                elif event.key == pygame.K_BACKSPACE:
                    if input_active == "username":
                        username = username[:-1]
                    else:
                        password = password[:-1]
                else:
                    if input_active == "username":
                        username += event.unicode
                    else:
                        password += event.unicode

        update_bg()
        if bg_frame_surface:
            screen.blit(bg_frame_surface, (0, 0))
        else:
            screen.fill(DARK_BG)

        # Render labels and input boxes
        user_label = input_font.render("Username:", True, WHITE)
        pass_label = input_font.render("Password:", True, WHITE)

        screen.blit(user_label, (400, 250))
        screen.blit(pass_label, (400, 320))

        user_input_surface = input_font.render(username, True, CYAN if input_active == "username" else WHITE)
        pass_masked = "*" * len(password)
        pass_input_surface = input_font.render(pass_masked, True, CYAN if input_active == "password" else WHITE)

        pygame.draw.rect(screen, CYAN if input_active == "username" else WHITE, pygame.Rect(600, 245, 300, 40), 2)
        pygame.draw.rect(screen, CYAN if input_active == "password" else WHITE, pygame.Rect(600, 315, 300, 40), 2)

        screen.blit(user_input_surface, (610, 250))
        screen.blit(pass_input_surface, (610, 320))

        instruction = input_font.render("Press TAB to switch fields, ENTER to submit", True, WHITE)
        screen.blit(instruction, (WIDTH // 2 - instruction.get_width() // 2, 400))

        # Display error message if any
        if error_message and pygame.time.get_ticks() - error_timer < 3000:  # Show error for 3 seconds
            error_surface = input_font.render(error_message, True, (255, 0, 0))
            screen.blit(error_surface, (WIDTH // 2 - error_surface.get_width() // 2, 450))

        pygame.display.flip()
        clock.tick(FPS)

    cap.release()
    return username, password

def get_font(size):
    return pygame.font.Font(FONT_PATH, size)

class Button:
    def __init__(self, text, x, y, w, h, callback,
                color_normal=CYAN,
                color_hover=(0, 200, 200),
                color_clicked=(0, 150, 150),
                text_color=DARK_BG,
                font_size=24,
                shadow=True):
        self.text = text
        self.rect = pygame.Rect(x, y, w, h)
        self.callback = callback

        self.color_normal = color_normal
        self.color_hover = color_hover
        self.color_clicked = color_clicked
        self.text_color = text_color
        self.font = get_font(font_size)

        self.hovered = False
        self.clicked = False
        self.shadow = shadow

        self.current_color = self.color_normal

    def draw(self, surface):
        mouse_pos = pygame.mouse.get_pos()
        self.hovered = self.rect.collidepoint(mouse_pos)

        # Determine current color
        if self.clicked:
            target_color = self.color_clicked
        elif self.hovered:
            target_color = self.color_hover
        else:
            target_color = self.color_normal

        # Smooth transition of color (lerp)
        self.current_color = self.lerp_color(self.current_color, target_color, 0.15)

        # Shadow
        if self.shadow:
            shadow_rect = self.rect.copy()
            shadow_rect.topleft = (self.rect.left + 4, self.rect.top + 4)
            pygame.draw.rect(surface, (20, 20, 20), shadow_rect, border_radius=12)

        # Button rect
        pygame.draw.rect(surface, self.current_color, self.rect, border_radius=12)

        # Text
        text_surface = self.font.render(self.text, True, self.text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.hovered:
            self.clicked = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.clicked:
            self.clicked = False
            if self.hovered:
                self.callback()

    @staticmethod
    def lerp_color(color1, color2, t):
        return tuple(
            int(color1[i] + (color2[i] - color1[i]) * t)
            for i in range(3)
        )

class LobbyScreen:
    def __init__(self):
        self.cap = cv2.VideoCapture(r"TETRISBG2.mp4")
        self.bg_frame_timer = 0
        self.bg_fps = 15
        self.bg_frame_surface = None
        self.network = Network()
        self.current_lobby = None
        self.lobby_list = []
        self.receive_thread = None
        self.username = None
        self.player_role = None
        self.lobby_players = []
        self.lobby_roles = {}
        self.lobby_ready = {}
        self.chat_messages = []
        self.max_chat_messages = 10  # Maximum number of messages to display

        self.buttons = [
            Button("Create Lobby", 500, 250, 280, 50, self.create_lobby),
            Button("Join Lobby", 500, 320, 280, 50, self.join_lobby),
            Button("Leaderboard", 500, 390, 280, 50, self.leaderboard),
            Button("Exit", 500, 460, 280, 50, self.exit_game),
        ]

    def start_receive_thread(self):
        self.receive_thread = threading.Thread(target=self.receive_messages)
        self.receive_thread.daemon = True
        self.receive_thread.start()

    def receive_messages(self):
        while True:
            try:
                message = self.network.receive()
                if message:
                    self.handle_server_message(message)
            except:
                break

    def handle_server_message(self, message):
        message_type = message.get('type')
        
        if message_type == 'lobby_created':
            self.current_lobby = message['lobby_id']
            self.player_role = message['role']
        elif message_type == 'player_joined':
            self.lobby_players = message['players']
            self.lobby_roles = message['roles']
            self.lobby_ready = message['ready']
        elif message_type == 'ready_update':
            self.lobby_players = message['players']
            self.lobby_roles = message['roles']
            self.lobby_ready = message['ready']
        elif message_type == 'game_start':
            self.lobby_players = message['players']
            self.lobby_roles = message['roles']
            self.lobby_ready = message['ready']
            # Start the game with the assigned roles
            print(f"Game starting! You are {self.player_role}")
        elif message_type == 'lobby_list':
            self.lobby_list = message['lobbies']
        elif message_type == 'chat_message':
            # Add new message to chat history
            self.chat_messages.append(f"{message['username']}: {message['message']}")
            # Keep only the last max_chat_messages
            if len(self.chat_messages) > self.max_chat_messages:
                self.chat_messages = self.chat_messages[-self.max_chat_messages:]

    def update_video_frame(self):
        now = pygame.time.get_ticks()
        if now - self.bg_frame_timer > 1000 // self.bg_fps:
            ret, frame = self.cap.read()
            if not ret:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
            if ret:
                frame = cv2.resize(frame, (WIDTH, HEIGHT))
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                self.bg_frame_surface = pygame.surfarray.make_surface(frame.swapaxes(0, 1))
            self.bg_frame_timer = now

    def draw(self, surface):
        self.update_video_frame()
        if self.bg_frame_surface:
            surface.blit(self.bg_frame_surface, (0, 0))
        else:
            surface.fill((0, 0, 0)) 

        for button in self.buttons:
            button.draw(surface)

    def create_lobby(self):
        if self.network.send({
            'command': 'create_lobby',
            'username': self.username
        }):
            self.current_lobby = None  # Will be set when server responds
            self.show_lobby_waiting_screen()

    def join_lobby(self):
        self.show_lobby_list()

    def show_lobby_list(self):
        self.network.send({'command': 'get_lobbies'})
        time.sleep(0.1)  # Wait for server response
        
        running = True
        selected_lobby = None
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    # Check if a lobby was clicked
                    for lobby in self.lobby_list:
                        lobby_rect = pygame.Rect(400, 200 + self.lobby_list.index(lobby) * 60, 480, 50)
                        if lobby_rect.collidepoint(event.pos):
                            selected_lobby = lobby['id']
                            running = False
                            break
                            
            self.update_video_frame()
            if self.bg_frame_surface:
                screen.blit(self.bg_frame_surface, (0, 0))
            else:
                screen.fill(DARK_BG)
                
            # Draw lobby list
            font = get_font(24)
            title = font.render("Available Lobbies", True, WHITE)
            screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 150))
            
            for i, lobby in enumerate(self.lobby_list):
                lobby_text = f"Lobby {lobby['id']} - Host: {lobby['host']} - Players: {lobby['players']}/{lobby['max_players']}"
                text_surface = font.render(lobby_text, True, WHITE)
                screen.blit(text_surface, (400, 200 + i * 60))
                
            pygame.display.flip()
            clock.tick(FPS)
            
        if selected_lobby:
            self.join_selected_lobby(selected_lobby)

    def join_selected_lobby(self, lobby_id):
        if self.network.send({
            'command': 'join_lobby',
            'lobby_id': lobby_id,
            'username': self.username
        }):
            self.current_lobby = lobby_id
            self.player_role = 'player2'  # Joining player is always player2
            self.show_lobby_waiting_screen()

    def show_lobby_waiting_screen(self):
        chat_input = ""
        input_active = True
        player_ready = False
        countdown_started = False
        countdown_time = 3  # 3 seconds countdown
        countdown_start = 0

        def toggle_ready():
            nonlocal player_ready
            player_ready = not player_ready
            self.network.send({
                'command': 'ready',
                'lobby_id': self.current_lobby,
                'username': self.username
            })

        def send_chat_message():
            nonlocal chat_input
            if chat_input.strip():
                self.network.send({
                    'command': 'chat',
                    'lobby_id': self.current_lobby,
                    'username': self.username,
                    'message': chat_input.strip()
                })
                chat_input = ""

        def check_all_ready():
            return all(self.lobby_ready.values()) and len(self.lobby_ready) == 2

        ready_button = Button("Ready", WIDTH - 250, HEIGHT - 100, 100, 40, toggle_ready)
        leave_button = Button("Leave", WIDTH - 130, HEIGHT - 100, 100, 40, lambda: self.leave_lobby())

        running = True
        while running:
            current_time = pygame.time.get_ticks()
            
            # Check if countdown should start
            if not countdown_started and check_all_ready():
                countdown_started = True
                countdown_start = current_time
            
            # Check if countdown should end
            if countdown_started:
                elapsed = (current_time - countdown_start) / 1000  # Convert to seconds
                if elapsed >= countdown_time:
                    # Start the game
                    game = MultiplayerGame(screen, self.network, self.username, self.player_role)
                    result = game.run()
                    if result == "menu":
                        return
                    elif result == "exit":
                        self.leave_lobby()
                        pygame.quit()
                        sys.exit()
                    break

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.leave_lobby()
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    if input_active:
                        if event.key == pygame.K_RETURN:
                            send_chat_message()
                        elif event.key == pygame.K_BACKSPACE:
                            chat_input = chat_input[:-1]
                        else:
                            chat_input += event.unicode

                ready_button.handle_event(event)
                leave_button.handle_event(event)

            self.update_video_frame()
            if self.bg_frame_surface:
                screen.blit(self.bg_frame_surface, (0, 0))
            else:
                screen.fill(DARK_BG)

            # Draw lobby info
            font = get_font(24)
            title = font.render(f"Lobby {self.current_lobby}", True, WHITE)
            screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 150))

            # Draw player roles and status
            status_font = get_font(28)
            for i, player in enumerate(self.lobby_players):
                role = self.lobby_roles.get(player, '')
                is_ready = self.lobby_ready.get(player, False)
                role_text = f"{role.upper()}: {player}"
                if player == self.username:
                    role_text += " (You)"
                if is_ready:
                    role_text += " - READY"
                
                # Draw player status box
                p_rect = pygame.Rect(WIDTH // 2 - 200, 250 + i * 80, 400, 60)
                
                # Set box color based on ready status
                box_color = (0, 100, 0) if is_ready else (20, 20, 100)  # Green if ready, dark blue if not
                border_color = (0, 255, 0) if is_ready else CYAN  # Bright green if ready, cyan if not
                
                pygame.draw.rect(screen, box_color, p_rect, border_radius=20)
                pygame.draw.rect(screen, border_color, p_rect, 3, border_radius=20)
                
                # Draw player text
                text_surface = status_font.render(role_text, True, WHITE)
                screen.blit(text_surface, (p_rect.x + (p_rect.width - text_surface.get_width()) // 2,
                                        p_rect.y + (p_rect.height - text_surface.get_height()) // 2))

            # Draw countdown if active
            if countdown_started:
                remaining = countdown_time - (current_time - countdown_start) / 1000
                if remaining > 0:
                    countdown_text = f"Game starting in {int(remaining) + 1}..."
                    countdown_surface = status_font.render(countdown_text, True, (255, 255, 0))  # Yellow color
                    screen.blit(countdown_surface, (WIDTH // 2 - countdown_surface.get_width() // 2, 450))

            # Draw chat box
            chat_box_rect = pygame.Rect(20, 20, 400, 300)
            pygame.draw.rect(screen, (30, 30, 30), chat_box_rect, border_radius=8)
            pygame.draw.rect(screen, CYAN, chat_box_rect, 2, border_radius=8)

            # Draw chat messages
            chat_font = get_font(20)
            for i, msg in enumerate(self.chat_messages[-self.max_chat_messages:]):
                msg_surface = chat_font.render(msg, True, WHITE)
                screen.blit(msg_surface, (30, 30 + i * 25))

            # Draw chat input
            input_rect = pygame.Rect(20, 280, 380, 30)
            pygame.draw.rect(screen, (40, 40, 40), input_rect, border_radius=4)
            pygame.draw.rect(screen, CYAN, input_rect, 1, border_radius=4)
            
            input_surface = chat_font.render(chat_input + "|", True, CYAN)
            screen.blit(input_surface, (25, 285))

            # Draw chat instructions
            instructions = chat_font.render("Press ENTER to send message", True, (150, 150, 150))
            screen.blit(instructions, (20, 320))

            # Draw buttons
            ready_button.draw(screen)
            leave_button.draw(screen)

            pygame.display.flip()
            clock.tick(FPS)

    def leave_lobby(self):
        if self.current_lobby:
            self.network.send({
                'command': 'leave_lobby',
                'lobby_id': self.current_lobby,
                'username': self.username
            })
            self.current_lobby = None

    def exit_game(self):
        self.leave_lobby()
        pygame.quit()
        sys.exit()

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            for button in self.buttons:
                if button.is_clicked(event.pos):
                    button.callback()

    def leaderboard(self):
        leaderboard_data = [
            ("Alice", 1500), ("Bob", 1200), ("Charlie", 1100),
            ("Dave", 1050), ("Eve", 950), ("Frank", 900),
            ("Grace", 850), ("Heidi", 800), ("Ivan", 750),
            ("Judy", 700), ("Mallory", 650), ("Niaj", 600)
        ]

        leaderboard = sorted(leaderboard_data, key=lambda x: x[1], reverse=True)
        
        search_query = ""
        input_active = True
        scroll_offset = 0

        font = get_font(28)
        small_font = get_font(22)
        back_button = Button("Back", 50, HEIGHT - 70, 100, 40, lambda: None)

        cap = cv2.VideoCapture(r"TETRISLEADERBOARD.mp4")
        bg_frame_timer = 0
        bg_fps = 15
        bg_frame_surface = None

        def update_bg():
            nonlocal bg_frame_surface, bg_frame_timer
            now = pygame.time.get_ticks()
            if now - bg_frame_timer > 1000 // bg_fps:
                ret, frame = cap.read()
                if not ret:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = cap.read()
                if ret:
                    frame = cv2.resize(frame, (WIDTH, HEIGHT))
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    bg_frame_surface = pygame.surfarray.make_surface(frame.swapaxes(0, 1))
                bg_frame_timer = now

        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    cap.release()
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    if input_active:
                        if event.key == pygame.K_BACKSPACE:
                            search_query = search_query[:-1]
                        elif event.key == pygame.K_RETURN:
                            scroll_offset = 0
                        else:
                            search_query += event.unicode
                    if event.key == pygame.K_ESCAPE:
                        running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if back_button.is_clicked(event.pos):
                        running = False
                back_button.handle_event(event)

            update_bg()
            if bg_frame_surface:
                screen.blit(bg_frame_surface, (0, 0))
            else:
                screen.fill(DARK_BG)

            # Draw Leaderboard Container
            container_rect = pygame.Rect(360, 150, 560, 430)
            pygame.draw.rect(screen, (15, 15, 25), container_rect, border_radius=15)  # Background
            pygame.draw.rect(screen, (0, 200, 255), container_rect, 3, border_radius=15)  # Outer Border
            pygame.draw.rect(screen, (0, 100, 150), container_rect.inflate(8, 8), 1, border_radius=18)  # Soft glow edge

            # Search bar
            pygame.draw.rect(screen, (20, 20, 20), (400, 110, 480, 40), 0, border_radius=8)
            pygame.draw.rect(screen, CYAN, (400, 110, 480, 40), 2, border_radius=8)
            placeholder = search_query if search_query else "Search player..."
            color = CYAN if search_query else (150, 150, 150)
            search_text = small_font.render(placeholder + ("|" if input_active else ""), True, color)
            screen.blit(search_text, (410, 120))

            # Filter leaderboard entries
            filtered = [(name, score) for name, score in leaderboard if search_query.lower() in name.lower()]

            # Draw leaderboard entries
            start_y = 190
            header_font = get_font(24)
            headers = [("Rank", 380), ("Name", 470), ("Score", 700)]
            for title, x in headers:
                header_text = header_font.render(title, True, CYAN)
                screen.blit(header_text, (x, start_y - 30))

            # Table entries
            for i, (name, score) in enumerate(filtered[scroll_offset:scroll_offset + 10]):
                y = start_y + i * 35

                # Get the real rank from the full sorted leaderboard
                actual_rank = next(idx for idx, (n, s) in enumerate(leaderboard) if n == name and s == score) + 1

                rank_surface = small_font.render(str(actual_rank), True, WHITE)
                name_surface = small_font.render(name, True, WHITE)
                score_surface = small_font.render(str(score), True, WHITE)

                screen.blit(rank_surface, (380, y))
                screen.blit(name_surface, (470, y))
                screen.blit(score_surface, (700, y))

            # Scroll if needed (mouse wheel)
            keys = pygame.key.get_pressed()
            if keys[pygame.K_DOWN] and scroll_offset < len(filtered) - 10:
                scroll_offset += 1
            elif keys[pygame.K_UP] and scroll_offset > 0:
                scroll_offset -= 1

            # Draw back button
            back_button.draw(screen)

            pygame.display.flip()
            clock.tick(FPS)

        cap.release()

class MultiplayerGame:
    def __init__(self, screen, network, username, player_role):
        self.screen = screen
        self.network = network
        self.username = username
        self.player_role = player_role
        
        # Game state
        self.score_p1 = 0
        self.score_p2 = 0
        self.paused = False
        self.show_help = False
        self.game_over = False
        
        # Player names
        self.player1_name = username if player_role == 'player1' else None
        self.player2_name = username if player_role == 'player2' else None
        
        # Get opponent's name from lobby data
        self.network.send({
            'command': 'get_lobby_info',
            'username': username
        })
        
        # Layout
        self.playfield_size = (300, 600)
        self.hold_box_size = (100, 100)
        
        # UI Elements
        self.p1_hold = pygame.Rect(100, 150, *self.hold_box_size)
        self.p1_playfield = pygame.Rect(self.p1_hold.right + 50, 100, *self.playfield_size)
        self.p2_hold = pygame.Rect(WIDTH - 180, 150, *self.hold_box_size)
        self.p2_playfield = pygame.Rect(self.p2_hold.left - 50 - self.playfield_size[0], 100, *self.playfield_size)
        self.pause_button = pygame.Rect(WIDTH - 100, 20, 60, 40)
        self.menu_rect = pygame.Rect(WIDTH // 2 - 150, HEIGHT // 2 - 100, 300, 250)
        
        # Game over buttons
        self.btn_main_menu = pygame.Rect(WIDTH // 2 - 120, HEIGHT - 120, 220, 40)
        self.btn_exit_game = pygame.Rect(WIDTH // 2 - 120, HEIGHT - 60, 220, 40)
        
        # Background video
        self.cap = cv2.VideoCapture(r"TETRISBG2.mp4")
        self.bg_frame_timer = 0
        self.bg_fps = 15
        self.bg_frame_surface = None

        # Tetris game logic
        self.BLOCK_SIZE = 30
        self.BOARD_WIDTH = 10
        self.BOARD_HEIGHT = 20
        
        # Colors for pieces
        self.COLORS = {
            'I': (0, 255, 255),    # Cyan
            'O': (255, 255, 0),    # Yellow
            'T': (128, 0, 128),    # Purple
            'S': (0, 255, 0),      # Green
            'Z': (255, 0, 0),      # Red
            'J': (0, 0, 255),      # Blue
            'L': (255, 127, 0)     # Orange
        }
        
        # Tetromino shapes
        self.SHAPES = {
            'I': [[1, 1, 1, 1]],
            'O': [[1, 1],
                  [1, 1]],
            'T': [[0, 1, 0],
                  [1, 1, 1]],
            'S': [[0, 1, 1],
                  [1, 1, 0]],
            'Z': [[1, 1, 0],
                  [0, 1, 1]],
            'J': [[1, 0, 0],
                  [1, 1, 1]],
            'L': [[0, 0, 1],
                  [1, 1, 1]]
        }
        
        # Initialize game boards for both players
        self.p1_board = [[0 for _ in range(self.BOARD_WIDTH)] for _ in range(self.BOARD_HEIGHT)]
        self.p2_board = [[0 for _ in range(self.BOARD_WIDTH)] for _ in range(self.BOARD_HEIGHT)]
        
        # Initialize current pieces and next pieces
        self.p1_current_piece = None
        self.p1_next_piece = None
        self.p1_hold_piece = None
        self.p1_can_hold = True
        
        self.p2_current_piece = None
        self.p2_next_piece = None
        self.p2_hold_piece = None
        self.p2_can_hold = True
        
        # Initialize piece positions
        self.p1_piece_pos = [0, 0]
        self.p2_piece_pos = [0, 0]
        
        # Game timing
        self.fall_time = 0
        self.fall_speed = 0.5  # Time in seconds between automatic falls
        self.last_fall_time = time.time()
        
        # Combo tracking
        self.p1_combo = 0
        self.p2_combo = 0
        
        # Start receiving thread for game updates
        self.receive_thread = threading.Thread(target=self.receive_game_updates)
        self.receive_thread.daemon = True
        self.receive_thread.start()
        
        # Initialize first pieces
        self.new_piece('p1')
        self.new_piece('p2')

    def draw_text(self, text, pos, font, color=WHITE, center=False):
        render = font.render(text, True, color)
        rect = render.get_rect()
        if center:
            rect.center = pos
        else:
            rect.topleft = pos
        self.screen.blit(render, rect)

    def draw_glow_rect(self, rect, color, border=2):
        pygame.draw.rect(self.screen, color, rect, border)
        glow_surface = pygame.Surface((rect.width+20, rect.height+20), pygame.SRCALPHA)
        pygame.draw.rect(glow_surface, (*color, 80), glow_surface.get_rect(), border_radius=10)
        self.screen.blit(glow_surface, (rect.x - 10, rect.y - 10))

    def new_piece(self, player):
        """Generate a new piece for the specified player"""
        if player == 'p1':
            if not self.p1_next_piece:
                self.p1_next_piece = random.choice(list(self.SHAPES.keys()))
            self.p1_current_piece = self.p1_next_piece
            self.p1_next_piece = random.choice(list(self.SHAPES.keys()))
            self.p1_piece_pos = [self.BOARD_WIDTH // 2 - len(self.SHAPES[self.p1_current_piece][0]) // 2, 0]
            self.p1_can_hold = True
        else:
            if not self.p2_next_piece:
                self.p2_next_piece = random.choice(list(self.SHAPES.keys()))
            self.p2_current_piece = self.p2_next_piece
            self.p2_next_piece = random.choice(list(self.SHAPES.keys()))
            self.p2_piece_pos = [self.BOARD_WIDTH // 2 - len(self.SHAPES[self.p2_current_piece][0]) // 2, 0]
            self.p2_can_hold = True

    def rotate_piece(self, piece, board, pos):
        """Rotate a piece clockwise"""
        # Create a new rotated piece
        new_piece = list(zip(*piece[::-1]))
        
        # Check if rotation is valid
        if self.is_valid_move(new_piece, board, pos):
            return new_piece
        return piece

    def is_valid_move(self, piece, board, pos):
        """Check if a move is valid"""
        for y, row in enumerate(piece):
            for x, cell in enumerate(row):
                if cell:
                    board_x = pos[0] + x
                    board_y = pos[1] + y
                    if (board_x < 0 or board_x >= self.BOARD_WIDTH or
                        board_y >= self.BOARD_HEIGHT or
                        (board_y >= 0 and board[board_y][board_x])):
                        return False
        return True

    def merge_piece(self, piece, board, pos):
        """Merge a piece into the board"""
        for y, row in enumerate(piece):
            for x, cell in enumerate(row):
                if cell:
                    board_y = pos[1] + y
                    board_x = pos[0] + x
                    if board_y >= 0:
                        # Determine which player's board we're merging into
                        if board is self.p1_board:
                            board[board_y][board_x] = self.COLORS[self.p1_current_piece]
                        else:
                            board[board_y][board_x] = self.COLORS[self.p2_current_piece]

    def clear_lines(self, board):
        """Clear completed lines and return the number of lines cleared"""
        lines_cleared = 0
        y = self.BOARD_HEIGHT - 1
        while y >= 0:
            if all(board[y]):
                lines_cleared += 1
                # Move all lines above down
                for y2 in range(y, 0, -1):
                    board[y2] = board[y2-1][:]
                board[0] = [0] * self.BOARD_WIDTH
            else:
                y -= 1
        return lines_cleared

    def hold_piece(self, player):
        """Hold the current piece"""
        if player == 'p1':
            if self.p1_can_hold:
                if self.p1_hold_piece:
                    self.p1_current_piece, self.p1_hold_piece = self.p1_hold_piece, self.p1_current_piece
                else:
                    self.p1_hold_piece = self.p1_current_piece
                    self.new_piece('p1')
                self.p1_can_hold = False
        else:
            if self.p2_can_hold:
                if self.p2_hold_piece:
                    self.p2_current_piece, self.p2_hold_piece = self.p2_hold_piece, self.p2_current_piece
                else:
                    self.p2_hold_piece = self.p2_current_piece
                    self.new_piece('p2')
                self.p2_can_hold = False

    def draw_piece(self, piece, pos, color, surface, offset=(0, 0)):
        """Draw a piece on the surface"""
        for y, row in enumerate(piece):
            for x, cell in enumerate(row):
                if cell:
                    rect = pygame.Rect(
                        offset[0] + (pos[0] + x) * self.BLOCK_SIZE,
                        offset[1] + (pos[1] + y) * self.BLOCK_SIZE,
                        self.BLOCK_SIZE - 1,
                        self.BLOCK_SIZE - 1
                    )
                    pygame.draw.rect(surface, color, rect)
                    pygame.draw.rect(surface, (255, 255, 255), rect, 1)

    def draw_board(self, board, surface, offset=(0, 0)):
        """Draw the game board"""
        for y, row in enumerate(board):
            for x, cell in enumerate(row):
                if cell:
                    rect = pygame.Rect(
                        offset[0] + x * self.BLOCK_SIZE,
                        offset[1] + y * self.BLOCK_SIZE,
                        self.BLOCK_SIZE - 1,
                        self.BLOCK_SIZE - 1
                    )
                    pygame.draw.rect(surface, cell, rect)
                    pygame.draw.rect(surface, (255, 255, 255), rect, 1)

    def draw_playfield(self):
        # Update player names if they're not set
        if self.player_role == 'player1' and not self.player2_name:
            self.player2_name = "Waiting for opponent..."
        elif self.player_role == 'player2' and not self.player1_name:
            self.player1_name = "Waiting for opponent..."

        self.draw_text(self.player1_name or "Waiting for opponent...", (self.p1_playfield.x, 50), get_font(36))
        self.draw_text(self.player2_name or "Waiting for opponent...", (self.p2_playfield.x, 50), get_font(36))

        # Box sizes
        next_box_size = (100, 240)
        hold_box_size = (80, 80)
        score_box_size = (100, 50)
        combo_box_size = (100, 40)
        ui_spacing = 30

        # Shift playfields toward center
        self.p1_playfield.x = 200
        self.p2_playfield.x = 800

        # P1 UI elements
        p1_next_box = pygame.Rect(self.p1_playfield.right + ui_spacing, self.p1_playfield.y, *next_box_size)
        p1_hold = pygame.Rect(self.p1_playfield.left - ui_spacing - hold_box_size[0], self.p1_playfield.y, *hold_box_size)
        p1_score_box = pygame.Rect(70, p1_hold.bottom + 50, *score_box_size)
        p1_combo_box = pygame.Rect(p1_score_box.x, p1_score_box.bottom + 50, *combo_box_size)

        # P2 UI elements
        p2_next_box = pygame.Rect(self.p2_playfield.left - ui_spacing - next_box_size[0], self.p2_playfield.y, *next_box_size)
        p2_hold = pygame.Rect(self.p2_playfield.right + ui_spacing, self.p2_playfield.y, *hold_box_size)
        p2_score_box = pygame.Rect(p2_hold.x, p2_hold.bottom + 50, *score_box_size)
        p2_combo_box = pygame.Rect(p2_score_box.x, p2_score_box.bottom + 50, *combo_box_size)

        # Draw Playfields
        for rect in [self.p1_playfield, self.p2_playfield]:
            overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 120))
            self.screen.blit(overlay, rect)
            self.draw_glow_rect(rect, CYAN)

        # Draw boards
        self.draw_board(self.p1_board, self.screen, (self.p1_playfield.x, self.p1_playfield.y))
        self.draw_board(self.p2_board, self.screen, (self.p2_playfield.x, self.p2_playfield.y))

        # Draw current pieces
        if self.p1_current_piece:
            self.draw_piece(
                self.SHAPES[self.p1_current_piece],
                self.p1_piece_pos,
                self.COLORS[self.p1_current_piece],
                self.screen,
                (self.p1_playfield.x, self.p1_playfield.y)
            )
        if self.p2_current_piece:
            self.draw_piece(
                self.SHAPES[self.p2_current_piece],
                self.p2_piece_pos,
                self.COLORS[self.p2_current_piece],
                self.screen,
                (self.p2_playfield.x, self.p2_playfield.y)
            )

        # Draw UI Boxes
        for box, label, value in [
            (p1_hold, "Hold", None), (p2_hold, "Hold", None),
            (p1_score_box, "Score:", self.score_p1), (p2_score_box, "Score:", self.score_p2),
            (p1_combo_box, "Combo:", self.p1_combo), (p2_combo_box, "Combo:", self.p2_combo),
        ]:
            self.draw_text(label, (box.x, box.y - 25), get_font(24))
            overlay = pygame.Surface(box.size, pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 120))
            self.screen.blit(overlay, box)
            self.draw_glow_rect(box, CYAN)
            if value is not None:
                self.draw_text(str(value), box.center, get_font(24), center=True)

        # Draw Next Boxes
        for rect, label in [(p1_next_box, "Next"), (p2_next_box, "Next")]:
            overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 120))
            self.screen.blit(overlay, rect)
            self.draw_glow_rect(rect, CYAN)
            self.draw_text(label, (rect.x, rect.y - 25), get_font(24))

        # Draw hold pieces
        if self.p1_hold_piece:
            self.draw_piece(
                self.SHAPES[self.p1_hold_piece],
                [1, 1],
                self.COLORS[self.p1_hold_piece],
                self.screen,
                (p1_hold.x, p1_hold.y)
            )
        if self.p2_hold_piece:
            self.draw_piece(
                self.SHAPES[self.p2_hold_piece],
                [1, 1],
                self.COLORS[self.p2_hold_piece],
                self.screen,
                (p2_hold.x, p2_hold.y)
            )

        # Draw next pieces
        if self.p1_next_piece:
            self.draw_piece(
                self.SHAPES[self.p1_next_piece],
                [1, 1],
                self.COLORS[self.p1_next_piece],
                self.screen,
                (p1_next_box.x, p1_next_box.y)
            )
        if self.p2_next_piece:
            self.draw_piece(
                self.SHAPES[self.p2_next_piece],
                [1, 1],
                self.COLORS[self.p2_next_piece],
                self.screen,
                (p2_next_box.x, p2_next_box.y)
            )

        pygame.draw.rect(self.screen, CYAN, self.pause_button, 2)
        self.draw_text("Menu", self.pause_button.center, get_font(24), center=True)

    def draw_menu(self):
        pygame.draw.rect(self.screen, (10, 10, 30, 220), self.menu_rect)
        self.draw_glow_rect(self.menu_rect, CYAN, 2)

        self.draw_text("Game Paused", (self.menu_rect.centerx, self.menu_rect.y + 20), get_font(36), center=True)
        self.draw_text("Resume (R)", (self.menu_rect.x + 20, self.menu_rect.y + 80), get_font(24))
        self.draw_text("Help (H)", (self.menu_rect.x + 20, self.menu_rect.y + 120), get_font(24))
        self.draw_text("Quit (Q)", (self.menu_rect.x + 20, self.menu_rect.y + 160), get_font(24))

        if self.show_help:
            self.draw_text("Controls:", (self.menu_rect.x + 150, self.menu_rect.y + 80), get_font(24))
            self.draw_text("←→↓ to move", (self.menu_rect.x + 150, self.menu_rect.y + 110), get_font(24))
            self.draw_text("Space to drop", (self.menu_rect.x + 150, self.menu_rect.y + 140), get_font(24))
            self.draw_text("C to hold", (self.menu_rect.x + 150, self.menu_rect.y + 170), get_font(24))

    def draw_video_background(self):
        now = pygame.time.get_ticks()
        if now - self.bg_frame_timer > 1000 // self.bg_fps:
            ret, frame = self.cap.read()
            if not ret:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
            if ret:
                frame = cv2.resize(frame, (WIDTH, HEIGHT))
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                self.bg_frame_surface = pygame.surfarray.make_surface(frame.swapaxes(0, 1))
            self.bg_frame_timer = now

        if self.bg_frame_surface:
            self.screen.blit(self.bg_frame_surface, (0, 0))
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 120))
            self.screen.blit(overlay, (0, 0))

    def draw_game_over(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))

        if self.score_p1 > self.score_p2:
            winner = f"{self.player1_name} Wins!"
        elif self.score_p2 > self.score_p1:
            winner = f"{self.player2_name} Wins!"
        else:
            winner = "It's a Tie!"

        self.draw_text("Game Over", (WIDTH // 2, 80), get_font(36), center=True)
        self.draw_text(winner, (WIDTH // 2, 130), get_font(36), center=True)

        pygame.draw.rect(self.screen, (30, 30, 30), self.btn_main_menu)
        pygame.draw.rect(self.screen, CYAN, self.btn_main_menu, 2)
        self.draw_text("Return to Main Menu", self.btn_main_menu.center, get_font(24), center=True)

        pygame.draw.rect(self.screen, (30, 30, 30), self.btn_exit_game)
        pygame.draw.rect(self.screen, CYAN, self.btn_exit_game, 2)
        self.draw_text("Exit Game", self.btn_exit_game.center, get_font(24), center=True)

    def run(self):
        running = True
        while running:
            clock.tick(60)  # Increased FPS for smoother gameplay
            
            # Handle piece falling
            current_time = time.time()
            if current_time - self.last_fall_time > self.fall_speed:
                self.last_fall_time = current_time
                
                # Move pieces down
                if self.player_role == 'player1':
                    if self.p1_current_piece:
                        new_pos = [self.p1_piece_pos[0], self.p1_piece_pos[1] + 1]
                        if self.is_valid_move(self.SHAPES[self.p1_current_piece], self.p1_board, new_pos):
                            self.p1_piece_pos = new_pos
                        else:
                            self.merge_piece(self.SHAPES[self.p1_current_piece], self.p1_board, self.p1_piece_pos)
                            lines = self.clear_lines(self.p1_board)
                            if lines > 0:
                                self.p1_combo += 1
                                self.score_p1 += lines * 100 * self.p1_combo
                                self.network.send({
                                    'command': 'game_update',
                                    'type': 'score_update',
                                    'player': 'p1',
                                    'score': self.score_p1,
                                    'combo': self.p1_combo
                                })
                            else:
                                self.p1_combo = 0
                            self.new_piece('p1')
                else:
                    if self.p2_current_piece:
                        new_pos = [self.p2_piece_pos[0], self.p2_piece_pos[1] + 1]
                        if self.is_valid_move(self.SHAPES[self.p2_current_piece], self.p2_board, new_pos):
                            self.p2_piece_pos = new_pos
                        else:
                            self.merge_piece(self.SHAPES[self.p2_current_piece], self.p2_board, self.p2_piece_pos)
                            lines = self.clear_lines(self.p2_board)
                            if lines > 0:
                                self.p2_combo += 1
                                self.score_p2 += lines * 100 * self.p2_combo
                                self.network.send({
                                    'command': 'game_update',
                                    'type': 'score_update',
                                    'player': 'p2',
                                    'score': self.score_p2,
                                    'combo': self.p2_combo
                                })
                            else:
                                self.p2_combo = 0
                            self.new_piece('p2')

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                if not self.game_over:
                    if event.type == pygame.MOUSEBUTTONDOWN and self.pause_button.collidepoint(event.pos):
                        self.paused = not self.paused
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            self.paused = not self.paused
                        elif self.paused:
                            if event.key == pygame.K_r:
                                self.paused = False
                            elif event.key == pygame.K_h:
                                self.show_help = not self.show_help
                            elif event.key == pygame.K_q:
                                running = False
                        else:
                            # Handle game controls
                            if self.player_role == 'player1':
                                if event.key == pygame.K_LEFT:
                                    new_pos = [self.p1_piece_pos[0] - 1, self.p1_piece_pos[1]]
                                    if self.is_valid_move(self.SHAPES[self.p1_current_piece], self.p1_board, new_pos):
                                        self.p1_piece_pos = new_pos
                                elif event.key == pygame.K_RIGHT:
                                    new_pos = [self.p1_piece_pos[0] + 1, self.p1_piece_pos[1]]
                                    if self.is_valid_move(self.SHAPES[self.p1_current_piece], self.p1_board, new_pos):
                                        self.p1_piece_pos = new_pos
                                elif event.key == pygame.K_DOWN:
                                    new_pos = [self.p1_piece_pos[0], self.p1_piece_pos[1] + 1]
                                    if self.is_valid_move(self.SHAPES[self.p1_current_piece], self.p1_board, new_pos):
                                        self.p1_piece_pos = new_pos
                                elif event.key == pygame.K_UP:
                                    rotated = self.rotate_piece(self.SHAPES[self.p1_current_piece], self.p1_board, self.p1_piece_pos)
                                    if rotated != self.SHAPES[self.p1_current_piece]:
                                        self.SHAPES[self.p1_current_piece] = rotated
                                elif event.key == pygame.K_SPACE:
                                    # Hard drop
                                    while self.is_valid_move(self.SHAPES[self.p1_current_piece], self.p1_board, [self.p1_piece_pos[0], self.p1_piece_pos[1] + 1]):
                                        self.p1_piece_pos[1] += 1
                                elif event.key == pygame.K_c:
                                    self.hold_piece('p1')
                            else:
                                if event.key == pygame.K_LEFT:
                                    new_pos = [self.p2_piece_pos[0] - 1, self.p2_piece_pos[1]]
                                    if self.is_valid_move(self.SHAPES[self.p2_current_piece], self.p2_board, new_pos):
                                        self.p2_piece_pos = new_pos
                                elif event.key == pygame.K_RIGHT:
                                    new_pos = [self.p2_piece_pos[0] + 1, self.p2_piece_pos[1]]
                                    if self.is_valid_move(self.SHAPES[self.p2_current_piece], self.p2_board, new_pos):
                                        self.p2_piece_pos = new_pos
                                elif event.key == pygame.K_DOWN:
                                    new_pos = [self.p2_piece_pos[0], self.p2_piece_pos[1] + 1]
                                    if self.is_valid_move(self.SHAPES[self.p2_current_piece], self.p2_board, new_pos):
                                        self.p2_piece_pos = new_pos
                                elif event.key == pygame.K_UP:
                                    rotated = self.rotate_piece(self.SHAPES[self.p2_current_piece], self.p2_board, self.p2_piece_pos)
                                    if rotated != self.SHAPES[self.p2_current_piece]:
                                        self.SHAPES[self.p2_current_piece] = rotated
                                elif event.key == pygame.K_SPACE:
                                    # Hard drop
                                    while self.is_valid_move(self.SHAPES[self.p2_current_piece], self.p2_board, [self.p2_piece_pos[0], self.p2_piece_pos[1] + 1]):
                                        self.p2_piece_pos[1] += 1
                                elif event.key == pygame.K_c:
                                    self.hold_piece('p2')
                else:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        if self.btn_main_menu.collidepoint(event.pos):
                            return "menu"
                        elif self.btn_exit_game.collidepoint(event.pos):
                            running = False

            self.draw_video_background()

            if self.game_over:
                self.draw_game_over()
            else:
                self.draw_playfield()
                if self.paused:
                    self.draw_menu()

            pygame.display.flip()

        self.cap.release()
        return "exit"

    def receive_game_updates(self):
        while True:
            try:
                message = self.network.receive()
                if message:
                    if message.get('type') == 'player_joined':
                        # Update opponent's name when they join
                        if self.player_role == 'player1':
                            self.player2_name = message.get('username')
                        else:
                            self.player1_name = message.get('username')
                    elif message.get('type') == 'lobby_info':
                        # Update player names from lobby info
                        players = message.get('players', [])
                        roles = message.get('roles', {})
                        for player in players:
                            if player != self.username:
                                if roles.get(player) == 'player1':
                                    self.player1_name = player
                                else:
                                    self.player2_name = player
                    elif message.get('type') == 'game_update':
                        # Handle other game updates here
                        pass
            except:
                break

def main():
    # Play loading video and wait for key press
    show_loading_screen()

    # Show login screen and get username and password
    username, password = run_login_screen()
    print(f"Username: {username}, Password: {password}")

    # Start lobby screen loop
    lobby_screen = LobbyScreen()
    lobby_screen.username = username
    lobby_screen.start_receive_thread()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            for button in lobby_screen.buttons:
                button.handle_event(event)

        lobby_screen.draw(screen)
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()