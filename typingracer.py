import copy
import pygame
import random

pygame.init()

from nltk.corpus import words

# ============================================================
#   CODENEST TYPING RACER — Redesigned to match CodeNest UI
# ============================================================

wordlist = words.words()
len_indexes = []
length = 1

wordlist.sort(key=len)
for i in range(len(wordlist)):
    if len(wordlist[i]) > length:
        length += 1
        len_indexes.append(i)
len_indexes.append(len(wordlist))

# ── Window ───────────────────────────────────────────────────
WIDTH  = 1100
HEIGHT = 680
screen = pygame.display.set_mode([WIDTH, HEIGHT])
pygame.display.set_caption('CodeNest · Typing Racer')
timer  = pygame.time.Clock()
fps    = 60

# ── CodeNest Color Palette ───────────────────────────────────
CN_BG           = (10,  15,  30)   # dark navy — body bg
CN_SIDEBAR      = (15,  23,  42)   # sidebar bg
CN_CARD         = (255, 255, 255, 20)   # glass card (alpha)
CN_CARD_BORDER  = (255, 255, 255, 35)
CN_ACCENT       = (255,  59,  92)  # #ff3b5c  — red accent
CN_ACCENT2      = (108,  92, 231)  # #6C5CE7  — purple
CN_GREEN        = ( 16, 185, 129)  # #10b981
CN_YELLOW       = (252, 211,  77)  # #fcd34d
CN_ORANGE       = (253, 110,  33)  # #fd6e21
CN_WHITE        = (255, 255, 255)
CN_MUTED        = (160, 160, 190)
CN_TEXT_DIM     = (100, 110, 140)
CN_SIDEBAR_W    = 220              # sidebar width in pixels

# ── Fonts (falls back to pygame default if custom not present)
def load_font(size, bold=False):
    try:
        return pygame.font.Font('assets/fonts/Square.ttf', size)
    except:
        return pygame.font.SysFont('Segoe UI', size, bold=bold)

def load_mono(size):
    try:
        return pygame.font.Font('assets/fonts/AldotheApache.ttf', size)
    except:
        return pygame.font.SysFont('Consolas', size)

font_logo     = load_font(22, bold=True)
font_nav      = load_font(14)
font_score    = load_font(13)
font_word     = load_mono(34)
font_input    = load_mono(26)
font_big      = load_font(32, bold=True)
font_med      = load_font(18, bold=True)
font_sm       = load_font(13)
font_badge    = load_font(11, bold=True)

# ── Sound ─────────────────────────────────────────────────────
pygame.mixer.init()
try:
    pygame.mixer.music.load('assets/sounds/music.mp3')
    pygame.mixer.music.set_volume(0.15)
    pygame.mixer.music.play(-1)
    click_snd = pygame.mixer.Sound('assets/sounds/click.mp3')
    woosh_snd = pygame.mixer.Sound('assets/sounds/Swoosh.mp3')
    wrong_snd = pygame.mixer.Sound('assets/sounds/Instrument Strum.mp3')
    click_snd.set_volume(0.3)
    woosh_snd.set_volume(0.2)
    wrong_snd.set_volume(0.3)
except:
    click_snd = woosh_snd = wrong_snd = None

def play(snd):
    if snd:
        snd.play()

# ── Game State ────────────────────────────────────────────────
score        = 0
level        = 1
lives        = 5
word_objects = []
pz           = True
new_level    = True
submit       = ''
active_str   = ''
choices      = [False, True, False, False, False, False, False]
letters      = list('abcdefghijklmnopqrstuvwxyz')

try:
    with open('high_score.txt', 'r') as f:
        high_score = int(f.readlines()[0])
except:
    high_score = 0

# ── Helpers ───────────────────────────────────────────────────
def draw_rect_alpha(surf, color, rect, radius=0):
    """Draw a rectangle with per-surface alpha (glass effect)."""
    s = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
    pygame.draw.rect(s, color, (0, 0, rect[2], rect[3]), border_radius=radius)
    surf.blit(s, (rect[0], rect[1]))

