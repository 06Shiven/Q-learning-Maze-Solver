import pygame
import sys
import maze
from maze import draw_maze, draw_goal, generate_maze, ROWS, COLS
from agent import Agent

# ─── SETTINGS ───────────────────────────────────────────────────────────────
FPS_CAP       = 60
UI_H          = 160
FIXED_GRID_PX = 11 * maze.CELL_SIZE   # 11×60 = 660px
STAT_W        = 250                   # side-panel width

# dynamic cell size so 660px splits into COLS columns
CELL_SIZE     = FIXED_GRID_PX // COLS
MAZE_PIXW     = FIXED_GRID_PX
MAZE_PIXH     = CELL_SIZE * ROWS
WIDTH, HEIGHT = MAZE_PIXW + STAT_W, FIXED_GRID_PX + UI_H

# center offsets
OFF_X = (FIXED_GRID_PX - MAZE_PIXW) // 2
OFF_Y = (FIXED_GRID_PX - MAZE_PIXH) // 2

# ─── PYGAME INIT ────────────────────────────────────────────────────────────
pygame.init()
win         = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Q-learning Maze Solver")
clock       = pygame.time.Clock()
font        = pygame.font.SysFont(None, 24)
start_ticks = pygame.time.get_ticks()

# ─── UI BUTTONS ──────────────────────────────────────────────────────────────
BTN_W, BTN_H, GAP = 60, 25, 8
btns = {k: pygame.Rect(0, 0, BTN_W, BTN_H)
        for k in ['dec50','dec10','dec5','refresh','pause','inc5','inc10','inc50']}

# ─── STATE ───────────────────────────────────────────────────────────────────
colors       = [(80,  0,  0), (0,  80,  0), (0,   0,  80)]
base_speed   = 60
paused       = False
show_heatmap = False
agents       = []
last_time    = {k: 0 for k in btns}

def create_agents():
    return [Agent(colors[i]) for i in range(3)]


# ─── HEATMAP ─────────────────────────────────────────────────────────────────
def draw_heatmap(surface):
    # Prune dead-ends (same as before)
    cells = [(r, c) for r in range(ROWS) for c in range(COLS) if maze.maze[r][c] == 1]
    alive = set(cells)
    start, goal = (1,1), maze.goal_pos

    def nbrs(cell):
        r, c = cell
        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
            nb = (r+dr, c+dc)
            if nb in alive:
                yield nb

    leaves = [c for c in alive if c not in (start,goal) and sum(1 for _ in nbrs(c))<=1]
    while leaves:
        next_leaves = []
        for leaf in leaves:
            alive.discard(leaf)
        for leaf in leaves:
            for nb in nbrs(leaf):
                if nb not in (start,goal) and sum(1 for _ in nbrs(nb))<=1:
                    next_leaves.append(nb)
        leaves = next_leaves

    dead_branch = set(cells) - alive

    # Build Q-value map
    qmap, max_v = [], 0.0
    for r in range(ROWS):
        row=[]
        for c in range(COLS):
            if (r,c) in dead_branch:
                mv = 0.0
            elif maze.maze[r][c] == 1:
                vals = [max(a.Q[(r,c)].values()) for a in agents]
                mv = sum(vals)/len(vals)
            else:
                mv = 0.0
            row.append(mv)
            max_v = max(max_v, mv)
        qmap.append(row)

    # **Show every positive Q-value**, not just those above a threshold**
    if max_v > 0:
        overlay = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
        for r in range(ROWS):
            for c in range(COLS):
                v = qmap[r][c]
                if v > 0:
                    alpha = int(200 * (v / max_v))
                    overlay.fill((255, 0, 0, alpha))
                    surface.blit(overlay,
                                 (OFF_X + c*CELL_SIZE, OFF_Y + r*CELL_SIZE))


