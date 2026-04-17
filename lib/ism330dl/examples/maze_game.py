"""Maze game example using ISM330DL accelerometer and SSD1327 OLED.

Navigate through a randomly generated maze by tilting the STeaMi board.
Your score is computed at the end based on how close you were to the
optimal path, calculated with Dijkstra's algorithm.

Hardware:
    - ISM330DL accelerometer (tilt input)
    - SSD1327 128x128 OLED display (round)

Controls:
    - Tilt the board forward  → move UP
    - Tilt the board backward → move DOWN
    - Tilt the board left     → move LEFT
    - Tilt the board right    → move RIGHT
"""

import random
from time import sleep_ms

import micropython
import ssd1327
from ism330dl import ISM330DL
from machine import I2C, SPI, Pin
from steami_screen import GRAY, LIGHT, WHITE, Screen, SSD1327Display

# =============================================================================
# === Display setup ===========================================================
# =============================================================================

spi = SPI(1)
dc = Pin("DATA_COMMAND_DISPLAY")
res = Pin("RST_DISPLAY")
cs = Pin("CS_DISPLAY")
display = SSD1327Display(ssd1327.WS_OLED_128X128_SPI(spi, dc, res, cs))
screen = Screen(display)

# =============================================================================
# === Accelerometer setup =====================================================
# =============================================================================

i2c = I2C(1)
imu = ISM330DL(i2c)

# =============================================================================
# === Game constants ===========================================================
# =============================================================================

MAZE_W = 11  # Must be odd
MAZE_H = 11  # Must be odd
START_ROW = 1
START_COL = 1
GOAL_ROW = MAZE_H - 2
GOAL_COL = MAZE_W - 2
MOVE_DELAY_MS = 200  # Delay between moves in milliseconds
TILT_THRESHOLD = 0.3  # Minimum tilt in g to trigger a move

# Cell types
WALL = 0
PATH = 1

# Directions: (row_delta, col_delta)
UP = (-1, 0)
DOWN = (1, 0)
LEFT = (0, -1)
RIGHT = (0, 1)
NONE = (0, 0)

# Display safe zone for round screen
SAFE_X = 19
SAFE_Y = 19
SAFE_SIZE = 90
CELL_SIZE = SAFE_SIZE // MAZE_W  # 8px per cell

# =============================================================================
# === Maze generation (Recursive Backtracker / DFS) ===========================
# =============================================================================


