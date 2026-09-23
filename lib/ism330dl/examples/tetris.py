# Tetris for STeaMi — controlled via ISM330DL accelerometer
# SSD1327 128x128 OLED, 4-bit greyscale
# Tilt left/right to move, shake to rotate, button A for hard drop,
# button B for soft rotation.

import random
from time import sleep_ms, ticks_ms

import ssd1327
from ism330dl import ISM330DL
from machine import I2C, SPI, Pin

# === Display ===
spi = SPI(1)
dc = Pin("DATA_COMMAND_DISPLAY")
res = Pin("RST_DISPLAY")
cs = Pin("CS_DISPLAY")
display = ssd1327.WS_OLED_128X128_SPI(spi, dc, res, cs)

# === IMU ===
i2c = I2C(1)
imu = ISM330DL(i2c)

# === Buttons ===
BTN_A = Pin("A_BUTTON", Pin.IN, Pin.PULL_UP)
BTN_B = Pin("B_BUTTON", Pin.IN, Pin.PULL_UP)

# === Game parameters ===
COLS = 10
ROWS = 20
CELL = 5  # cell size in pixels
GRID_X = 25  # grid X position (centered for round OLED)
GRID_Y = 14  # grid Y position (centered for round OLED)
TILT_THRESH = 0.35  # tilt threshold (g)
SHAKE_THRESH = 1.8  # shake threshold (g)
MOVE_DELAY = 180  # ms between two lateral moves
SHAKE_COOLDOWN = 400  # ms between two rotations

# === Colors (0-15) ===
COL_BG = 0
COL_BORDER = 8
COL_TEXT = 15
COL_GHOST = 3

# Piece colors (1-15)
PIECE_COLORS = [0, 12, 14, 11, 13, 10, 9, 15]

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

    # Clear full lines
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


def draw_text_centered(text, y, color):
    # MicroPython framebuf font is 8 px wide per char
    x = 64 - (len(text) * 8) // 2
    x = max(x, 0)
    display.text(text, x, y, color)


def draw_screen():
    display.fill(COL_BG)

    # Grid border
    draw_rect_outline(
        GRID_X - 1, GRID_Y - 1, COLS * CELL + 1, ROWS * CELL + 1, COL_BORDER
    )

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

    # === Right info panel ===
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
    draw_text_centered("GAME", 45, 15)
    draw_text_centered("OVER", 57, 15)
    draw_text_centered("SCR:" + str(score), 75, 10)
    draw_text_centered("B=restart", 95, 7)
    display.show()


def draw_start():
    display.fill(0)
    draw_text_centered("TETRIS", 22, 15)
    draw_text_centered("Tilt=move", 45, 10)
    draw_text_centered("Shake=rot", 57, 10)
    draw_text_centered("B=rot", 69, 10)
    draw_text_centered("A=drop", 81, 10)
    draw_text_centered("A to start", 102, 7)
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
