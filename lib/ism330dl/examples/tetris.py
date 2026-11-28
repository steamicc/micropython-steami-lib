# Tetris for STeaMi — controlled via ISM330DL accelerometer
# Board screen through steami.Screen: SSD1327 128x128 OLED (greyscale) on
# V1a/V1b, round GC9A01 240x240 TFT (colour) on V1c. The layout is given in
# 128 px units and scaled with screen.u().
# Tilt left/right to move, shake to rotate, button A for hard drop,
# button B for soft rotation.

import random
from time import sleep_ms, ticks_ms

from ism330dl import ISM330DL
from machine import I2C, Pin
from steami import Screen
from steami_screen import BLACK, BLUE, DARK, GRAY, LIGHT, RED, WHITE, YELLOW

# === Display ===
screen = Screen()
screen.begin()  # allocate the frame buffer early in the program

# === IMU ===
i2c = I2C(1)
imu = ISM330DL(i2c)

# === Buttons ===
BTN_A = Pin("A_BUTTON", Pin.IN, Pin.PULL_UP)
BTN_B = Pin("B_BUTTON", Pin.IN, Pin.PULL_UP)

# === Game parameters ===
COLS = 10
ROWS = 20
CELL = screen.u(5)  # cell size: 5 px on 128 px, 9 px on 240 px
GRID_X = screen.u(25)  # grid X position (centered for the round screen)
GRID_Y = screen.u(14)  # grid Y position (centered for the round screen)
TILT_THRESH = 0.35  # tilt threshold (g)
SHAKE_THRESH = 1.8  # shake threshold (g)
MOVE_DELAY = 180  # ms between two lateral moves
SHAKE_COOLDOWN = 400  # ms between two rotations

# === Colors (RGB, shown as grey levels on the SSD1327) ===
COL_BG = BLACK
COL_BORDER = GRAY
COL_TEXT = WHITE
COL_VALUE = LIGHT
COL_GHOST = (51, 51, 51)  # grey level 3 of 15

# Piece colors, in PIECES order (I, O, T, S, Z, J, L), after an unused 0.
# On the SSD1327 they are the grey levels 12, 14, 9, 13, 8, 6 and 10.
CYAN = (85, 255, 255)
MAGENTA = (255, 85, 255)
LIGHT_GREEN = (150, 255, 150)  # GREEN on the GC9A01, a grey apart from CYAN
ORANGE = (255, 165, 0)
PIECE_COLORS = [BLACK, CYAN, YELLOW, MAGENTA, LIGHT_GREEN, RED, BLUE, ORANGE]

# === Tetris pieces (tetrominoes) ===
# Format: list of rotations, each rotation = list of (row, col)
PIECES = [
    # I
    [[(0, 0), (0, 1), (0, 2), (0, 3)], [(0, 0), (1, 0), (2, 0), (3, 0)]],
    # O
    [[(0, 0), (0, 1), (1, 0), (1, 1)]],
    # T
    [
        [(0, 1), (1, 0), (1, 1), (1, 2)],
        [(0, 0), (1, 0), (2, 0), (1, 1)],
        [(1, 0), (1, 1), (1, 2), (0, 1)],
        [(0, 1), (1, 1), (2, 1), (1, 0)],
    ],
    # S
    [[(0, 1), (0, 2), (1, 0), (1, 1)], [(0, 0), (1, 0), (1, 1), (2, 1)]],
    # Z
    [[(0, 0), (0, 1), (1, 1), (1, 2)], [(0, 1), (1, 0), (1, 1), (2, 0)]],
    # J
    [
        [(0, 0), (1, 0), (1, 1), (1, 2)],
        [(0, 0), (0, 1), (1, 0), (2, 0)],
        [(1, 0), (1, 1), (1, 2), (0, 2)],
        [(0, 1), (1, 1), (2, 0), (2, 1)],
    ],
    # L
    [
        [(0, 2), (1, 0), (1, 1), (1, 2)],
        [(0, 0), (1, 0), (2, 0), (2, 1)],
        [(1, 0), (1, 1), (1, 2), (0, 0)],
        [(0, 0), (0, 1), (1, 1), (2, 1)],
    ],
]

# === Game state ===
grid = [[None] * COLS for _ in range(ROWS)]
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

    # Clear full lines
    full = [r for r in range(ROWS) if all(grid[r])]
    for r in full:
        del grid[r]
        grid.insert(0, [None] * COLS)

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
    screen.rect(x, y, CELL - 1, CELL - 1, color, fill=True)


def draw_text(text, x, y, color):
    # x, y: top left of the first character, in real pixels
    screen.text(text, at=(x, y), color=color)