def draw_rounded_rect(surf, color, rect, radius=12, border=0, border_color=None):
    pygame.draw.rect(surf, color, rect, border, border_radius=radius)
    if border_color and border > 0:
        pygame.draw.rect(surf, border_color, rect, border, border_radius=radius)

def pill(surf, text, font, fg, bg, x, y, pad_x=12, pad_y=5, radius=20):
    """Draw a rounded badge/pill."""
    tw, th = font.size(text)
    pw, ph = tw + pad_x * 2, th + pad_y * 2
    draw_rect_alpha(surf, (*bg, 40), (x, y, pw, ph), radius)
    pygame.draw.rect(surf, (*bg, 120), (x, y, pw, ph), 1, border_radius=radius)
    surf.blit(font.render(text, True, fg), (x + pad_x, y + pad_y))
    return pw, ph

def stat_pill(surf, label, value, color, x, y):
    """Score/Level/Lives pill matching CodeNest streak-badge style."""
    draw_rect_alpha(surf, (*color, 25), (x, y, 110, 42), 20)
    pygame.draw.rect(surf, (*color, 80), (x, y, 110, 42), 1, border_radius=20)
    surf.blit(font_score.render(label, True, (*color,)), (x + 10, y + 5))
    surf.blit(font_med.render(str(value), True, CN_WHITE), (x + 10, y + 20))

# ── Word Class ────────────────────────────────────────────────
class Word:
    def __init__(self, text, speed, y_pos, x_pos):
        self.text  = text
        self.speed = speed
        self.y_pos = y_pos
        self.x_pos = x_pos
        # each word gets a subtle color tint based on speed
        tints = [CN_WHITE, (200, 230, 255), (255, 200, 200)]
        self.base_color = tints[min(speed - 1, 2)]

    def draw(self):
        act_len = len(active_str)
        matched  = active_str == self.text[:act_len] and act_len > 0

        # word background pill
        tw = font_word.size(self.text)[0]
        draw_rect_alpha(screen, (255, 255, 255, 12),
                        (self.x_pos - 8, self.y_pos - 4, tw + 16, 42), 8)

        # render full word in base color
        screen.blit(font_word.render(self.text, True, self.base_color),
                    (self.x_pos, self.y_pos))

        # overlay matched prefix in accent green
        if matched and act_len > 0:
            screen.blit(font_word.render(active_str, True, CN_GREEN),
                        (self.x_pos, self.y_pos))

        # speed indicator dot
        dot_colors = [CN_GREEN, CN_YELLOW, CN_ACCENT]
        pygame.draw.circle(screen, dot_colors[min(self.speed - 1, 2)],
                           (self.x_pos - 4, self.y_pos + 18), 4)

    def update(self):
        self.x_pos -= self.speed


