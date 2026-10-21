"""Renderer - all Pygame drawing for the coffee kiosk.

The renderer only DRAWS. It never decides what happens next - main.py
tells it which screen to show and which data to display.

Design: warm cream background, dark coffee brown text, caramel accent,
white rounded cards with soft shadows, a modern navbar with the logo,
a compact step rail, a clean camera panel and toast notifications.
"""
import math

import cv2
import pygame

from src import config
from src.effects import Effects, ease_out_back, ease_out_cubic
from src.product import format_price

WINDOW_SIZE = (config.WINDOW_WIDTH, config.WINDOW_HEIGHT)
MAIN_WIDTH = config.MAIN_WIDTH
PANEL_X = config.WINDOW_WIDTH - config.SIDEBAR_WIDTH
PREVIEW_SIZE = (260, 195)

# MediaPipe hand skeleton: pairs of landmark numbers joined by a line
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),            # thumb
    (0, 5), (5, 6), (6, 7), (7, 8),            # index
    (5, 9), (9, 10), (10, 11), (11, 12),       # middle
    (9, 13), (13, 14), (14, 15), (15, 16),     # ring
    (13, 17), (17, 18), (18, 19), (19, 20),    # pinky
    (0, 17),                                   # palm edge
]
# Fingertip landmark number and short label for each finger
FINGER_TIPS = (("thumb", 4, "Thumb"), ("index", 8, "Index"), ("middle", 12, "Mid"),
               ("ring", 16, "Ring"), ("pinky", 20, "Pinky"))

# Gesture legend in the bottom instruction bar: (gesture, action)
GESTURE_LEGEND = [
    ("OPEN PALM", "Menu"),
    ("POINT", "Select"),
    ("RIGHT", "Next"),
    ("LEFT", "Prev"),
    ("2 FINGERS", "Qty"),
    ("THUMBS", "OK"),
    ("FIST", "Cancel"),
]


# ============================================================ small helpers
def make_font(size, bold=False):
    return pygame.font.SysFont("segoeui,helveticaneue,arial,dejavusans", size, bold=bold)


def draw_rounded_rect(surface, color, rect, radius=18, border_color=None, border_width=0):
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    if border_color is not None and border_width > 0:
        pygame.draw.rect(surface, border_color, rect, width=border_width, border_radius=radius)


def draw_card(surface, rect, radius=20, border_color=None, border_width=0):
    """A white rounded card with a soft shadow below it."""
    draw_rounded_rect(surface, config.COLORS["shadow"], rect.move(0, 5), radius)
    draw_rounded_rect(surface, config.COLORS["card"], rect, radius, border_color, border_width)


