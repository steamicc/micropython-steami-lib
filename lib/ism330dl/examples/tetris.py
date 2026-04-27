# Tetris pour STeaMi — contrôle par accéléromètre ISM330DL
# Ecran SSD1327 128x128, 4-bit greyscale
# Incliner gauche/droite pour déplacer, secouer pour tourner
# Bouton A pour hard drop
 
from machine import I2C, SPI, Pin
from time import ticks_ms, sleep_ms
import ssd1327
from ism330dl import ISM330DL
import random
 
# === Ecran ===
spi = SPI(1)
dc = Pin("DATA_COMMAND_DISPLAY")
res = Pin("RST_DISPLAY")
cs = Pin("CS_DISPLAY")
display = ssd1327.WS_OLED_128X128_SPI(spi, dc, res, cs)
 
# === IMU ===
i2c = I2C(1)
imu = ISM330DL(i2c)
 
# === Boutons ===
BTN_A = Pin("A_BUTTON", Pin.IN, Pin.PULL_UP)
BTN_B = Pin("B_BUTTON", Pin.IN, Pin.PULL_UP)
 
# === Parametres du jeu ===
COLS = 10
ROWS = 20
CELL = 5          # taille d'une cellule en pixels
GRID_X = 14      # position X de la grille
GRID_Y = 4       # position Y de la grille
TILT_THRESH = 0.35   # seuil inclinaison (g)
SHAKE_THRESH = 1.8   # seuil secousse (g)
MOVE_DELAY = 180     # ms entre deux deplacements lateraux
SHAKE_COOLDOWN = 400 # ms entre deux rotations
 
# === Couleurs (0-15) ===
COL_BG = 0
COL_GRID = 1
COL_BORDER = 8
COL_TEXT = 15
COL_GHOST = 3
 
# Couleurs des pieces (1-15)
PIECE_COLORS = [0, 12, 14, 11, 13, 10, 9, 15]
 
# === Pieces Tetris (tetrominoes) ===
# Format : liste de rotations, chaque rotation = liste de (row, col)
PIECES = [
    # I
    [[(0,0),(0,1),(0,2),(0,3)],
     [(0,0),(1,0),(2,0),(3,0)]],
    # O
    [[(0,0),(0,1),(1,0),(1,1)]],
    # T
    [[(0,1),(1,0),(1,1),(1,2)],
     [(0,0),(1,0),(2,0),(1,1)],  # corrigé
     [(1,0),(1,1),(1,2),(0,1)],
     [(0,1),(1,1),(2,1),(1,0)]],
    # S
    [[(0,1),(0,2),(1,0),(1,1)],
     [(0,0),(1,0),(1,1),(2,1)]],
    # Z
    [[(0,0),(0,1),(1,1),(1,2)],
     [(0,1),(1,0),(1,1),(2,0)]],
    # J
    [[(0,0),(1,0),(1,1),(1,2)],
     [(0,0),(0,1),(1,0),(2,0)],
     [(1,0),(1,1),(1,2),(0,2)],
     [(0,1),(1,1),(2,0),(2,1)]],
    # L
    [[(0,2),(1,0),(1,1),(1,2)],
     [(0,0),(1,0),(2,0),(2,1)],
     [(1,0),(1,1),(1,2),(0,0)],
     [(0,0),(0,1),(1,1),(2,1)]],
]
 
# === Etat du jeu ===
grid = [[0] * COLS for _ in range(ROWS)]
score = 0
level = 1
lines_cleared = 0
game_over = False
 
piece_type = 0
piece_rot = 0
piece_row = 0
piece_col = 0
next_type = 0
 
last_fall = 0
last_move = 0
last_shake = 0
fall_interval = 600
 
def new_piece():
    global piece_type, piece_rot, piece_row, piece_col, next_type, game_over
    piece_type = next_type
    next_type = random.randint(0, len(PIECES) - 1)
    piece_rot = 0
    piece_row = 0
    piece_col = COLS // 2 - 2
    if not valid_pos(piece_row, piece_col, piece_rot):
        game_over = True
 
def get_cells(row, col, rot, ptype=None):
    if ptype is None:
        ptype = piece_type
    return [(row + r, col + c) for r, c in PIECES[ptype][rot % len(PIECES[ptype])]]
 
def valid_pos(row, col, rot, ptype=None):
    for r, c in get_cells(row, col, rot, ptype):
        if r < 0 or r >= ROWS or c < 0 or c >= COLS:
            return False
        if grid[r][c]:
            return False
    return True
 
def lock_piece():
    global score, lines_cleared, level, fall_interval
    color = PIECE_COLORS[piece_type + 1]
    for r, c in get_cells(piece_row, piece_col, piece_rot):
        if 0 <= r < ROWS and 0 <= c < COLS:
            grid[r][c] = color
 
    # Effacer les lignes completes
    full = [r for r in range(ROWS) if all(grid[r])]
    for r in full:
        del grid[r]
        grid.insert(0, [0] * COLS)
 
    n = len(full)
    lines_cleared += n
    score += [0, 100, 300, 500, 800][n] * level
    level = lines_cleared // 10 + 1
    fall_interval = max(100, 600 - (level - 1) * 50)
 
def ghost_row():
    r = piece_row
    while valid_pos(r + 1, piece_col, piece_rot):
        r += 1
    return r
 
def draw_cell(row, col, color):
    x = GRID_X + col * CELL
    y = GRID_Y + row * CELL
    for dy in range(CELL - 1):
        for dx in range(CELL - 1):
            display.pixel(x + dx, y + dy, color)
 
