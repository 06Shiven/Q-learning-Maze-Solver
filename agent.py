import random
import pygame
import maze
from maze import ROWS, COLS

# ─── HYPERPARAMETERS ────────────────────────────────────────────────────────
ACTIONS       = ['up', 'down', 'left', 'right']
OPPOSITE      = {'up':'down', 'down':'up', 'left':'right', 'right':'left'}
ALPHA, GAMMA  = 0.1, 0.9
EPSILON       = 0.2       # exploration rate
MOVE_DURATION = 200       # ms per cell

class Agent:
    def __init__(self, color, start=(1,1)):
        self.color        = color
        self.start        = start
        self.goal         = maze.goal_pos

        # interpolation state
        self.pos          = start
        self.prev_pos     = start
        self.target_pos   = start
        self.anim_t       = 1.0

        # Q-table
        self.Q = { (r, c): {a: 0.0 for a in ACTIONS}
                   for r in range(ROWS) for c in range(COLS) }

        # history & stats
        self.last_action    = None
        self.prev_prev_pos  = start
        self.epsilon        = EPSILON
        self.steps          = 0
        self.wins           = 0
        self.best_len       = float('inf')
        self.total_steps    = 0

    def reset(self):
        """Reset between episodes but keep ε constant for ongoing exploration."""
        self.pos, self.prev_pos, self.target_pos = self.start, self.start, self.start
        self.anim_t = 1.0
        self.last_action = None
        self.prev_prev_pos = self.start
        self.steps = 0

    def _compute_next(self, action):
        r, c = self.pos
        nr, nc = r, c
        if   action=='up'    and r>0:      nr -= 1
        elif action=='down'  and r<ROWS-1: nr += 1
        elif action=='left'  and c>0:      nc -= 1
        elif action=='right' and c<COLS-1: nc += 1
        return (nr, nc) if maze.maze[nr][nc] == 1 else (r, c)

    def choose_action(self):
        """ε-greedy with no immediate reversals. Full random until first win."""
        legal = []
        for a in ACTIONS:
            nxt = self._compute_next(a)
            # ban reversal
            if self.last_action and a == OPPOSITE[self.last_action]:
                continue
            # ban walls
            if nxt == self.pos:
                continue
            legal.append(a)
        if not legal:
            legal = [a for a in ACTIONS if self._compute_next(a) != self.pos]

        # fully random on first run
        if self.wins == 0:
            return random.choice(legal)

        # thereafter ε-greedy
        if random.random() < self.epsilon:
            return random.choice(legal)
        return max(legal, key=lambda a: self.Q[self.pos][a])

    def update(self, dt):
        """Advance animation or choose + execute + learn."""
        if self.anim_t < 1.0:
            self.anim_t = min(1.0, self.anim_t + dt/MOVE_DURATION)
            if self.anim_t >= 1.0:
                old, new = self.prev_pos, self.target_pos
                self.pos = new
                self._q_update(old, self.last_action, new)
            return

        action   = self.choose_action()
        old_cell = self.pos
        next_cell= self._compute_next(action)

        # wall-hit
        if next_cell == old_cell:
            best_val = max(self.Q[old_cell].values())
            self.Q[old_cell][action] += ALPHA*( -1 + GAMMA*best_val - self.Q[old_cell][action])
            return

        # commit
        self.prev_prev_pos = self.prev_pos
        self.prev_pos      = self.pos
        self.target_pos    = next_cell
        self.anim_t        = 0.0
        self.last_action   = action

    def _q_update(self, old, action, new):
        if new == self.goal:
            reward = 1.0
        else:
            pd = abs(old[0] - self.goal[0]) + abs(old[1] - self.goal[1])
            nd = abs(new[0] - self.goal[0]) + abs(new[1] - self.goal[1])
            reward = 0.01 * (pd - nd)

        best_next = max(self.Q[new].values())
        self.Q[old][action] += ALPHA*(reward + GAMMA*best_next - self.Q[old][action])

        if new == self.goal:
            # record stats
            self.wins += 1
            self.total_steps += self.steps
            if self.steps < self.best_len:
                self.best_len = self.steps
            self.reset()

    def draw(self, win, cell_size, off_x=0, off_y=0):
        y = (1-self.anim_t)*self.prev_pos[0] + self.anim_t*self.target_pos[0]
        x = (1-self.anim_t)*self.prev_pos[1] + self.anim_t*self.target_pos[1]
        cx = off_x + x*cell_size + cell_size/2
        cy = off_y + y*cell_size + cell_size/2
        radius = cell_size // 3
        pygame.draw.circle(win, self.color, (int(cx), int(cy)), radius)