# ─── DRAW BOTTOM UI ──────────────────────────────────────────────────────────
def draw_bottom_ui():
    pygame.draw.rect(win, (30,30,30), pygame.Rect(0, FIXED_GRID_PX, WIDTH, UI_H))
    win.blit(font.render(f"Speed: {base_speed}", True, (255,255,255)),
             (10, FIXED_GRID_PX + 10))

    hm = "ON" if show_heatmap else "OFF"
    win.blit(font.render(f"Heatmap (H): {hm}", True, (255,255,255)),
             (10, FIXED_GRID_PX + 60))

    # Buttons
    y      = FIXED_GRID_PX + 90
    keys   = ['dec50','dec10','dec5','refresh','pause','inc5','inc10','inc50']
    labels = ['−50','−10','−5','Refresh',
              'Pause' if not paused else 'Play','+5','+10','+50']
    bcols  = [(120,0,0),(150,0,0),(180,0,0),(0,120,200),
              (200,200,0),(0,180,0),(0,150,0),(0,120,0)]
    total_w = len(keys)*BTN_W + (len(keys)-1)*GAP
    start_x = (WIDTH - STAT_W - total_w)//2
    for idx, key in enumerate(keys):
        btn = btns[key]
        btn.x = start_x + idx*(BTN_W+GAP)
        btn.y = y
        pygame.draw.rect(win, bcols[idx], btn, border_radius=5)
        lbl = font.render(labels[idx], True,
                          (0,0,0) if key=='pause' else (255,255,255))
        win.blit(lbl, (
            btn.x + (BTN_W - lbl.get_width())//2,
            btn.y + (BTN_H - lbl.get_height())//2
        ))


# ─── SIDE PANEL ─────────────────────────────────────────────────────────────
def draw_side_panel():
    panel_x = MAZE_PIXW
    pygame.draw.rect(win, (25,25,25), (panel_x, 0, STAT_W, HEIGHT))
    y, lh = 10, 24

    # Global stats
    elapsed_s = (pygame.time.get_ticks() - start_ticks) / 1000
    fps       = clock.get_fps()
    total_ep  = sum(ag.wins for ag in agents)
    items = [
        f"Maze Size: {ROWS}×{COLS}",
        f"Cell Size: {CELL_SIZE}px",
        f"Epsilon: {agents[0].epsilon:.2f}",
        f"Elapsed: {elapsed_s:.1f}s",
        f"FPS: {fps:.1f}",
        f"Episodes: {total_ep}",
    ]
    for it in items:
        win.blit(font.render(it, True, (200,200,200)), (panel_x+10, y))
        y += lh
    y += lh//2

    # Per-Agent stats, in that agent’s color
    for i, ag in enumerate(agents, start=1):
        color = ag.color
        wins  = ag.wins
        best  = ag.best_len if ag.best_len < float('inf') else 0
        avg   = (ag.total_steps/ag.wins) if ag.wins>0 else 0
        cur   = ag.steps

        win.blit(font.render(f"Agent {i}:", True, color), (panel_x+10, y))
        y += lh
        for label, val in [("Wins", wins), ("Best", best),
                           ("Avg", f"{avg:.1f}"), ("Cur", cur)]:
            txt = font.render(f"  {label}: {val}", True, color)
            win.blit(txt, (panel_x+10, y))
            y += lh
        y += lh//2


# ─── CONTROLS & MAIN LOOP ─────────────────────────────────────────────────────
def refresh_all():
    generate_maze()
    global agents
    agents = create_agents()

def main():
    global base_speed, paused, agents, last_time, show_heatmap

    generate_maze()
    agents = create_agents()

    while True:
        now    = pygame.time.get_ticks()
        dt     = clock.tick(FPS_CAP)
        sim_dt = dt * (base_speed/60)
        win.fill((0,0,0))

        # Events
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_h:
                show_heatmap = not show_heatmap
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                mx, my = e.pos
                # speed buttons
                for key, delta in [('dec50',-50),('dec10',-10),('dec5',-5),
                                   ('inc5',5),('inc10',10),('inc50',50)]:
                    if btns[key].collidepoint(mx,my):
                        base_speed = max(1, min(1000, base_speed + delta))
                        last_time[key] = now
                if btns['refresh'].collidepoint(mx,my):
                    refresh_all()
                elif btns['pause'].collidepoint(mx,my):
                    paused = not paused

        # Hold-to-adjust
        if pygame.mouse.get_pressed()[0]:
            mx, my = pygame.mouse.get_pos()
            for key, delta in [('dec50',-50),('dec10',-10),('dec5',-5),
                               ('inc5',5),('inc10',10),('inc50',50)]:
                if btns[key].collidepoint(mx,my) and now - last_time[key] > 200:
                    base_speed = max(1, min(1000, base_speed + delta))
                    last_time[key] = now

        # Draw everything
        draw_maze(win, CELL_SIZE, OFF_X, OFF_Y)
        draw_goal(win, CELL_SIZE, OFF_X, OFF_Y)
        if show_heatmap:
            draw_heatmap(win)

        if not paused:
            for ag in agents:
                ag.update(sim_dt)
        for ag in agents:
            ag.draw(win, CELL_SIZE, OFF_X, OFF_Y)

        draw_bottom_ui()
        draw_side_panel()
        pygame.display.flip()

if __name__ == "__main__":
    main()