def generate_maze(width, height):
    """Generate a perfect maze using Recursive Backtracker algorithm.

    Returns a 2D list of WALL/PATH values.
    Width and height must be odd numbers.
    """
    maze = [[WALL] * width for _ in range(height)]

    def carve(row, col):
        maze[row][col] = PATH
        dirs = [(-2, 0), (2, 0), (0, -2), (0, 2)]
        # Shuffle directions
        for i in range(len(dirs) - 1, 0, -1):
            j = random.randint(0, i)
            dirs[i], dirs[j] = dirs[j], dirs[i]
        for dr, dc in dirs:
            nr, nc = row + dr, col + dc
            if 0 <= nr < height and 0 <= nc < width and maze[nr][nc] == WALL:
                maze[row + dr // 2][col + dc // 2] = PATH
                carve(nr, nc)

    carve(1, 1)
    return maze


# =============================================================================
# === Dijkstra shortest path ==================================================
# =============================================================================


def dijkstra(maze, start_row, start_col, goal_row, goal_col):
    """Find the shortest path length from start to goal in the maze.

    Returns the number of steps in the optimal path, or -1 if not found.
    """
    height = len(maze)
    width = len(maze[0])
    INF = 999999
    dist = [[INF] * width for _ in range(height)]
    dist[start_row][start_col] = 0
    queue = [(0, start_row, start_col)]

    while queue:
        # Find minimum distance node
        min_idx = 0
        for i in range(1, len(queue)):
            if queue[i][0] < queue[min_idx][0]:
                min_idx = i
        cost, row, col = queue.pop(min_idx)

        if row == goal_row and col == goal_col:
            return cost
        if cost > dist[row][col]:
            continue

        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = row + dr, col + dc
            if 0 <= nr < height and 0 <= nc < width and maze[nr][nc] == PATH:
                new_cost = cost + 1
                if new_cost < dist[nr][nc]:
                    dist[nr][nc] = new_cost
                    queue.append((new_cost, nr, nc))

    return -1


def compute_score(player_steps, optimal_steps, max_score=1000):
    """Compute player score based on path efficiency.

    Returns a score between 0 and max_score.
    Perfect path = max_score. Score decreases as player takes more steps.
    """
    if optimal_steps <= 0:
        return 0
    if player_steps <= optimal_steps:
        return max_score
    return max(0, int(max_score * optimal_steps / player_steps))


# =============================================================================
# === Accelerometer input =====================================================
# =============================================================================


def read_direction():
    ax, ay, _ = imu.acceleration_g()
    ax = -ax  # Invert forward/backward axis
    abs_x = ax if ax >= 0 else -ax
    abs_y = ay if ay >= 0 else -ay

    if abs_x < TILT_THRESHOLD and abs_y < TILT_THRESHOLD:
        return NONE
    if abs_x >= abs_y:
        return DOWN if ax > 0 else UP
    return RIGHT if ay > 0 else LEFT


# =============================================================================
# === Display helpers =========================================================
# =============================================================================


def cell_to_pixel(row, col):
    """Convert maze cell coordinates to screen pixel coordinates."""
    return SAFE_X + col * CELL_SIZE, SAFE_Y + row * CELL_SIZE


@micropython.native
def draw_maze(maze):
    """Draw all maze walls as filled rectangles."""
    for row in range(len(maze)):
        for col in range(len(maze[0])):
            x, y = cell_to_pixel(row, col)
            if maze[row][col] == WALL:
                screen.rect(x, y, CELL_SIZE, CELL_SIZE, LIGHT, fill=True)


def draw_player(row, col):
    """Draw player as a bright filled circle."""
    x, y = cell_to_pixel(row, col)
    cx = x + CELL_SIZE // 2
    cy = y + CELL_SIZE // 2
    screen.circle(cx, cy, CELL_SIZE // 2 - 1, WHITE, fill=True)


def draw_goal(row, col):
    """Draw goal marker as a gray filled circle."""
    x, y = cell_to_pixel(row, col)
    cx = x + CELL_SIZE // 2
    cy = y + CELL_SIZE // 2
    screen.circle(cx, cy, CELL_SIZE // 2 - 1, GRAY, fill=True)


def render(maze, player_row, player_col, steps, optimal):
    """Full frame render: maze, goal, player and HUD."""
    screen.clear()
    draw_maze(maze)
    draw_goal(GOAL_ROW, GOAL_COL)
    draw_player(player_row, player_col)
    screen.title(f"S:{steps} B:{optimal}")
    screen.show()


# =============================================================================
# === Screens =================================================================
# =============================================================================


def show_start_screen():
    """Display start screen."""
    screen.clear()
    screen.title("MAZE GAME")
    screen.face("happy")
    screen.subtitle("Tilt to play!")
    screen.show()
    sleep_ms(2000)


def show_win_screen(steps, optimal):
    """Display win screen with score."""
    score = compute_score(steps, optimal)
    screen.clear()
    screen.title("YOU WIN!")
    screen.value(str(score), unit="pts")
    screen.subtitle(f"Steps: {steps}", f"Best:  {optimal}")
    screen.show()
    sleep_ms(5000)


# =============================================================================
# === Main game loop ==========================================================
# =============================================================================


def run_game():
    """Generate a new maze and run one full game round.

    Returns when the player reaches the goal.
    """
    maze = generate_maze(MAZE_W, MAZE_H)
    optimal = dijkstra(maze, START_ROW, START_COL, GOAL_ROW, GOAL_COL)

    player_row = START_ROW
    player_col = START_COL
    steps = 0

    show_start_screen()

    while True:
        render(maze, player_row, player_col, steps, optimal)

        direction = read_direction()
        if direction != NONE:
            dr, dc = direction
            nr = player_row + dr
            nc = player_col + dc
            if 0 <= nr < MAZE_H and 0 <= nc < MAZE_W and maze[nr][nc] == PATH:
                player_row = nr
                player_col = nc
                steps += 1

        if player_row == GOAL_ROW and player_col == GOAL_COL:
            show_win_screen(steps, optimal)
            return

        sleep_ms(MOVE_DELAY_MS)


# =============================================================================
# === Entry point =============================================================
# =============================================================================

print("Maze game starting...")

try:
    while True:
        run_game()
except KeyboardInterrupt:
    print("\nMaze game stopped.")
finally:
    screen.clear()
    screen.show()
    imu.power_off()