def draw_cup(surface, center, size, color):
    """A simple coffee cup made from shapes (placeholder / welcome art)."""
    size = int(size)
    x, y = center
    body = pygame.Rect(0, 0, size, int(size * 0.7))
    body.center = (x - size // 10, y + size // 12)
    pygame.draw.rect(surface, color, body, border_bottom_left_radius=size // 4,
                     border_bottom_right_radius=size // 4)
    handle = pygame.Rect(0, 0, size // 2, int(size / 2.4))
    handle.midleft = (body.right - size // 14, body.centery - size // 20)
    pygame.draw.ellipse(surface, color, handle, max(3, size // 14))
    saucer = pygame.Rect(0, 0, int(size * 1.25), size // 9)
    saucer.center = (body.centerx, body.bottom + size // 20)
    pygame.draw.rect(surface, color, saucer, border_radius=size // 18)


def make_placeholder(name, size, font):
    """Picture shown when a coffee image file is missing (never a different coffee)."""
    placeholder = pygame.Surface(size, pygame.SRCALPHA)
    draw_rounded_rect(placeholder, (232, 217, 197), placeholder.get_rect(), 16)
    draw_cup(placeholder, (size[0] // 2, size[1] // 2 - 12), min(size) // 2.2,
             config.COLORS["accent"])
    label = font.render(name, True, config.COLORS["accent_dark"])
    placeholder.blit(label, label.get_rect(center=(size[0] // 2, size[1] - 18)))
    return placeholder


class Renderer:
    """Draws every screen of the Smart Coffee Ordering app."""

    def __init__(self, screen, menu_manager):
        self.screen = screen
        self.menu = menu_manager
        self.fonts = {
            "title": make_font(46, True),
            "heading": make_font(30, True),
            "large": make_font(24, True),
            "body": make_font(20),
            "body_bold": make_font(20, True),
            "small": make_font(15),
            "small_bold": make_font(15, True),
            "tiny": make_font(13),
            "tiny_bold": make_font(13, True),
            "huge": make_font(96, True),
        }
        self.image_cache = {}
        self.logo_cache = {}
        self.logo_image = self._load_logo()
        self.hits = []          # clickable areas collected while drawing
        self.fx = Effects()     # animation clock, confetti, sparkles, bubbles
        self._last_selected_id = None
        self._selected_at = -10.0
        self._last_discount = False
        self._last_cart_count = None
        self._cart_bump_at = -10.0
        self._toast_message = None
        self._toast_at = 0.0
        self._pointer_trail = []

    # ------------------------------------------------------------ base tools
    def text(self, text, font, color, position, align="left"):
        """Draw text. align = 'left', 'center' or 'right' (relative to position)."""
        surface = self.fonts[font].render(str(text), True, config.COLORS[color])
        rect = surface.get_rect()
        if align == "center":
            rect.center = position
        elif align == "right":
            rect.midright = position
        else:
            rect.midleft = position
        self.screen.blit(surface, rect)
        return rect

    def register(self, rect, action, value=None):
        """Remember a clickable area for this frame (mouse support)."""
        self.hits.append((rect, action, value))

    def action_at(self, position):
        """Return (action, value) of the clickable area under position, or None."""
        if position is None:
            return None
        for rect, action, value in reversed(self.hits):   # topmost wins
            if rect.collidepoint(position):
                return action, value
        return None

    def button(self, rect, label, action, value=None, primary=True, small=False):
        """A modern rounded button. Registers itself for mouse clicks."""
        if primary:
            draw_rounded_rect(self.screen, config.COLORS["accent"], rect, 16)
            text_color = "white"
        else:
            draw_rounded_rect(self.screen, config.COLORS["beige"], rect, 16,
                              config.COLORS["border"], 2)
            text_color = "accent_dark"
        font = "small_bold" if small else "body_bold"
        self.text(label, font, text_color, rect.center, "center")
        self.register(rect, action, value)
        return rect

    def _load_logo(self):
        for path in config.LOGO_PATHS:
            if path.exists():
                try:
                    return pygame.image.load(str(path)).convert_alpha()
                except pygame.error as error:
                    print(f"[Renderer] Could not load logo {path.name}: {error}")
        return None

    def get_logo_image(self, size):
        """Scale the brand logo (returns None when no logo file exists)."""
        if self.logo_image is None:
            return None
        if size not in self.logo_cache:
            scale = min(size[0] / self.logo_image.get_width(),
                        size[1] / self.logo_image.get_height())
            scaled = (max(1, int(self.logo_image.get_width() * scale)),
                      max(1, int(self.logo_image.get_height() * scale)))
            self.logo_cache[size] = pygame.transform.smoothscale(self.logo_image, scaled)
        return self.logo_cache[size]

    def get_product_image(self, product, size):
        """Coffee picture scaled to fit; a placeholder when the file is missing."""
        key = (product.id, size)
        if key in self.image_cache:
            return self.image_cache[key]
        image_path = self.menu.get_image_path(product)
        image = None
        if image_path is not None:
            try:
                loaded = pygame.image.load(str(image_path)).convert_alpha()
                scale = min(size[0] / loaded.get_width(), size[1] / loaded.get_height())
                new_size = (max(1, int(loaded.get_width() * scale)),
                            max(1, int(loaded.get_height() * scale)))
                image = pygame.transform.smoothscale(loaded, new_size)
            except (pygame.error, OSError, ZeroDivisionError):
                image = None
        if image is None:
            image = make_placeholder(product.name, size, self.fonts["tiny_bold"])
        self.image_cache[key] = image
        return image

    def get_cover_image(self, product, size, radius):
        """Photo cropped to fill `size` with rounded corners (radius = size/2 -> circle)."""
        key = ("cover", product.id, size, radius)
        if key in self.image_cache:
            return self.image_cache[key]
        surf, path = None, self.menu.get_image_path(product)
        if path is not None:
            try:
                src = pygame.image.load(str(path)).convert_alpha()
                surf = pygame.Surface(size, pygame.SRCALPHA)
                if src.get_at((0, 0)).a < 250:          # cut-out cup: keep it whole on beige
                    draw_rounded_rect(surf, config.COLORS["beige"], surf.get_rect(), radius)
                    k = min(size[0] / src.get_width(), size[1] / src.get_height()) * 0.9
                    fit = pygame.transform.smoothscale(src, (max(1, round(src.get_width() * k)),
                                                             max(1, round(src.get_height() * k))))
                    surf.blit(fit, fit.get_rect(center=surf.get_rect().center))
                else:                                    # photo: fill the whole frame
                    k = max(size[0] / src.get_width(), size[1] / src.get_height())
                    big = pygame.transform.smoothscale(src, (max(1, round(src.get_width() * k)),
                                                             max(1, round(src.get_height() * k))))
                    surf.blit(big, big.get_rect(center=surf.get_rect().center))
                    mask = pygame.Surface(size, pygame.SRCALPHA)
                    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius)
                    surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            except (pygame.error, OSError, ZeroDivisionError):
                surf = None
        if surf is None:
            surf = make_placeholder(product.name, size, self.fonts["tiny_bold"])
        self.image_cache[key] = surf
        return surf

    def draw_product_picture(self, product, box_rect):
        """Draw a coffee image centered inside a rounded beige box."""
        image = self.get_cover_image(product, (box_rect.width, box_rect.height), 16)
        self.screen.blit(image, box_rect)

    # ============================================================ chrome
    def draw_background(self):
        """Start every frame: forget old click areas and paint the cream background."""
        self.hits = []
        self.fx.tick()
        self.screen.fill(config.COLORS["background"])

    def draw_effects(self):
        """Confetti and sparkles - drawn on top of the main area (not the camera panel)."""
        self.fx.draw_particles(self.screen, pygame.Rect(0, 0, MAIN_WIDTH, config.WINDOW_HEIGHT))

    @staticmethod
    def _draw_cart_icon(surface, center, color):
        """A tiny shopping-cart glyph for the navbar."""
        x, y = center
        pygame.draw.rect(surface, color, (x - 7, y - 5, 13, 9), 2, 3)
        pygame.draw.line(surface, color, (x - 11, y - 8), (x - 8, y - 8), 2)
        pygame.draw.circle(surface, color, (x - 4, y + 6), 2)
        pygame.draw.circle(surface, color, (x + 3, y + 6), 2)

    def draw_navbar(self, section_label, cart_count, ai_ready):
        """Modern top bar:  logo + name | current section | cart + AI status."""
        width = config.WINDOW_WIDTH
        nav = pygame.Rect(0, 0, width, config.NAVBAR_HEIGHT)
        pygame.draw.rect(self.screen, config.COLORS["card"], nav)
        pygame.draw.line(self.screen, config.COLORS["border"],
                         (0, config.NAVBAR_HEIGHT - 1), (width, config.NAVBAR_HEIGHT - 1), 2)

        # LEFT: logo + shop name
        logo = self.get_logo_image((44, 44))
        if logo is not None:
            self.screen.blit(logo, logo.get_rect(center=(40, 36)))
        else:
            draw_cup(self.screen, (40, 32), 34, config.COLORS["accent"])
        self.text(config.SHOP_NAME, "body_bold", "text", (72, 36))

        # CENTER: current section (hidden on the welcome screen)
        if section_label != "Welcome":
            label_surface = self.fonts["small_bold"].render(section_label, True,
                                                            config.COLORS["accent_dark"])
            pill = pygame.Rect(0, 0, label_surface.get_width() + 44, 32)
            pill.center = (width // 2, 36)
            draw_rounded_rect(self.screen, config.COLORS["accent_soft"], pill, 15)
            self.screen.blit(label_surface, label_surface.get_rect(center=pill.center))

        # RIGHT: cart pill + AI pill
        if self._last_cart_count is not None and cart_count != self._last_cart_count:
            self._cart_bump_at = self.fx.now          # the cart "jumps" when it changes
        self._last_cart_count = cart_count
        bump = max(0.0, 1.0 - (self.fx.now - self._cart_bump_at) / 0.45)
        bump = math.sin(bump * math.pi) if bump > 0 else 0.0
        cart_rect = pygame.Rect(0, 0, 120, 40)
        cart_rect.right = width - 24
        cart_rect = cart_rect.inflate(int(14 * bump), int(10 * bump))
        cart_rect.right = width - 24 + int(7 * bump)
        draw_rounded_rect(self.screen, config.COLORS["accent_soft"], cart_rect, 16)
        self._draw_cart_icon(self.screen, (cart_rect.x + 22, cart_rect.centery),
                             config.COLORS["accent_dark"])
        item_label = f"{cart_count} item" if cart_count == 1 else f"{cart_count} items"
        self.text(item_label, "small_bold", "accent_dark", (cart_rect.x + 40, cart_rect.centery))

        ai_rect = pygame.Rect(0, 0, 116, 40)
        ai_rect.right = cart_rect.left - 12
        ai_bg = config.COLORS["good_soft"] if ai_ready else config.COLORS["beige"]
        draw_rounded_rect(self.screen, ai_bg, ai_rect, 16)
        dot_color = config.COLORS["good"] if ai_ready else config.COLORS["muted"]
        breathe = 6 + (1.6 * self.fx.wave(0.8) if ai_ready else 0)     # the AI dot "breathes"
        pygame.draw.circle(self.screen, dot_color, (ai_rect.x + 18, ai_rect.centery), int(breathe))
        self.text("AI Ready" if ai_ready else "AI Off", "small_bold",
                  "good" if ai_ready else "muted", (ai_rect.x + 32, ai_rect.centery))

    def draw_progress(self, current_state, hovered_state=None):
        """Compact step rail: Welcome > Menu > ... > Done (current step highlighted)."""
        band = pygame.Rect(0, config.NAVBAR_HEIGHT, MAIN_WIDTH, config.PROGRESS_HEIGHT)
        pygame.draw.line(self.screen, config.COLORS["border"],
                         (0, band.bottom - 1), (MAIN_WIDTH, band.bottom - 1), 1)

        steps = config.STEP_LABELS
        current_index = [name for name, _ in steps].index(current_state)
        cell = MAIN_WIDTH / len(steps)
        rail_y = band.centery
        first_x, last_x = cell * 0.5, cell * (len(steps) - 0.5)
        pygame.draw.line(self.screen, config.COLORS["shadow"], (first_x, rail_y), (last_x, rail_y), 3)
        pygame.draw.line(self.screen, config.COLORS["accent"], (first_x, rail_y),
                         (cell * (current_index + 0.5), rail_y), 3)

        for index, (name, label) in enumerate(steps):
            is_current = index == current_index
            chip = pygame.Rect(0, 0, int(cell) - 18, 32)
            chip.center = (int(cell * (index + 0.5)), rail_y)
            if is_current:
                draw_rounded_rect(self.screen, config.COLORS["accent"], chip, 16)
                text_color = "white"
            else:
                bg = config.COLORS["accent_soft"] if index < current_index else config.COLORS["background"]
                border = config.COLORS["accent"] if hovered_state == name else None
                draw_rounded_rect(self.screen, bg, chip, 16, border, 2 if border else 0)
                text_color = "accent_dark" if index < current_index else "muted"
            self.text(label, "small_bold" if is_current else "tiny_bold", text_color,
                      chip.center, "center")
            self.register(chip, "step", name)

    # ============================================================ screens
    def draw_welcome(self, ai_ready=False):
        """Hero screen: headline + start button on the left, coffee collage on the right."""
        left = 64
        self.fx.ambient(self.screen, pygame.Rect(0, config.CONTENT_TOP - 20, MAIN_WIDTH,
                                                 config.CONTENT_BOTTOM - config.CONTENT_TOP + 20))
        # soft background shapes behind the collage
        pygame.draw.circle(self.screen, config.COLORS["accent_soft"], (730, 400), 250)
        pygame.draw.circle(self.screen, config.COLORS["beige"], (730, 400), 190)

        # collage: three real coffees in white circles with soft shadows
        by_name = {p.name: p for p in self.menu.products}
        picks = [by_name.get(n) for n in ("Cappuccino", "Iced Latte", "Caramel Macchiato")]
        picks = [p for p in picks if p] or self.menu.products[:3]
        layout = [((730, 410), 300), ((575, 560), 150), ((880, 250), 160)]
        intro = ease_out_back(self.fx.see("welcome") / 0.7)            # collage pops in
        for index, (product, (center, size)) in enumerate(zip(picks, layout)):
            bob = math.sin(self.fx.now * 1.5 + index * 1.7) * 7         # gentle floating
            size = int(size * min(1.15, max(0.0, intro - index * 0.04)))
            if size < 40:
                continue                                             # still too small to draw
            center = (center[0], center[1] + bob)
            disc = pygame.Rect(0, 0, size, size)
            disc.center = center
            pygame.draw.circle(self.screen, config.COLORS["shadow"], disc.move(0, 6).center, size // 2)
            pygame.draw.circle(self.screen, config.COLORS["white"], disc.center, size // 2)
            ring = size - 14
            image = self.get_cover_image(product, (ring, ring), ring // 2)
            self.screen.blit(image, image.get_rect(center=disc.center))

        # headline + slogan + start button
        self.text("Order coffee with", "title", "text", (left, 250))
        self.text("a wave of your hand.", "title", "accent", (left, 304))
        self.text("No touching, no queue. Just show your palm,", "body", "muted", (left, 366))
        self.text("pick your drink and we start brewing.", "body", "muted", (left, 394))
        start_rect = pygame.Rect(left, 440, 250, 58)
        self.fx.pulse_ring(self.screen, start_rect, radius=26)
        self.button(start_rect, "Start Ordering", "start")

        if ai_ready:
            dot, status, bg, color = (config.COLORS["good"], "Camera ready - show your open palm",
                                      config.COLORS["good_soft"], "good")
        else:
            dot, status, bg, color = (config.COLORS["muted"], ("Camera not found - connect a camera" if config.GESTURE_ONLY
                                      else "Camera off - use keyboard or mouse"),
                                      config.COLORS["beige"], "muted")
        status_surface = self.fonts["tiny"].render(status, True, config.COLORS[color])
        pill = pygame.Rect(left, 520, status_surface.get_width() + 44, 32)
        draw_rounded_rect(self.screen, bg, pill, 16)
        pygame.draw.circle(self.screen, dot, (pill.x + 17, pill.centery), 5)
        self.screen.blit(status_surface, status_surface.get_rect(midleft=(pill.x + 30, pill.centery)))

    @staticmethod
    def _card_rects():
        """The 3 x 2 grid of coffee cards inside the main area."""
        margin, gap_x, gap_y, top = 24, 16, 16, 178
        width = (MAIN_WIDTH - 2 * margin - 2 * gap_x) // 3        # 300
        height = (config.CONTENT_BOTTOM - 8 - top - gap_y) // 2   # 223
        rects = []
        for index in range(config.ITEMS_PER_PAGE):
            row, column = divmod(index, 3)
            rects.append(pygame.Rect(margin + column * (width + gap_x),
                                     top + row * (height + gap_y), width, height))
        return rects

    def draw_menu(self, hovered_product, selected_product):
        """Menu page: heading, page controls and the coffee cards."""
        if not self.menu.products:
            card = pygame.Rect(*config.CONTENT_CARD)
            draw_card(self.screen, card, 24)
            self.text("The menu could not be loaded", "heading", "text",
                      (card.centerx, card.y + 180), "center")
            detail = self.menu.error_message or "Check data/menu.json"
            self.text(detail, "body", "muted", (card.centerx, card.y + 230), "center")
            return

        self.text("Choose your coffee", "heading", "text", (24, 150))

        # page controls (right side of the heading row)
        next_rect = pygame.Rect(MAIN_WIDTH - 24 - 36, 132, 36, 36)
        prev_rect = pygame.Rect(next_rect.left - 44, 132, 36, 36)
        page_label = f"Page {self.menu.page + 1} / {self.menu.page_count}"
        self.text(page_label, "small_bold", "muted", (prev_rect.left - 14, 150), "right")
        self._page_button(prev_rect, "‹", self.menu.can_go_previous, "prev_page")
        self._page_button(next_rect, "›", self.menu.can_go_next, "next_page")

        since_enter = self.fx.see(("menu", self.menu.page))
        selected_id = selected_product.id if selected_product is not None else None
        selection_changed = selected_id != self._last_selected_id
        if selection_changed:
            self._selected_at = self.fx.now
            self._last_selected_id = selected_id
        for index, (rect, product) in enumerate(zip(self._card_rects(), self.menu.current_products)):
            is_selected = selected_id is not None and selected_id == product.id
            is_hovered = hovered_product is not None and hovered_product.id == product.id
            if is_selected and selection_changed and since_enter > 0.5:
                self.fx.sparkle(rect.move(0, 70).midtop, 16)       # little stars on selection
            pop = ease_out_back((since_enter - index * 0.07) / 0.45)
            if since_enter < index * 0.07:
                self.register(rect, "card", product)               # not visible yet, still clickable
                continue
            self._draw_product_card(rect, product, is_hovered, is_selected,
                                    slide=int((1.0 - pop) * 42))

    def _page_button(self, rect, chevron, enabled, action):
        if enabled:
            self.button(rect, chevron, action, primary=False, small=True)
        else:
            draw_rounded_rect(self.screen, config.COLORS["beige"], rect, 12,
                              config.COLORS["border"], 2)
            self.text(chevron, "body_bold", "muted", rect.center, "center")

    def _draw_product_card(self, rect, product, is_hovered, is_selected, slide=0):
        """One modern coffee card: image, name, price, selection state."""
        hit_rect = rect                                   # the click area never moves
        lift = self.fx.smooth(("lift", product.id), 1.0 if is_hovered else 0.0, 14.0)
        rect = rect.move(0, slide - int(9 * lift))        # slide-in + smooth hover lift
        pulse = self.fx.wave(1.2)
        if is_selected:
            border, width = config.COLORS["accent"], 3 + int(pulse * 1.5)
        elif is_hovered or lift > 0.05:
            border, width = config.COLORS["accent"], 2
        else:
            border, width = None, 0
        draw_rounded_rect(self.screen, config.COLORS["shadow"], rect.move(0, 5 + int(8 * lift)), 20)
        draw_rounded_rect(self.screen, config.COLORS["card"], rect, 20, border, width)

        image_rect = pygame.Rect(rect.x + 12, rect.y + 12, rect.width - 24, 126)
        self.draw_product_picture(product, image_rect)
        self.text(product.name, "body_bold", "text", (rect.x + 16, rect.y + 164))
        self.text(format_price(product.price), "large", "accent_dark", (rect.x + 16, rect.y + 196))

        if is_selected:
            badge_center = (image_rect.right - 16, image_rect.y + 16)
            badge_scale = ease_out_back((self.fx.now - self._selected_at) / 0.35)
            pygame.draw.circle(self.screen, config.COLORS["accent_dark"], badge_center,
                               max(1, int(13 * badge_scale)))
            pygame.draw.lines(self.screen, config.COLORS["white"], False,
                              [(badge_center[0] - 6, badge_center[1]),
                               (badge_center[0] - 2, badge_center[1] + 4),
                               (badge_center[0] + 6, badge_center[1] - 5)], 2)
        self.register(hit_rect, "card", product)

    @staticmethod
    def _content_card():
        """The big white card used by most screens."""
        return pygame.Rect(*config.CONTENT_CARD)

    def draw_select(self, product):
        """Selected coffee: big picture, name, price and description."""
        card = self._content_card()
        draw_card(self.screen, card, 24)
        if product is None:
            self.text("No coffee selected", "heading", "muted", card.center, "center")
            return
        self.draw_product_picture(product, pygame.Rect(card.x + 28, card.y + 28, 350, 340))
        self.text("You selected", "small_bold", "muted", (card.x + 420, card.y + 66))
        self.text(product.name, "title", "text", (card.x + 420, card.y + 116))
        self.text(format_price(product.price), "huge", "accent_dark", (card.x + 414, card.y + 226))
        if product.description:
            self.text(product.description, "body", "muted", (card.x + 420, card.y + 306))
        self.text("THUMBS UP or Enter - continue", "small_bold", "good", (card.x + 420, card.y + 356))
        self.text("FIST or ESC - choose another coffee", "small", "muted",
                  (card.x + 420, card.y + 384))

        y = card.bottom - 72
        self.button(pygame.Rect(card.x + 420, y, 180, 48), "Continue", "continue")
        self.button(pygame.Rect(card.x + 616, y, 140, 48), "Back", "back", primary=False)

    def draw_quantity(self, product, quantity):
        """Choose how many cups: big number with - / + buttons."""
        card = self._content_card()
        draw_card(self.screen, card, 24)
        if product is None:
            self.text("No coffee selected", "heading", "muted", card.center, "center")
            return
        self.draw_product_picture(product, pygame.Rect(card.x + 28, card.y + 28, 300, 340))
        self.text(f"{format_price(product.price)} each", "body_bold", "accent_dark",
                  (card.x + 178, card.y + 396), "center")

        center_x = card.x + 640
        self.text(product.name, "heading", "text", (center_x, card.y + 66), "center")
        self.text("How many?", "body", "muted", (center_x, card.y + 112), "center")

        minus_rect = pygame.Rect(center_x - 168, card.y + 150, 52, 52)
        plus_rect = pygame.Rect(center_x + 116, card.y + 150, 52, 52)
        self.button(minus_rect, "−", "qty_minus", primary=False)
        self.button(plus_rect, "+", "qty_plus", primary=False)
        self.text(str(quantity), "huge", "accent_dark", (center_x, card.y + 178), "center")

        line_total = product.price * quantity
        self.text(f"{format_price(product.price)} x {quantity} = {format_price(line_total)}",
                  "large", "text", (center_x, card.y + 296), "center")
        self.text("TWO FINGERS, swipe or the buttons", "small", "muted",
                  (center_x, card.y + 336), "center")
        self.text("THUMBS UP to add to your order", "small_bold", "good",
                  (center_x, card.y + 366), "center")

        y = card.bottom - 72
        self.button(pygame.Rect(center_x - 160, y, 200, 48), "Add to order", "continue")
        self.button(pygame.Rect(center_x + 56, y, 140, 48), "Back", "back", primary=False)

    def draw_order_lines(self, cart, rect):
        """List the cart items and subtotal / discount / total inside `rect`."""
        if cart.is_empty():
            self.text("Your cart is empty", "body", "muted", (rect.x, rect.y))
            return
        line_height = 34 if len(cart.items) <= 6 else 27
        y = rect.y
        for item in cart.items:
            self.text(f"{item.name} x {item.quantity}", "body", "text", (rect.x, y))
            self.text(format_price(item.line_total()), "body", "text", (rect.right, y), "right")
            y += line_height

        y += 6
        pygame.draw.line(self.screen, config.COLORS["shadow"], (rect.x, y), (rect.right, y), 2)
        y += 26
        self.text("Subtotal", "body", "muted", (rect.x, y))
        self.text(format_price(cart.subtotal()), "body", "muted", (rect.right, y), "right")
        y += 32
        if cart.discount_applied:
            label = f"Smile discount ({config.DISCOUNT_PERCENT}%)"
            self.text(label, "body_bold", "good", (rect.x, y))
            self.text("-" + format_price(cart.discount_amount()), "body_bold", "good",
                      (rect.right, y), "right")
            y += 32
        y += 6
        self.text("Total", "large", "text", (rect.x, y))
        self.text(format_price(cart.total()), "large", "accent_dark", (rect.right, y), "right")

    def draw_discount(self, cart):
        """Smile for 10% off - the order so far on the right."""
        card = self._content_card()
        draw_card(self.screen, card, 24)

        happy = cart.discount_applied
        if happy and not self._last_discount:                        # the moment of the smile!
            self.fx.confetti((card.x + 230, card.y + 120), 60, 520.0)
            self.fx.sparkle((card.x + 230, card.y + 180), 18, 240.0)
        self._last_discount = happy
        since = self.fx.see("discount")
        bob = math.sin(self.fx.now * 2.0) * 5
        face_center = (card.x + 230, card.y + 180 + bob)
        face_center = (int(face_center[0]), int(face_center[1]))
        if not happy:
            self.fx.pulse_ring(self.screen, pygame.Rect(0, 0, 190, 190).move(
                face_center[0] - 95, face_center[1] - 95), radius=95, period=1.8)
        radius = 95 + int(8 * math.sin(min(1.0, since / 0.5) * math.pi)) if since < 0.5 else 95
        pygame.draw.circle(self.screen, config.COLORS["accent_soft"] if happy else config.COLORS["beige"],
                           face_center, radius)
        pygame.draw.circle(self.screen, config.COLORS["good"] if happy else config.COLORS["accent"],
                           face_center, radius, 5)
        blinking = (self.fx.now % 3.2) < 0.12 and not happy            # an idle blink
        for eye_x in (-34, 34):
            eye = (face_center[0] + eye_x, face_center[1] - 26)
            if happy:                                                  # happy ^ ^ eyes
                pygame.draw.arc(self.screen, config.COLORS["text"],
                                pygame.Rect(eye[0] - 12, eye[1] - 10, 24, 22),
                                math.pi * 0.1, math.pi * 0.9, 5)
            elif blinking:
                pygame.draw.line(self.screen, config.COLORS["text"],
                                 (eye[0] - 9, eye[1]), (eye[0] + 9, eye[1]), 4)
            else:
                pygame.draw.circle(self.screen, config.COLORS["text"], eye, 9)
        if happy:                                                      # big open smile
            mouth = pygame.Rect(0, 0, 90, 56)
            mouth.center = (face_center[0], face_center[1] + 22)
            pygame.draw.ellipse(self.screen, config.COLORS["text"], mouth)
            pygame.draw.rect(self.screen, config.COLORS["accent_soft"],
                             (mouth.x, mouth.y, mouth.width, mouth.height // 2 - 2))
        else:
            wide = 110 + int(10 * self.fx.wave(0.9))
            mouth = pygame.Rect(0, 0, wide, 84)
            mouth.center = (face_center[0], face_center[1] + 4)
            pygame.draw.arc(self.screen, config.COLORS["text"], mouth, math.pi * 1.1, math.pi * 1.9, 7)

        self.text("Smile for 10% off!", "heading", "text", (face_center[0], card.y + 330), "center")
        if cart.discount_applied:
            status, color = (f"{config.DISCOUNT_PERCENT}% discount applied!", "good")
        else:
            status, color = ("Smile at the camera or press G", "muted")
        self.text(status, "small_bold", color, (face_center[0], card.y + 372), "center")

        right_x = card.x + 470
        self.text("Your order", "large", "text", (right_x, card.y + 56))
        self.draw_order_lines(cart, pygame.Rect(right_x, card.y + 110, 400, 240))

        y = card.bottom - 72
        self.button(pygame.Rect(card.x + 28, y, 140, 48), "Back", "back", primary=False)
        self.button(pygame.Rect(card.x + 184, y, 180, 48), "Add another", "add_another",
                    primary=False)
        self.button(pygame.Rect(card.right - 28 - 180, y, 180, 48), "Continue", "continue")

    def draw_confirm(self, cart):
        """Final check before the order is saved."""
        card = self._content_card()
        draw_card(self.screen, card, 24)

        draw_cup(self.screen, (card.x + 230, card.y + 165), 150, config.COLORS["accent"])
        self.text("Ready to order?", "heading", "text", (card.x + 230, card.y + 310), "center")
        self.text("THUMBS UP or Enter - confirm", "small_bold", "good",
                  (card.x + 230, card.y + 352), "center")
        self.text("SMILE adds your 10% discount", "small", "muted",
                  (card.x + 230, card.y + 380), "center")
        self.text("FIST or C - clear the order", "small", "bad",
                  (card.x + 230, card.y + 408), "center")

        right_x = card.x + 470
        self.text("Your order", "large", "text", (right_x, card.y + 56))
        self.draw_order_lines(cart, pygame.Rect(right_x, card.y + 110, 400, 240))

        y = card.bottom - 72
        self.button(pygame.Rect(card.x + 28, y, 140, 48), "Back", "back", primary=False)
        self.button(pygame.Rect(card.x + 184, y, 150, 48), "Clear cart", "clear", primary=False)
        self.button(pygame.Rect(card.right - 28 - 210, y, 210, 48), "Confirm order", "confirm")

    def draw_summary(self, cart, order_number, kitchen_status):
        """Order saved: number, kitchen status and the final bill."""
        card = self._content_card()
        draw_card(self.screen, card, 24)
        center_x = card.centerx
        self.text("Order Summary", "title", "text", (center_x, card.y + 66), "center")

        # order number + kitchen status pills
        number_label = order_number or "#---"
        number_surface = self.fonts["body_bold"].render(number_label, True,
                                                        config.COLORS["accent_dark"])
        status_label = kitchen_status or "Saved"
        status_surface = self.fonts["small_bold"].render(status_label, True,
                                                         config.COLORS["good"])
        gap = 14
        total_width = number_surface.get_width() + status_surface.get_width() + gap + 48
        x = center_x - total_width // 2
        number_pill = pygame.Rect(x, card.y + 108, number_surface.get_width() + 32, 34)
        draw_rounded_rect(self.screen, config.COLORS["accent_soft"], number_pill, 17)
        self.screen.blit(number_surface, number_surface.get_rect(center=number_pill.center))
        status_pill = pygame.Rect(number_pill.right + gap, card.y + 108,
                                  status_surface.get_width() + 32, 34)
        draw_rounded_rect(self.screen, config.COLORS["good_soft"], status_pill, 17)
        pygame.draw.circle(self.screen, config.COLORS["good"],
                           (status_pill.x + 15, status_pill.centery), 5)
        self.screen.blit(status_surface,
                         status_surface.get_rect(center=(status_pill.centerx + 8,
                                                         status_pill.centery)))

        self.draw_order_lines(cart, pygame.Rect(center_x - 200, card.y + 180, 400, 250))

        y = card.bottom - 72
        self.button(pygame.Rect(center_x - 90, y, 180, 48), "Finish", "continue")

    def draw_complete(self, cart, order_number, kitchen_status, seconds_left):
        """Thank-you screen; closes itself after config.COMPLETE_SECONDS."""
        card = self._content_card()
        draw_card(self.screen, card, 24)
        since = self.fx.see("complete")
        if since < 0.05 and not self.fx.particles:                      # celebration!
            self.fx.confetti((card.x + 60, card.bottom - 40), 60, 700.0)
            self.fx.confetti((card.right - 60, card.bottom - 40), 60, 700.0)
        if since < 2.5:
            self.fx.confetti_rain(pygame.Rect(card.x, card.y, card.width, 10), 2)
        center = (card.centerx, card.y + 140)
        grow = ease_out_back(since / 0.55)                              # badge pops in
        radius = max(1, int(72 * grow))
        pygame.draw.circle(self.screen, config.COLORS["good_soft"], center,
                           radius + int(10 + 8 * self.fx.wave(0.7)))
        pygame.draw.circle(self.screen, config.COLORS["good"], center, radius)
        tick = ease_out_cubic((since - 0.25) / 0.4)                     # the tick draws itself
        a, b, c = (center[0] - 32, center[1] + 2), (center[0] - 8, center[1] + 28), \
                  (center[0] + 36, center[1] - 26)
        if tick > 0:
            first = min(1.0, tick * 2)
            mid = (a[0] + (b[0] - a[0]) * first, a[1] + (b[1] - a[1]) * first)
            points = [a, mid]
            if tick > 0.5:
                second = (tick - 0.5) * 2
                points.append((b[0] + (c[0] - b[0]) * second, b[1] + (c[1] - b[1]) * second))
            pygame.draw.lines(self.screen, config.COLORS["white"], False, points, 12)
        self.text("Thank you!", "title", "text", (card.centerx, card.y + 264), "center")
        number_label = order_number or ""
        line = "Your coffee is being prepared." if not number_label else f"{number_label} is being prepared."
        self.text(line, "large", "muted", (card.centerx, card.y + 316), "center")
        if kitchen_status:
            self.text(f"Kitchen status: {kitchen_status}", "body_bold", "accent_dark",
                      (card.centerx, card.y + 356), "center")
        self.text(f"Next customer in {max(0, math.ceil(seconds_left))} s", "small", "muted",
                  (card.centerx, card.y + 392), "center")
        y = card.bottom - 72
        self.button(pygame.Rect(card.centerx - 110, y, 220, 48), "New order", "new_order")

    # ============================================================ feedback
    def draw_toast(self, message):
        """Small modern notification at the top of the content area."""
        if not message:
            return
        if message != self._toast_message:                       # new message -> drop in
            self._toast_message = message
            self._toast_at = self.fx.now
        drop = ease_out_back((self.fx.now - self._toast_at) / 0.35)
        label = self.fonts["small_bold"].render(message, True, config.COLORS["accent_dark"])
        width = min(660, label.get_width() + 56)
        rect = pygame.Rect(0, 0, width, 40)
        rect.center = (MAIN_WIDTH // 2, 152 - int((1.0 - drop) * 46))
        draw_rounded_rect(self.screen, config.COLORS["shadow"], rect.move(0, 4), 14)
        draw_rounded_rect(self.screen, config.COLORS["card"], rect, 14,
                          config.COLORS["border"], 2)
        pygame.draw.rect(self.screen, config.COLORS["accent"],
                         (rect.x + 8, rect.y + 9, 5, rect.height - 18),
                         border_radius=3)
        clipped = label.get_rect(center=(rect.centerx + 6, rect.centery))
        self.screen.blit(label, clipped)

    def draw_instruction_bar(self):
        """Compact bottom bar with the gesture legend."""
        bar = pygame.Rect(0, config.CONTENT_BOTTOM, MAIN_WIDTH, config.HINT_HEIGHT)
        pygame.draw.rect(self.screen, config.COLORS["card"], bar)
        pygame.draw.line(self.screen, config.COLORS["border"], (0, bar.y), (MAIN_WIDTH, bar.y), 2)

        margin, gap = 14, 8
        chip_width = (MAIN_WIDTH - 2 * margin - gap * (len(GESTURE_LEGEND) - 1)) // len(GESTURE_LEGEND)
        x = margin
        for gesture, action in GESTURE_LEGEND:
            chip = pygame.Rect(x, bar.y + 8, chip_width, config.HINT_HEIGHT - 16)
            draw_rounded_rect(self.screen, config.COLORS["background"], chip, 12)
            self.text(gesture, "tiny_bold", "accent_dark", (chip.centerx, chip.y + 12), "center")
            self.text(action, "tiny", "text", (chip.centerx, chip.y + 27), "center")
            x += chip_width + gap

    # ============================================================ sidebar
    def draw_sidebar(self, frame, landmarks, debug_rows, hold_progress,
                     ai_ready, hand_detected, status_message, finger_states=None,
                     face_state=None):
        """Compact AI camera panel on the right (technical detail only in debug mode)."""
        panel = pygame.Rect(PANEL_X, config.NAVBAR_HEIGHT, config.SIDEBAR_WIDTH,
                            config.WINDOW_HEIGHT - config.NAVBAR_HEIGHT)
        pygame.draw.rect(self.screen, config.COLORS["panel"], panel)
        left = panel.x + 20
        right = panel.right - 20

        # header: AI CAMERA + ready / standby
        self.text("AI CAMERA", "small_bold", "panel_text", (left, panel.y + 30))
        status_word = "Ready" if ai_ready else "Standby"
        self.text(status_word, "tiny_bold", "good" if ai_ready else "panel_muted",
                  (right, panel.y + 30), "right")
        if ai_ready:
            pygame.draw.circle(self.screen, config.COLORS["good"],
                               (right - 58, panel.y + 25), 5)

        preview_rect = pygame.Rect(left, panel.y + 52, *PREVIEW_SIZE)
        self._draw_camera_preview(frame, landmarks, preview_rect, finger_states)

        # friendly status line with a colored dot
        dot_color = (config.COLORS["good"] if hand_detected else
                     config.COLORS["muted"] if ai_ready else config.COLORS["bad"])
        pygame.draw.circle(self.screen, dot_color, (left + 7, preview_rect.bottom + 28), 6)
        self.text(status_message, "tiny_bold",
                  "good" if hand_detected else "panel_muted",
                  (left + 20, preview_rect.bottom + 28))
        if finger_states:
            count = sum(finger_states.values())
            self.text(f"{count}/5 fingers", "tiny_bold", "good",
                      (right, preview_rect.bottom + 28), "right")

        # one chip per finger: green = this finger is recognized as straight
        self._draw_finger_chips(finger_states, left, right, preview_rect.bottom + 46)

        # hold-gesture progress bar
        self.text("Hold gesture", "tiny", "panel_muted", (left, preview_rect.bottom + 90))
        bar = pygame.Rect(left, preview_rect.bottom + 108, right - left, 10)
        draw_rounded_rect(self.screen, config.COLORS["panel_alt"], bar, 5)
        if hold_progress > 0:
            draw_rounded_rect(self.screen, config.COLORS["accent"],
                              pygame.Rect(bar.x, bar.y, int(bar.width * hold_progress),
                                          bar.height), 5)

        # face gestures: smile -> discount, eyes closed -> back one step
        self._draw_face_chips(face_state, left, right, preview_rect.bottom + 132)

        # technical rows only when DEBUG_MODE is on
        if config.DEBUG_MODE:
            y = preview_rect.bottom + 190
            for label, value, is_good in debug_rows:
                self.text(label, "tiny", "panel_muted", (left, y))
                value_color = config.COLORS["good"] if is_good else config.COLORS["panel_muted"]
                surface = self.fonts["tiny_bold"].render(str(value), True, value_color)
                self.screen.blit(surface, surface.get_rect(midright=(right, y)))
                y += 24
        else:
            y = preview_rect.bottom + 190
            self.text("Gesture AI is active.", "tiny", "panel_muted", (left, y))
            self.text("Raise your open palm to start.", "tiny", "panel_muted", (left, y + 22))
            if not config.GESTURE_ONLY:
                self.text("Or use the keyboard.", "tiny", "panel_muted", (left, y + 44))

        # keyboard help (bottom of the panel)
        if config.GESTURE_ONLY or config.DEBUG_MODE:    # debug rows need the room
            return
        self.text("KEYBOARD", "tiny_bold", "panel_muted", (left, panel.bottom - 96))
        self.text("F1-F8 screens   F11 fullscreen", "tiny", "panel_muted",
                  (left, panel.bottom - 74))
        self.text("C clear   S summary   Q quit", "tiny", "panel_muted",
                  (left, panel.bottom - 54))
        self.text("ESC back   ENTER select", "tiny", "panel_muted",
                  (left, panel.bottom - 34))

    def _draw_finger_chips(self, finger_states, left, right, top):
        """Five small chips (Thumb..Pinky). A chip turns green when that finger is up."""
        gap = 4
        chip_width = (right - left - gap * (len(FINGER_TIPS) - 1)) // len(FINGER_TIPS)
        for i, (name, _tip, label) in enumerate(FINGER_TIPS):
            chip = pygame.Rect(left + i * (chip_width + gap), top, chip_width, 24)
            is_up = bool(finger_states and finger_states.get(name))
            draw_rounded_rect(self.screen,
                              config.COLORS["good"] if is_up else config.COLORS["panel_alt"],
                              chip, 8)
            self.text(label, "tiny_bold", "white" if is_up else "panel_muted",
                      chip.center, "center")

    def _draw_face_chips(self, face_state, left, right, top):
        """Two chips: SMILE (10% off) and EYES CLOSED (back). They fill while you hold."""
        state = face_state or {}
        gap = 6
        chip_width = (right - left - gap) // 2
        items = (("Smile: 10% off", "smiling", "smile_progress"),
                 ("Close eyes: Back", "eyes_closed", "blink_progress"))
        for i, (label, active_key, progress_key) in enumerate(items):
            chip = pygame.Rect(left + i * (chip_width + gap), top, chip_width, 26)
            draw_rounded_rect(self.screen, config.COLORS["panel_alt"], chip, 8)
            progress = state.get(progress_key, 0.0)
            if progress > 0:
                fill = pygame.Rect(chip.x, chip.y, max(10, int(chip.width * progress)),
                                   chip.height)
                draw_rounded_rect(self.screen, config.COLORS["good"], fill, 8)
            is_active = bool(state.get(active_key))
            self.text(label, "tiny_bold", "white" if is_active else "panel_muted",
                      chip.center, "center")
        if face_state is not None and not face_state.get("found"):
            self.text("Face not detected", "tiny", "panel_muted", (left, top + 34))

    def _draw_hand_overlay(self, landmarks, rect, finger_states):
        """Hand skeleton + fingertip dots (green = finger up, grey = finger down)."""
        def to_screen(point):
            return (rect.x + int(point[0] * rect.width), rect.y + int(point[1] * rect.height))

        for start, end in HAND_CONNECTIONS:
            pygame.draw.line(self.screen, config.COLORS["panel_text"],
                             to_screen(landmarks[start]), to_screen(landmarks[end]), 2)
        for name, tip, _label in FINGER_TIPS:
            is_up = bool(finger_states and finger_states.get(name))
            center = to_screen(landmarks[tip])
            pygame.draw.circle(self.screen, config.COLORS["good"] if is_up
                               else config.COLORS["panel_muted"], center, 6)
            pygame.draw.circle(self.screen, config.COLORS["white"], center, 6, 1)

    def _draw_camera_preview(self, frame, landmarks, rect, finger_states=None):
        """Live camera image with rounded corners, hand skeleton and fingertip dots."""
        draw_rounded_rect(self.screen, (25, 18, 14), rect, 14)
        if frame is None:
            self.text("No camera image", "tiny", "panel_muted", rect.center, "center")
            return
        try:
            small_frame = cv2.resize(frame, PREVIEW_SIZE)
            rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        except cv2.error:
            self.text("No camera image", "tiny", "panel_muted", rect.center, "center")
            return
        picture = pygame.image.frombuffer(rgb_frame.tobytes(), PREVIEW_SIZE, "RGB")

        # clip to rounded corners
        self.screen.set_clip(rect.inflate(-4, -4).move(0, 0))
        self.screen.blit(picture, rect)
        if landmarks:
            self._draw_hand_overlay(landmarks, rect, finger_states)
        if landmarks and config.DEBUG_MODE:
            for x, y in landmarks:          # 21 hand points - developers only
                pygame.draw.circle(self.screen, config.COLORS["accent"],
                                   (rect.x + int(x * rect.width),
                                    rect.y + int(y * rect.height)), 3)
        self.screen.set_clip(None)
        pygame.draw.rect(self.screen, config.COLORS["panel_alt"], rect, width=2, border_radius=14)

    # ============================================================ pointer
    def draw_pointer(self, position, progress):
        """A circle that follows the finger. The ring fills while you hold POINTING."""
        x, y = int(position[0]), int(position[1])
        self._pointer_trail.append((x, y))
        self._pointer_trail = self._pointer_trail[-9:]
        for i, (tx, ty) in enumerate(self._pointer_trail[:-1]):      # fading comet tail
            pygame.draw.circle(self.screen, config.COLORS["accent"], (tx, ty),
                               max(2, int(2 + 9 * i / len(self._pointer_trail))))
        pygame.draw.circle(self.screen, config.COLORS["white"], (x, y), 16)
        pygame.draw.circle(self.screen, config.COLORS["accent_dark"], (x, y), 12)
        if progress > 0:
            ring = pygame.Rect(x - 26, y - 26, 52, 52)
            pygame.draw.arc(self.screen, config.COLORS["accent"], ring,
                            math.pi / 2 - 2 * math.pi * progress, math.pi / 2, 6)