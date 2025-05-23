import pygame
import sys
import cv2
import numpy as np
import random

# === Pygame Init ===
pygame.init()
pygame.font.init()

# === Screen Setup ===
SCREEN_WIDTH, SCREEN_HEIGHT = 1280, 720
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Multiplayer Tetris")
clock = pygame.time.Clock() 

# === OpenCV Video Background ===
video_path = r"TETRISBG2.mp4"
cap = cv2.VideoCapture(video_path)

# === Fonts & Colors ===
font_large = pygame.font.SysFont("Orbitron", 36)  # Use Orbitron or futuristic font if available
font_small = pygame.font.SysFont("Orbitron", 24)
WHITE = (255, 255, 255)
CYAN = (0, 255, 255)
OVERLAY_COLOR = (0, 0, 0, 120)

# === Layout Rects ===
playfield_size = (300, 600)
hold_box_size = (100, 100)

p1_hold = pygame.Rect(100, 150, *hold_box_size)
p1_playfield = pygame.Rect(p1_hold.right + 50, 100, *playfield_size)

p2_hold = pygame.Rect(SCREEN_WIDTH - 180, 150, *hold_box_size)
p2_playfield = pygame.Rect(p2_hold.left - 50 - playfield_size[0], 100, *playfield_size)

pause_button = pygame.Rect(SCREEN_WIDTH - 100, 20, 60, 40)
menu_rect = pygame.Rect(SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT // 2 - 100, 300, 250)

# === Tetromino Shapes ===
SHAPES = {
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

# === Colors ===
COLORS = {
    'I': (0, 255, 255),    # Cyan
    'O': (255, 255, 0),    # Yellow
    'T': (128, 0, 128),    # Purple
    'S': (0, 255, 0),      # Green
    'Z': (255, 0, 0),      # Red
    'J': (0, 0, 255),      # Blue
    'L': (255, 127, 0)     # Orange
}

# Add color gradients for each piece
COLOR_GRADIENTS = {
    'I': [(0, 200, 255), (0, 255, 255)],  # Light to dark cyan
    'O': [(255, 200, 0), (255, 255, 0)],  # Light to dark yellow
    'T': [(180, 0, 180), (128, 0, 128)],  # Light to dark purple
    'S': [(0, 200, 0), (0, 255, 0)],      # Light to dark green
    'Z': [(255, 50, 50), (255, 0, 0)],    # Light to dark red
    'J': [(50, 50, 255), (0, 0, 255)],    # Light to dark blue
    'L': [(255, 180, 0), (255, 127, 0)]   # Light to dark orange
}

# === Game Constants ===
BLOCK_SIZE = 30
PREVIEW_BLOCK_SIZE = 20  # Smaller size for preview blocks
GRID_WIDTH = 10
GRID_HEIGHT = 20
FALL_SPEED = 0.5  # seconds per cell
LOCK_DELAY = 0.1  # seconds before piece locks

# === Player Class ===
class Player:
    def __init__(self, playfield_rect):
        self.playfield_rect = playfield_rect
        self.grid = [[0 for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.current_piece = None
        self.next_pieces = []
        self.held_piece = None
        self.can_hold = True
        self.score = 0
        self.combo = 0
        self.fall_time = 0
        self.lock_time = 0
        self.game_over = False
        self.shadow_y = 0
        self.pending_garbage = 0  # Number of garbage lines to receive
        self.garbage_send_buffer = 0  # Accumulated garbage to send
        
    def new_piece(self):
        # Initialize next pieces if empty
        if not self.next_pieces:
            for _ in range(3):  # Keep 3 pieces in queue
                self.next_pieces.append(random.choice(list(SHAPES.keys())))
                
        self.current_piece = {
            'shape': self.next_pieces[0],
            'rotation': 0,
            'x': GRID_WIDTH // 2 - len(SHAPES[self.next_pieces[0]][0]) // 2,
            'y': 0
        }
        self.next_pieces.pop(0)  # Remove the used piece
        self.next_pieces.append(random.choice(list(SHAPES.keys())))  # Add new piece
        self.can_hold = True
        
        if self.check_collision():
            self.game_over = True

    def hold_piece(self):
        if not self.can_hold:
            return
            
        if self.held_piece is None:
            self.held_piece = self.current_piece['shape']
            self.new_piece()
        else:
            self.held_piece, self.current_piece['shape'] = self.current_piece['shape'], self.held_piece
            self.current_piece['rotation'] = 0
            self.current_piece['x'] = GRID_WIDTH // 2 - len(SHAPES[self.current_piece['shape']][0]) // 2
            self.current_piece['y'] = 0
            
        self.can_hold = False

    def rotate_piece(self):
        shape = SHAPES[self.current_piece['shape']]
        rotated = list(zip(*shape[::-1]))  # Rotate 90 degrees clockwise
        old_rotation = self.current_piece['rotation']
        self.current_piece['rotation'] = (self.current_piece['rotation'] + 1) % 4
        
        # Try rotation, if collision occurs, try wall kicks
        if self.check_collision():
            # Wall kick attempts
            kicks = [(1, 0), (-1, 0), (0, -1), (1, -1), (-1, -1)]
            for dx, dy in kicks:
                self.current_piece['x'] += dx
                self.current_piece['y'] += dy
                if not self.check_collision():
                    return
                self.current_piece['x'] -= dx
                self.current_piece['y'] -= dy
            
            # If all kicks fail, revert rotation
            self.current_piece['rotation'] = old_rotation

    def move_piece(self, dx, dy):
        self.current_piece['x'] += dx
        self.current_piece['y'] += dy
        if self.check_collision():
            self.current_piece['x'] -= dx
            self.current_piece['y'] -= dy
            if dy > 0:  # If moving downward and collision occurs
                self.lock_time = LOCK_DELAY  # Immediately trigger lock
            return False
        return True

    def check_collision(self):
        shape = SHAPES[self.current_piece['shape']]
        for _ in range(self.current_piece['rotation']):
            shape = list(zip(*shape[::-1]))
            
        for y, row in enumerate(shape):
            for x, cell in enumerate(row):
                if cell:
                    board_x = self.current_piece['x'] + x
                    board_y = self.current_piece['y'] + y
                    if (board_x < 0 or board_x >= GRID_WIDTH or 
                        board_y >= GRID_HEIGHT or 
                        (board_y >= 0 and self.grid[board_y][board_x])):
                        return True
        return False

    def lock_piece(self):
        shape = SHAPES[self.current_piece['shape']]
        for _ in range(self.current_piece['rotation']):
            shape = list(zip(*shape[::-1]))
            
        for y, row in enumerate(shape):
            for x, cell in enumerate(row):
                if cell:
                    board_x = self.current_piece['x'] + x
                    board_y = self.current_piece['y'] + y
                    if board_y >= 0:
                        self.grid[board_y][board_x] = self.current_piece['shape']

    def add_garbage_lines(self, num_lines):
        if num_lines <= 0:
            return
            
        # Move all existing blocks up by num_lines
        for y in range(num_lines, GRID_HEIGHT):
            self.grid[y - num_lines] = self.grid[y][:]
        
        # Add garbage lines at the bottom
        for y in range(GRID_HEIGHT - num_lines, GRID_HEIGHT):
            # Create a garbage line with a random hole
            hole_pos = random.randint(0, GRID_WIDTH - 1)
            self.grid[y] = ['G' for _ in range(GRID_WIDTH)]
            self.grid[y][hole_pos] = 0  # Create a hole in the garbage line
            
        # Check if the new garbage lines cause game over
        if self.check_collision():
            self.game_over = True

    def clear_lines(self):
        lines_cleared = 0
        y = GRID_HEIGHT - 1
        while y >= 0:
            if all(self.grid[y]):
                lines_cleared += 1
                for y2 in range(y, 0, -1):
                    self.grid[y2] = self.grid[y2-1][:]
                self.grid[0] = [0] * GRID_WIDTH
            else:
                y -= 1
                
        if lines_cleared > 0:
            self.combo += 1
            points = {1: 100, 2: 300, 3: 500, 4: 800}
            self.score += points.get(lines_cleared, 0) * self.combo
            
            # Calculate garbage to send based on lines cleared
            garbage_to_send = 0
            if lines_cleared == 2:
                garbage_to_send = 1
            elif lines_cleared == 3:
                garbage_to_send = 2
            elif lines_cleared == 4:
                garbage_to_send = 4
                
            self.garbage_send_buffer += garbage_to_send
        else:
            self.combo = 0

    def update(self, dt):
        if self.game_over:
            return
            
        if self.current_piece is None:
            self.new_piece()
            
        self.fall_time += dt
        if self.fall_time >= FALL_SPEED:
            self.fall_time = 0
            if not self.move_piece(0, 1):
                self.lock_time += dt
                if self.lock_time >= LOCK_DELAY:
                    self.lock_piece()
                    self.clear_lines()
                    self.new_piece()
                    self.lock_time = 0
            else:
                self.lock_time = 0

    def get_shadow_position(self):
        if not self.current_piece:
            return None
            
        # Create a copy of the current piece to test drop position
        shadow_piece = {
            'shape': self.current_piece['shape'],
            'rotation': self.current_piece['rotation'],
            'x': self.current_piece['x'],
            'y': self.current_piece['y']
        }
        
        # Drop the shadow piece until it collides
        while True:
            shadow_piece['y'] += 1
            # Check collision with the shadow piece
            shape = SHAPES[shadow_piece['shape']]
            for _ in range(shadow_piece['rotation']):
                shape = list(zip(*shape[::-1]))
                
            for y, row in enumerate(shape):
                for x, cell in enumerate(row):
                    if cell:
                        board_x = shadow_piece['x'] + x
                        board_y = shadow_piece['y'] + y
                        if (board_x < 0 or board_x >= GRID_WIDTH or 
                            board_y >= GRID_HEIGHT or 
                            (board_y >= 0 and self.grid[board_y][board_x])):
                            return shadow_piece['y'] - 1  # Return the last valid position
        return None

    def draw(self, surface):
        # Draw grid
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                if self.grid[y][x]:
                    color = self.grid[y][x]
                    rect = pygame.Rect(
                        self.playfield_rect.x + x * BLOCK_SIZE,
                        self.playfield_rect.y + y * BLOCK_SIZE,
                        BLOCK_SIZE - 1,
                        BLOCK_SIZE - 1
                    )
                    draw_block(surface, rect, color)

        # Draw shadow piece
        if self.current_piece:
            shadow_y = self.get_shadow_position()
            if shadow_y is not None:
                shape = SHAPES[self.current_piece['shape']]
                for _ in range(self.current_piece['rotation']):
                    shape = list(zip(*shape[::-1]))
                    
                for y, row in enumerate(shape):
                    for x, cell in enumerate(row):
                        if cell:
                            rect = pygame.Rect(
                                self.playfield_rect.x + (self.current_piece['x'] + x) * BLOCK_SIZE,
                                self.playfield_rect.y + (shadow_y + y) * BLOCK_SIZE,
                                BLOCK_SIZE - 1,
                                BLOCK_SIZE - 1
                            )
                            # Draw semi-transparent shadow
                            shadow_surface = pygame.Surface((BLOCK_SIZE - 1, BLOCK_SIZE - 1), pygame.SRCALPHA)
                            shadow_surface.fill((*COLORS[self.current_piece['shape']], 100))
                            surface.blit(shadow_surface, rect)
                            pygame.draw.rect(surface, (255, 255, 255), rect, 1)

        # Draw current piece
        if self.current_piece:
            shape = SHAPES[self.current_piece['shape']]
            for _ in range(self.current_piece['rotation']):
                shape = list(zip(*shape[::-1]))
                
            for y, row in enumerate(shape):
                for x, cell in enumerate(row):
                    if cell:
                        rect = pygame.Rect(
                            self.playfield_rect.x + (self.current_piece['x'] + x) * BLOCK_SIZE,
                            self.playfield_rect.y + (self.current_piece['y'] + y) * BLOCK_SIZE,
                            BLOCK_SIZE - 1,
                            BLOCK_SIZE - 1
                        )
                        draw_block(surface, rect, self.current_piece['shape'])

def draw_block(surface, rect, color, is_preview=False):
    # Create gradient effect
    gradient_height = rect.height // 2
    top_color, bottom_color = COLOR_GRADIENTS.get(color, (color, color))
    
    # Draw main block with gradient
    top_rect = pygame.Rect(rect.x, rect.y, rect.width, gradient_height)
    bottom_rect = pygame.Rect(rect.x, rect.y + gradient_height, rect.width, rect.height - gradient_height)
    
    pygame.draw.rect(surface, top_color, top_rect)
    pygame.draw.rect(surface, bottom_color, bottom_rect)
    
    # Draw border
    border_color = (255, 255, 255) if not is_preview else (200, 200, 200)
    pygame.draw.rect(surface, border_color, rect, 1)
    
    # Draw inner highlight
    highlight_rect = pygame.Rect(rect.x + 2, rect.y + 2, rect.width - 4, gradient_height - 2)
    highlight_color = (255, 255, 255, 100) if not is_preview else (200, 200, 200, 100)
    highlight_surface = pygame.Surface((highlight_rect.width, highlight_rect.height), pygame.SRCALPHA)
    pygame.draw.rect(highlight_surface, highlight_color, highlight_surface.get_rect())
    surface.blit(highlight_surface, highlight_rect)

# === Game State ===
p1 = Player(p1_playfield)
p2 = Player(p2_playfield)
paused = False
show_help = False
game_over = False

# Mock leaderboard data
leaderboard = [
    ("Alice", 1500),
    ("Bob", 1300),
    ("Ashton", p1.score),
    ("Bruce", p2.score),
    ("Eve", 800),
]

# Game over buttons
btn_main_menu = pygame.Rect(SCREEN_WIDTH // 2 - 120, SCREEN_HEIGHT - 120, 220, 40)
btn_exit_game = pygame.Rect(SCREEN_WIDTH // 2 - 120, SCREEN_HEIGHT - 60, 220, 40)

def draw_text(text, pos, font, color=WHITE, center=False):
    render = font.render(text, True, color)
    rect = render.get_rect()
    if center:
        rect.center = pos
    else:
        rect.topleft = pos
    screen.blit(render, rect)

def draw_glow_rect(rect, color, border=2):
    pygame.draw.rect(screen, color, rect, border)
    glow_surface = pygame.Surface((rect.width+20, rect.height+20), pygame.SRCALPHA)
    pygame.draw.rect(glow_surface, (*color, 80), glow_surface.get_rect(), border_radius=10)
    screen.blit(glow_surface, (rect.x - 10, rect.y - 10))

def draw_playfield():
    draw_text("Ashton", (p1_playfield.x, 50), font_large)
    draw_text("Bruce", (p2_playfield.x, 50), font_large)

    # Box sizes
    next_box_size = (100, 300)
    hold_box_size = (80, 80)
    score_box_size = (100, 50)
    combo_box_size = (100, 40)
    garbage_box_size = (100, 40)  # New box for garbage
    ui_spacing = 30

    # Shift playfields toward center to create space on both outer sides
    p1_playfield.x = 200
    p2_playfield.x = 800  

    # P1 Next Box (right of playfield), UI (left)
    p1_next_box = pygame.Rect(p1_playfield.right + ui_spacing, p1_playfield.y, *next_box_size)
    p1_hold = pygame.Rect(p1_playfield.left - ui_spacing - hold_box_size[0], p1_playfield.y, *hold_box_size)
    p1_score_box = pygame.Rect(70, p1_hold.bottom + 50, *score_box_size)
    p1_combo_box = pygame.Rect(p1_score_box.x, p1_score_box.bottom + 50, *combo_box_size)
    p1_garbage_box = pygame.Rect(p1_combo_box.x, p1_combo_box.bottom + 50, *garbage_box_size)

    # P2 Next Box (left of playfield), UI (right)
    p2_next_box = pygame.Rect(p2_playfield.left - ui_spacing - next_box_size[0], p2_playfield.y, *next_box_size)
    p2_hold = pygame.Rect(p2_playfield.right + ui_spacing, p2_playfield.y, *hold_box_size)
    p2_score_box = pygame.Rect(p2_hold.x, p2_hold.bottom + 50, *score_box_size)
    p2_combo_box = pygame.Rect(p2_score_box.x, p2_score_box.bottom + 50, *combo_box_size)
    p2_garbage_box = pygame.Rect(p2_combo_box.x, p2_combo_box.bottom + 50, *garbage_box_size)

    # Draw Playfields
    for rect in [p1_playfield, p2_playfield]:
        overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        screen.blit(overlay, rect)
        draw_glow_rect(rect, CYAN)

    # Draw UI Boxes
    for box, label, value in [
        (p1_hold, "Hold", None), (p2_hold, "Hold", None),
        (p1_score_box, "Score:", p1.score), (p2_score_box, "Score:", p2.score),
        (p1_combo_box, "Combo:", p1.combo), (p2_combo_box, "Combo:", p2.combo),
        (p1_garbage_box, "Garbage:", p1.garbage_send_buffer), (p2_garbage_box, "Garbage:", p2.garbage_send_buffer),
    ]:
        draw_text(label, (box.x, box.y - 25), font_small)
        overlay = pygame.Surface(box.size, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        screen.blit(overlay, box)
        draw_glow_rect(box, CYAN)
        if value is not None:
            draw_text(str(value), box.center, font_small, center=True)

    # Draw Next Boxes with multiple pieces
    for rect, label, player in [(p1_next_box, "Next", p1), (p2_next_box, "Next", p2)]:
        overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        screen.blit(overlay, rect)
        draw_glow_rect(rect, CYAN)
        draw_text(label, (rect.x, rect.y - 25), font_small)
        
        # Draw each next piece
        for i, piece in enumerate(player.next_pieces):
            shape = SHAPES[piece]
            piece_height = len(shape)
            piece_width = len(shape[0])
            
            # Calculate position to center the piece in its section
            section_height = rect.height // 3
            y_offset = rect.y + (section_height * i) + (section_height - piece_height * PREVIEW_BLOCK_SIZE) // 2
            x_offset = rect.x + (rect.width - piece_width * PREVIEW_BLOCK_SIZE) // 2
            
            # Draw the piece
            for y, row in enumerate(shape):
                for x, cell in enumerate(row):
                    if cell:
                        block_rect = pygame.Rect(
                            x_offset + x * PREVIEW_BLOCK_SIZE,
                            y_offset + y * PREVIEW_BLOCK_SIZE,
                            PREVIEW_BLOCK_SIZE - 1,
                            PREVIEW_BLOCK_SIZE - 1
                        )
                        draw_block(screen, block_rect, piece, is_preview=True)

    pygame.draw.rect(screen, CYAN, pause_button, 2)
    draw_text("Menu", pause_button.center, font_small, center=True)

def draw_menu():
    pygame.draw.rect(screen, (10, 10, 30, 220), menu_rect)
    draw_glow_rect(menu_rect, CYAN, 2)

    draw_text("Game Paused", (menu_rect.centerx, menu_rect.y + 20), font_large, center=True)
    draw_text("Resume (R)", (menu_rect.x + 20, menu_rect.y + 80), font_small)
    draw_text("Help (H)", (menu_rect.x + 20, menu_rect.y + 120), font_small)
    draw_text("Quit (Q)", (menu_rect.x + 20, menu_rect.y + 160), font_small)

    if show_help:
        draw_text("Controls:", (menu_rect.x + 150, menu_rect.y + 80), font_small)
        draw_text("←→↓ to move", (menu_rect.x + 150, menu_rect.y + 110), font_small)
        draw_text("Space to drop", (menu_rect.x + 150, menu_rect.y + 140), font_small)
        draw_text("C to hold", (menu_rect.x + 150, menu_rect.y + 170), font_small)

def draw_video_background():
    ret, frame = cap.read()
    if not ret:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ret, frame = cap.read()
    frame = cv2.resize(frame, (SCREEN_WIDTH, SCREEN_HEIGHT))
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    surface = pygame.surfarray.make_surface(np.flipud(np.rot90(frame)))
    screen.blit(surface, (0, 0))

    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill(OVERLAY_COLOR)
    screen.blit(overlay, (0, 0))

def draw_game_over():
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    screen.blit(overlay, (0, 0))

    winner = "Ashton Wins!" if p1.score > p2.score else "Bruce Wins!" if p2.score > p1.score else "It's a Tie!"
    draw_text("Game Over", (SCREEN_WIDTH // 2, 80), font_large, center=True)
    draw_text(winner, (SCREEN_WIDTH // 2, 130), font_large, center=True)
    draw_text("Leaderboard", (SCREEN_WIDTH // 2, 200), font_large, center=True)

    for i, (name, score) in enumerate(leaderboard[:5]):
        y_pos = 240 + i * 30
        draw_text(f"{i+1}. {name} - {score}", (SCREEN_WIDTH // 2, y_pos), font_small, center=True)

    pygame.draw.rect(screen, (30, 30, 30), btn_main_menu)
    pygame.draw.rect(screen, CYAN, btn_main_menu, 2)
    draw_text("Return to Main Menu", btn_main_menu.center, font_small, center=True)

    pygame.draw.rect(screen, (30, 30, 30), btn_exit_game)
    pygame.draw.rect(screen, CYAN, btn_exit_game, 2)
    draw_text("Exit Game", btn_exit_game.center, font_small, center=True)

# === Main Game Loop ===
running = True
last_time = pygame.time.get_ticks()

while running:
    current_time = pygame.time.get_ticks()
    dt = (current_time - last_time) / 1000.0
    last_time = current_time
    
    clock.tick(60)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if not game_over:
            if event.type == pygame.MOUSEBUTTONDOWN and pause_button.collidepoint(event.pos):
                paused = not paused
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    paused = not paused
                elif paused:
                    if event.key == pygame.K_r:
                        paused = False
                    elif event.key == pygame.K_h:
                        show_help = not show_help
                    elif event.key == pygame.K_q:
                        pygame.quit()
                        sys.exit()
                else:
                    # Player 1 controls
                    if event.key == pygame.K_LEFT:
                        p1.move_piece(-1, 0)
                    elif event.key == pygame.K_RIGHT:
                        p1.move_piece(1, 0)
                    elif event.key == pygame.K_DOWN:
                        p1.move_piece(0, 1)
                    elif event.key == pygame.K_UP:
                        p1.rotate_piece()
                    elif event.key == pygame.K_SPACE:
                        while p1.move_piece(0, 1):
                            pass
                    elif event.key == pygame.K_c:
                        p1.hold_piece()
                        
                    # Player 2 controls
                    elif event.key == pygame.K_a:
                        p2.move_piece(-1, 0)
                    elif event.key == pygame.K_d:
                        p2.move_piece(1, 0)
                    elif event.key == pygame.K_s:
                        p2.move_piece(0, 1)
                    elif event.key == pygame.K_w:
                        p2.rotate_piece()
                    elif event.key == pygame.K_f:
                        while p2.move_piece(0, 1):
                            pass
                    elif event.key == pygame.K_v:
                        p2.hold_piece()
        else:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if btn_main_menu.collidepoint(event.pos):
                    p1 = Player(p1_playfield)
                    p2 = Player(p2_playfield)
                    game_over = False
                elif btn_exit_game.collidepoint(event.pos):
                    pygame.quit()
                    sys.exit()

    if not paused and not game_over:
        p1.update(dt)
        p2.update(dt)
        
        # Send garbage between players
        if p1.garbage_send_buffer > 0:
            p2.add_garbage_lines(p1.garbage_send_buffer)
            p1.garbage_send_buffer = 0
        if p2.garbage_send_buffer > 0:
            p1.add_garbage_lines(p2.garbage_send_buffer)
            p2.garbage_send_buffer = 0
            
        game_over = p1.game_over or p2.game_over

    draw_video_background()
    
    if game_over:
        draw_game_over()
    else:
        draw_playfield()
        p1.draw(screen)
        p2.draw(screen)
        if paused:
            draw_menu()

    pygame.display.update()

cap.release()
pygame.quit()
sys.exit()