def draw_text_centered(text, y, color):
    # y in 128 px units; characters are 8 px wide on 128 and 240 px
    char_w = screen.width // screen.max_chars
    x = screen.width // 2 - (len(text) * char_w) // 2
    x = max(x, 0)
    draw_text(text, x, screen.u(y), color)


def draw_screen():
    screen.clear(COL_BG)

    # Grid border
    screen.rect(GRID_X - 1, GRID_Y - 1, COLS * CELL + 2, ROWS * CELL + 2, COL_BORDER)

    # Background grid (locked cells)
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

    # Current piece
    color = PIECE_COLORS[piece_type + 1]
    for r, c in get_cells(piece_row, piece_col, piece_rot):
        if 0 <= r < ROWS and 0 <= c < COLS:
            draw_cell(r, c, color)

    # === Right info panel (offsets in 128 px units) ===
    px = GRID_X + COLS * CELL + screen.u(4)
    py = GRID_Y

    # Score
    draw_text("SCR", px, py, COL_TEXT)
    s = str(score)
    draw_text(s[:5], px, py + screen.u(10), COL_VALUE)

    # Level
    draw_text("LVL", px, py + screen.u(25), COL_TEXT)
    draw_text(str(level), px, py + screen.u(35), COL_VALUE)

    # Lines
    draw_text("LNS", px, py + screen.u(50), COL_TEXT)
    draw_text(str(lines_cleared), px, py + screen.u(60), COL_VALUE)

    # Next piece
    draw_text("NXT", px, py + screen.u(75), COL_TEXT)
    ncells = get_cells(0, 0, 0, next_type)
    for r, c in ncells:
        nx = px + c * (CELL - 1)
        ny = py + screen.u(85) + r * (CELL - 1)
        screen.rect(nx, ny, CELL - 2, CELL - 2, PIECE_COLORS[next_type + 1], fill=True)

    screen.show()


def draw_game_over():
    screen.clear()
    draw_text_centered("GAME", 45, WHITE)
    draw_text_centered("OVER", 57, WHITE)
    draw_text_centered("SCR:" + str(score), 75, LIGHT)
    draw_text_centered("B=restart", 95, DARK)
    screen.show()


def draw_start():
    screen.clear()
    draw_text_centered("TETRIS", 22, WHITE)
    draw_text_centered("Tilt=move", 45, LIGHT)
    draw_text_centered("Shake=rot", 57, LIGHT)
    draw_text_centered("B=rot", 69, LIGHT)
    draw_text_centered("A=drop", 81, LIGHT)
    draw_text_centered("A to start", 102, DARK)
    screen.show()


def reset_game():
    global grid, score, level, lines_cleared, game_over
    global last_fall, last_move, last_shake, fall_interval, next_type
    grid = [[None] * COLS for _ in range(ROWS)]
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


# === Start screen ===
draw_start()
while BTN_A.value() == 1:
    sleep_ms(50)
sleep_ms(200)

# === Init game ===
reset_game()

# === Main loop ===
while True:
    now = ticks_ms()

    if game_over:
        draw_game_over()
        while BTN_B.value() == 1:
            sleep_ms(50)
        sleep_ms(200)
        reset_game()
        continue

    # IMU read
    ax, ay, az = imu.acceleration_g()

    # Shake -> rotation
    magnitude = (ax * ax + ay * ay + az * az) ** 0.5
    if magnitude > SHAKE_THRESH and (now - last_shake) > SHAKE_COOLDOWN:
        new_rot = (piece_rot + 1) % len(PIECES[piece_type])
        if valid_pos(piece_row, piece_col, new_rot):
            piece_rot = new_rot
        last_shake = now

    # Tilt -> lateral movement
    if (now - last_move) > MOVE_DELAY:
        if ay > TILT_THRESH:
            if valid_pos(piece_row, piece_col + 1, piece_rot):
                piece_col += 1
            last_move = now
        elif ay < -TILT_THRESH:
            if valid_pos(piece_row, piece_col - 1, piece_rot):
                piece_col -= 1
            last_move = now

    # Button A -> hard drop
    if BTN_A.value() == 0:
        while valid_pos(piece_row + 1, piece_col, piece_rot):
            piece_row += 1
        lock_piece()
        new_piece()
        last_fall = now
        sleep_ms(150)

    # Button B -> soft rotation
    if BTN_B.value() == 0 and (now - last_shake) > SHAKE_COOLDOWN:
        new_rot = (piece_rot + 1) % len(PIECES[piece_type])
        if valid_pos(piece_row, piece_col, new_rot):
            piece_rot = new_rot
        last_shake = now
        sleep_ms(150)

    # Automatic fall
    if (now - last_fall) > fall_interval:
        if valid_pos(piece_row + 1, piece_col, piece_rot):
            piece_row += 1
        else:
            lock_piece()
            new_piece()
        last_fall = now

    draw_screen()
    sleep_ms(30)