def draw_hline(x, y, w, color):
    for i in range(w):
        display.pixel(x + i, y, color)
 
def draw_vline(x, y, h, color):
    for i in range(h):
        display.pixel(x, y + i, color)
 
def draw_rect_outline(x, y, w, h, color):
    draw_hline(x, y, w, color)
    draw_hline(x, y + h, w, color)
    draw_vline(x, y, h, color)
    draw_vline(x + w, y, h, color)
 
def draw_screen():
    display.fill(COL_BG)
 
    # Bordure grille
    draw_rect_outline(GRID_X - 1, GRID_Y - 1,
                      COLS * CELL + 1, ROWS * CELL + 1, COL_BORDER)
 
    # Grille de fond
    for r in range(ROWS):
        for c in range(COLS):
            if grid[r][c]:
                draw_cell(r, c, grid[r][c])
 
    # Ghost piece
    gr = ghost_row()
    if gr != piece_row:
        for r, c in get_cells(gr, piece_col, piece_rot):
            if 0 <= r < ROWS and 0 <= c < COLS:
                draw_cell(r, c, COL_GHOST)
 
    # Piece courante
    color = PIECE_COLORS[piece_type + 1]
    for r, c in get_cells(piece_row, piece_col, piece_rot):
        if 0 <= r < ROWS and 0 <= c < COLS:
            draw_cell(r, c, color)
 
    # === Panneau droite ===
    px = GRID_X + COLS * CELL + 4
    py = GRID_Y
 
    # Score
    display.text("SCR", px, py, COL_TEXT)
    s = str(score)
    display.text(s[:5], px, py + 10, 14)
 
    # Level
    display.text("LVL", px, py + 25, COL_TEXT)
    display.text(str(level), px, py + 35, 14)
 
    # Lines
    display.text("LNS", px, py + 50, COL_TEXT)
    display.text(str(lines_cleared), px, py + 60, 14)
 
    # Next piece
    display.text("NXT", px, py + 75, COL_TEXT)
    ncells = get_cells(0, 0, 0, next_type)
    for r, c in ncells:
        nx = px + c * (CELL - 1)
        ny = py + 85 + r * (CELL - 1)
        for dy in range(CELL - 2):
            for dx in range(CELL - 2):
                display.pixel(nx + dx, ny + dy, PIECE_COLORS[next_type + 1])
 
    display.show()
 
def draw_game_over():
    display.fill(0)
    display.text("GAME", 35, 45, 15)
    display.text("OVER", 35, 57, 15)
    display.text(f"SCR:{score}", 20, 75, 10)
    display.text("B=restart", 15, 95, 7)
    display.show()
 
def draw_start():
    display.fill(0)
    display.text("TETRIS", 28, 30, 15)
    display.text("Tilt=move", 15, 55, 10)
    display.text("Shake=rot", 15, 67, 10)
    display.text("A=drop", 25, 79, 10)
    display.text("A to start", 14, 100, 7)
    display.show()
 
def reset_game():
    global grid, score, level, lines_cleared, game_over
    global last_fall, last_move, last_shake, fall_interval, next_type
    grid = [[0] * COLS for _ in range(ROWS)]
    score = 0
    level = 1
    lines_cleared = 0
    game_over = False
    fall_interval = 600
    next_type = random.randint(0, len(PIECES) - 1)
    new_piece()
    last_fall = ticks_ms()
    last_move = ticks_ms()
    last_shake = ticks_ms()
 
# === Ecran de démarrage ===
draw_start()
while BTN_A.value() == 1:
    sleep_ms(50)
sleep_ms(200)
 
# === Init jeu ===
reset_game()
 
# === Boucle principale ===
while True:
    now = ticks_ms()
 
    if game_over:
        draw_game_over()
        while BTN_B.value() == 1:
            sleep_ms(50)
        sleep_ms(200)
        reset_game()
        continue
 
    # Lecture IMU
    ax, ay, az = imu.acceleration_g()
 
    # Secousse → rotation
    magnitude = (ax*ax + ay*ay + az*az) ** 0.5
    if magnitude > SHAKE_THRESH and (now - last_shake) > SHAKE_COOLDOWN:
        new_rot = (piece_rot + 1) % len(PIECES[piece_type])
        if valid_pos(piece_row, piece_col, new_rot):
            piece_rot = new_rot
        last_shake = now
 
    # Inclinaison → deplacement lateral
    if (now - last_move) > MOVE_DELAY:
        if ay > TILT_THRESH:
            if valid_pos(piece_row, piece_col + 1, piece_rot):
                piece_col += 1
            last_move = now
        elif ay < -TILT_THRESH:
            if valid_pos(piece_row, piece_col - 1, piece_rot):
                piece_col -= 1
            last_move = now
 
    # Bouton A → hard drop
    if BTN_A.value() == 0:
        while valid_pos(piece_row + 1, piece_col, piece_rot):
            piece_row += 1
        lock_piece()
        new_piece()
        last_fall = now
        sleep_ms(150)
 
    # Bouton B → rotation douce
    if BTN_B.value() == 0 and (now - last_shake) > SHAKE_COOLDOWN:
        new_rot = (piece_rot + 1) % len(PIECES[piece_type])
        if valid_pos(piece_row, piece_col, new_rot):
            piece_rot = new_rot
        last_shake = now
        sleep_ms(150)
 
    # Chute automatique
    if (now - last_fall) > fall_interval:
        if valid_pos(piece_row + 1, piece_col, piece_rot):
            piece_row += 1
        else:
            lock_piece()
            new_piece()
        last_fall = now
 
    draw_screen()
    sleep_ms(30)
 