# ── Button Class ──────────────────────────────────────────────
class Button:
    def __init__(self, x, y, w, h, text, surf, color=None, radius=12):
        self.x      = x
        self.y      = y
        self.w      = w
        self.h      = h
        self.text   = text
        self.surf   = surf
        self.color  = color or CN_ACCENT2
        self.radius = radius
        self.clicked = False

    def draw(self):
        rect = pygame.Rect(self.x, self.y, self.w, self.h)
        mouse = pygame.mouse.get_pos()
        hovered = rect.collidepoint(mouse)
        pressed = pygame.mouse.get_pressed()[0]

        # offset mouse by surf position if surf != screen
        # (for pause overlay surface, mouse coords are global so just use global)
        bg = self.color
        if hovered:
            bg = tuple(min(c + 30, 255) for c in self.color)
            if pressed:
                bg = tuple(max(c - 20, 0) for c in self.color)
                self.clicked = True

        draw_rect_alpha(self.surf, (*bg, 220), (self.x, self.y, self.w, self.h), self.radius)
        pygame.draw.rect(self.surf, (*CN_WHITE, 60),
                         (self.x, self.y, self.w, self.h), 1, border_radius=self.radius)

        tw, th = font_nav.size(self.text)
        self.surf.blit(font_nav.render(self.text, True, CN_WHITE),
                       (self.x + (self.w - tw) // 2, self.y + (self.h - th) // 2))
        return self.clicked


# ── Draw Sidebar ──────────────────────────────────────────────
NAV_ITEMS = [
    ('⌨  Typing Racer', True),
    ('📊  Leaderboard',  False),
    ('⚙   Settings',    False),
]

def draw_sidebar():
    # sidebar background
    draw_rect_alpha(screen, (*CN_SIDEBAR, 210), (0, 0, CN_SIDEBAR_W, HEIGHT), 0)
    pygame.draw.line(screen, (*CN_WHITE, 25), (CN_SIDEBAR_W, 0), (CN_SIDEBAR_W, HEIGHT), 1)

    # logo
    logo_icon = font_med.render('</>', True, CN_ACCENT)
    logo_text = font_med.render(' CodeNest', True, CN_WHITE)
    screen.blit(logo_icon, (18, 22))
    screen.blit(logo_text, (18 + logo_icon.get_width(), 22))

    # nav items
    for i, (label, active) in enumerate(NAV_ITEMS):
        y = 80 + i * 48
        if active:
            draw_rect_alpha(screen, (*CN_ACCENT, 25), (8, y, CN_SIDEBAR_W - 16, 38), 10)
            pygame.draw.rect(screen, CN_ACCENT, (8, y, 3, 38), border_radius=2)
        color = CN_WHITE if active else CN_MUTED
        screen.blit(font_nav.render(label, True, color), (20, y + 10))

    # focus mode card at bottom
    card_y = HEIGHT - 90
    draw_rect_alpha(screen, (*CN_ACCENT2, 30), (10, card_y, CN_SIDEBAR_W - 20, 72), 12)
    pygame.draw.rect(screen, (*CN_ACCENT2, 60), (10, card_y, CN_SIDEBAR_W - 20, 72), 1, border_radius=12)
    screen.blit(font_sm.render('🌿  Focus Mode', True, CN_WHITE), (20, card_y + 10))
    screen.blit(font_score.render('Stay focused. Keep typing.', True, CN_MUTED), (20, card_y + 32))
    screen.blit(font_score.render(f'Session XP:  +{score // 10}', True, CN_GREEN), (20, card_y + 50))


# ── Draw Top Bar ──────────────────────────────────────────────
def draw_topbar():
    bar_h = 56
    draw_rect_alpha(screen, (*CN_BG, 200), (CN_SIDEBAR_W, 0, WIDTH - CN_SIDEBAR_W, bar_h), 0)
    pygame.draw.line(screen, (*CN_WHITE, 20),
                     (CN_SIDEBAR_W, bar_h), (WIDTH, bar_h), 1)

    # page title
    screen.blit(font_med.render('Typing Racer', True, CN_WHITE), (CN_SIDEBAR_W + 20, 16))

    # stat pills — score / level / lives
    stat_pill(screen, 'SCORE',  score,      CN_ACCENT2, WIDTH - 360, 7)
    stat_pill(screen, 'LEVEL',  level,      CN_GREEN,   WIDTH - 240, 7)
    stat_pill(screen, 'LIVES',  '♥' * max(lives, 0), CN_ACCENT, WIDTH - 120, 7)


# ── Draw Game Area ────────────────────────────────────────────
GAME_X = CN_SIDEBAR_W
GAME_Y = 56
GAME_W = WIDTH - CN_SIDEBAR_W
GAME_H = HEIGHT - 56 - 80   # leave bottom bar

def draw_game_area():
    # subtle grid lines
    for y in range(GAME_Y, GAME_Y + GAME_H, 60):
        pygame.draw.line(screen, (*CN_WHITE, 6), (GAME_X, y), (WIDTH, y), 1)

    # high score badge top-right
    pill(screen, f'🏆  Best: {high_score}', font_score,
         CN_YELLOW, (100, 80, 10), WIDTH - 155, GAME_Y + 10)


# ── Draw Bottom Input Bar ─────────────────────────────────────
def draw_input_bar():
    bar_y = HEIGHT - 80
    draw_rect_alpha(screen, (*CN_SIDEBAR, 230), (GAME_X, bar_y, GAME_W, 80), 0)
    pygame.draw.line(screen, (*CN_WHITE, 25), (GAME_X, bar_y), (WIDTH, bar_y), 1)

    # input box
    iw = GAME_W - 220
    draw_rect_alpha(screen, (255, 255, 255, 15), (GAME_X + 16, bar_y + 16, iw, 48), 12)
    pygame.draw.rect(screen, (*CN_ACCENT2, 180), (GAME_X + 16, bar_y + 16, iw, 48), 1, border_radius=12)

    # typed text or placeholder
    if active_str:
        screen.blit(font_input.render(active_str, True, CN_WHITE),
                    (GAME_X + 28, bar_y + 26))
    else:
        screen.blit(font_input.render('Start typing...', True, CN_TEXT_DIM),
                    (GAME_X + 28, bar_y + 26))

    # cursor blink (simple: show if time % 1000 < 500)
    if pygame.time.get_ticks() % 1000 < 600 and active_str is not None:
        cx = GAME_X + 28 + font_input.size(active_str)[0]
        pygame.draw.rect(screen, CN_ACCENT, (cx, bar_y + 28, 2, 28))

    # ENTER hint
    screen.blit(font_score.render('ENTER / SPACE to submit   ESC to pause', True, CN_TEXT_DIM),
                (GAME_X + 20, bar_y + 66))

    # pause button
    pause_btn = Button(WIDTH - 180, bar_y + 16, 100, 48, '⏸  Pause', screen, CN_ACCENT2)
    return pause_btn.draw()


# ── Draw Pause Overlay ────────────────────────────────────────
def draw_pause():
    choice_commits = copy.deepcopy(choices)

    # full-screen dim
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.rect(overlay, (5, 8, 20, 180), (0, 0, WIDTH, HEIGHT))
    screen.blit(overlay, (0, 0))

    # glass modal
    mw, mh = 620, 380
    mx = (WIDTH - mw) // 2
    my = (HEIGHT - mh) // 2

    draw_rect_alpha(screen, (*CN_SIDEBAR, 240), (mx, my, mw, mh), 18)
    pygame.draw.rect(screen, (*CN_ACCENT2, 80), (mx, my, mw, mh), 1, border_radius=18)

    # accent top bar
    draw_rect_alpha(screen, (*CN_ACCENT, 200), (mx, my, mw, 4), 2)

    # header
    screen.blit(font_big.render('MENU', True, CN_WHITE), (mx + 24, my + 20))
    screen.blit(font_sm.render(f'High Score: {high_score}', True, CN_MUTED), (mx + 24, my + 58))

    # divider
    pygame.draw.line(screen, (*CN_WHITE, 30), (mx + 20, my + 80), (mx + mw - 20, my + 80), 1)

    # PLAY button
    play_btn  = Button(mx + 30,  my + 100, 180, 52, '▶   Play', screen, (16, 185, 129), 12)
    quit_btn  = Button(mx + 230, my + 100, 180, 52, '✕   Quit', screen, CN_ACCENT, 12)
    play_clicked = play_btn.draw()
    quit_clicked = quit_btn.draw()

    # word length section
    screen.blit(font_score.render('Word Length Filter:', True, CN_MUTED), (mx + 24, my + 175))
    for i in range(len(choices)):
        bx = mx + 30 + i * 78
        by = my + 200
        active = choices[i]
        col = CN_ACCENT2 if active else (40, 50, 70)
        btn = Button(bx, by, 64, 38, str(i + 2), screen, col, 8)
        if btn.draw():
            choice_commits[i] = not choice_commits[i]
        if active:
            pygame.draw.rect(screen, CN_GREEN, (bx, by, 64, 38), 2, border_radius=8)

    # stat summary
    pygame.draw.line(screen, (*CN_WHITE, 20), (mx + 20, my + 260), (mx + mw - 20, my + 260), 1)
    screen.blit(font_sm.render(f'Current Score: {score}', True, CN_YELLOW), (mx + 30, my + 275))
    screen.blit(font_sm.render(f'Level Reached: {level}', True, CN_GREEN), (mx + 200, my + 275))
    screen.blit(font_sm.render(f'Lives Left: {lives}', True, CN_ACCENT), (mx + 380, my + 275))

    # keybinds hint
    screen.blit(font_score.render('ESC — toggle menu    ENTER/SPACE — submit word', True, CN_TEXT_DIM),
                (mx + 30, my + 330))

    return play_clicked, choice_commits, quit_clicked


# ── Generate Level ────────────────────────────────────────────
def generate_level():
    word_objs = []
    include   = []
    vertical_spacing = (HEIGHT - 56 - 80 - 50) // level
    if True not in choices:
        choices[0] = True
    for i in range(len(choices)):
        if choices[i]:
            include.append((len_indexes[i], len_indexes[i + 1]))
    for i in range(level):
        speed = random.randint(1, min(level, 4))
        y_pos = GAME_Y + 10 + random.randint(i * vertical_spacing,
                                              (i + 1) * vertical_spacing - 40)
        x_pos = random.randint(WIDTH, WIDTH + 1200)
        ind_sel = random.choice(include)
        index   = random.randint(ind_sel[0], ind_sel[1])
        text    = wordlist[index].lower()
        word_objs.append(Word(text, speed, y_pos, x_pos))
    return word_objs


def check_answer(scor):
    for wrd in word_objects:
        if wrd.text == submit:
            pts = wrd.speed * len(wrd.text) * 10 * (len(wrd.text) / 4)
            scor += int(pts)
            word_objects.remove(wrd)
            play(woosh_snd)
    return scor


def check_high_score():
    global high_score
    if score > high_score:
        high_score = score
        with open('high_score.txt', 'w') as f:
            f.write(str(int(high_score)))


# ── Main Loop ─────────────────────────────────────────────────
run = True
while run:
    timer.tick(fps)

    # ── Background ──
    screen.fill(CN_BG)

    # faint radial glow center-right (matches CodeNest video glow)
    glow = pygame.Surface((600, 400), pygame.SRCALPHA)
    pygame.draw.ellipse(glow, (108, 92, 231, 18), (0, 0, 600, 400))
    screen.blit(glow, (WIDTH // 2, HEIGHT // 4))

    # ── Sidebar & Topbar ──
    draw_sidebar()
    draw_topbar()
    draw_game_area()

    # ── Pause overlay ──
    if pz:
        resume_butt, changes, quit_butt = draw_pause()
        if resume_butt:
            pz = False
        if quit_butt:
            check_high_score()
            run = False

    # ── Game objects ──
    if new_level and not pz:
        word_objects = generate_level()
        new_level = False
    else:
        for w in list(word_objects):
            w.draw()
            if not pz:
                w.update()
            if w.x_pos < GAME_X - 200:
                word_objects.remove(w)
                lives -= 1

    if not word_objects and not pz:
        level += 1
        new_level = True

    # ── Submit check ──
    if submit:
        init  = score
        score = check_answer(score)
        submit = ''
        if init == score:
            play(wrong_snd)

    # ── Input bar (drawn on top of words) ──
    pause_butt = draw_input_bar()

    # ── Events ──
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            check_high_score()
            run = False

        if event.type == pygame.KEYDOWN:
            if not pz:
                if event.unicode.lower() in letters:
                    active_str += event.unicode
                    play(click_snd)
                if event.key == pygame.K_BACKSPACE and active_str:
                    active_str = active_str[:-1]
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    submit     = active_str
                    active_str = ''
            if event.key == pygame.K_ESCAPE:
                pz = not pz

        if event.type == pygame.MOUSEBUTTONUP and pz:
            if event.button == 1:
                choices = changes

    if pause_butt:
        pz = True

    # ── Game over ──
    if lives < 0:
        pz        = True
        level     = 1
        lives     = 5
        word_objects = []
        new_level = True
        check_high_score()
        score     = 0

    pygame.display.flip()

pygame.quit()