import random
import pygame
from collections import deque

# ─── MAZE CONFIG ────────────────────────────────────────────────────────────
ROWS, COLS = 50, 50      # ← Change these to whatever you like
CELL_SIZE = 60           # ← Only used for initial carve spacing; drawing is dynamic
maze = [[0] * COLS for _ in range(ROWS)]
goal_pos = (1, 1)

CARVE_DIRS = [(2, 0), (-2, 0), (0, 2), (0, -2)]


def generate_maze():
    """Carve a perfect maze interior and pick the farthest non-corner cell as goal."""
    global maze, goal_pos
    # reset to walls
    maze[:] = [[0] * COLS for _ in range(ROWS)]
    visited = [[False] * COLS for _ in range(ROWS)]

    def carve(r, c):
        visited[r][c] = True
        maze[r][c] = 1
        dirs = CARVE_DIRS[:]
        random.shuffle(dirs)
        for dr, dc in dirs:
            nr, nc = r + dr, c + dc
            if 1 <= nr < ROWS - 1 and 1 <= nc < COLS - 1 and not visited[nr][nc]:
                maze[r + dr // 2][c + dc // 2] = 1
                carve(nr, nc)

    carve(1, 1)

    # enforce outer walls
    for x in range(COLS):
        maze[0][x] = maze[ROWS - 1][x] = 0
    for y in range(ROWS):
        maze[y][0] = maze[y][COLS - 1] = 0

    # choose goal
    goal_pos = _find_goal((1, 1))


def _find_goal(start):
    """BFS to find farthest reachable non-corner path cell."""
    corners = {(0, 0), (0, COLS - 1), (ROWS - 1, 0), (ROWS - 1, COLS - 1)}
    visited = [[False] * COLS for _ in range(ROWS)]
    queue = deque([(start[0], start[1], 0)])
    visited[start[0]][start[1]] = True

    farthest, maxd = start, -1
    while queue:
        r, c, dist = queue.popleft()
        if maze[r][c] == 1 and (r, c) != start and (r, c) not in corners and dist > maxd:
            farthest, maxd = (r, c), dist
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < ROWS and 0 <= nc < COLS and not visited[nr][nc] and maze[nr][nc] == 1:
                visited[nr][nc] = True
                queue.append((nr, nc, dist + 1))
    return farthest


def draw_maze(win, cell_size, off_x=0, off_y=0):
    """Draw the maze grid with dynamic cell_size and offsets."""
    for y in range(ROWS):
        for x in range(COLS):
            color = (255, 255, 255) if maze[y][x] else (0, 0, 0)
            rect = pygame.Rect(
                off_x + x * cell_size,
                off_y + y * cell_size,
                cell_size,
                cell_size
            )
            pygame.draw.rect(win, color, rect.inflate(-1, -1))
    border = pygame.Rect(off_x, off_y, COLS * cell_size, ROWS * cell_size)
    pygame.draw.rect(win, (0, 0, 0), border, width=1)


def draw_goal(win, cell_size, off_x=0, off_y=0):
    """Draw the goal as a green circle in its cell."""
    gr, gc = goal_pos
    cx = off_x + gc * cell_size + cell_size // 2
    cy = off_y + gr * cell_size + cell_size // 2
    radius = cell_size // 3
    pygame.draw.circle(win, (0, 255, 0), (cx, cy), radius)
