"""Effects - the "life" of the kiosk: smooth motion, confetti, sparkles, bubbles.

Nothing here knows about coffee or gestures. The Renderer asks for an
effect (for example `fx.confetti(center)`) and calls `fx.draw_particles()`
once per frame. Every effect is cheap enough for 30 FPS on a laptop.

    ease_out_back(t)      0 -> 1 with a small overshoot ("pop")
    Effects.smooth(...)   glide a value toward a target (hover lift)
    Effects.see(key)      seconds since a screen / page was entered
    Effects.confetti()    colourful paper burst
    Effects.sparkle()     little golden stars
    Effects.ambient()     soft bubbles floating up in the background
    Effects.pulse_ring()  expanding ring that says "do this next"
"""
import math
import random
import time

import pygame

from src import config

CONFETTI_COLORS = (
    (180, 112, 57),    # caramel
    (126, 77, 40),     # deep caramel
    (80, 155, 103),    # green
    (232, 180, 76),    # gold
    (214, 120, 100),   # warm red
    (120, 170, 210),   # soft blue
)
SPARKLE_COLORS = ((255, 214, 102), (255, 236, 170), (232, 180, 76))


def clamp01(value):
    return max(0.0, min(1.0, value))


def ease_out_cubic(t):
    t = clamp01(t)
    return 1.0 - (1.0 - t) ** 3


def ease_out_back(t):
    """Fast start, tiny overshoot, settle - the 'pop' used for cards and badges."""
    t = clamp01(t)
    c1 = 1.70158
    c3 = c1 + 1.0
    return 1.0 + c3 * (t - 1.0) ** 3 + c1 * (t - 1.0) ** 2


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "age", "life", "size", "color",
                 "shape", "angle", "spin", "gravity")

    def __init__(self, x, y, vx, vy, life, size, color, shape, spin=0.0, gravity=0.0):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.age, self.life, self.size, self.color = 0.0, life, size, color
        self.shape = shape                      # "paper" or "star"
        self.angle = random.uniform(0, math.tau)
        self.spin, self.gravity = spin, gravity


class Effects:
    """Owns the clock, the particles and the small animation helpers."""

    MAX_PARTICLES = 260

    def __init__(self):
        self.now = 0.0
        self.dt = 0.0
        self._clock_start = time.monotonic()
        self._last_tick = self._clock_start
        self.particles = []
        self._values = {}              # smooth() state
        self._entered = {}             # see() state: key -> time entered
        self._seen_this_frame = set()
        self._seen_last_frame = set()
        self._overlay_cache = {}

    # ============================================================ clock
    def tick(self):
        """Call once at the start of every frame."""
        real_now = time.monotonic()
        self.dt = min(0.1, real_now - self._last_tick)     # never jump after a lag spike
        self._last_tick = real_now
        self.now = real_now - self._clock_start

        # forget screens we left, so re-entering them animates again
        for key in list(self._entered):
            if key not in self._seen_this_frame and key not in self._seen_last_frame:
                del self._entered[key]
        self._seen_last_frame = self._seen_this_frame
        self._seen_this_frame = set()
        self._update_particles()

    def see(self, key):
        """Seconds since `key` (a screen / page) first appeared on screen."""
        self._seen_this_frame.add(key)
        if key not in self._entered:
            self._entered[key] = self.now
        return self.now - self._entered[key]

    def smooth(self, key, target, speed=12.0):
        """Glide a stored value toward `target` (exponential easing)."""
        value = self._values.get(key, target)
        value += (target - value) * min(1.0, speed * self.dt)
        self._values[key] = value
        return value

    def wave(self, speed=1.0, phase=0.0):
        """Smooth 0..1..0 loop (breathing / pulsing)."""
        return 0.5 + 0.5 * math.sin(self.now * speed * math.tau + phase)

    # ============================================================ spawning
    def confetti(self, center, count=70, power=420.0, upward=True):
        for _ in range(count):
            if len(self.particles) >= self.MAX_PARTICLES:
                break
            angle = random.uniform(-math.pi * 0.95, -math.pi * 0.05) if upward \
                else random.uniform(0, math.tau)
            speed = random.uniform(0.35, 1.0) * power
            self.particles.append(Particle(
                center[0], center[1], math.cos(angle) * speed, math.sin(angle) * speed,
                life=random.uniform(1.6, 2.6), size=random.uniform(6, 11),
                color=random.choice(CONFETTI_COLORS), shape="paper",
                spin=random.uniform(-9, 9), gravity=620.0))

    def confetti_rain(self, area, count=3):
        """A few pieces falling from the top of `area` (call every frame for a shower)."""
        for _ in range(count):
            if len(self.particles) >= self.MAX_PARTICLES:
                return
            self.particles.append(Particle(
                random.uniform(area.left, area.right), area.top - 10,
                random.uniform(-40, 40), random.uniform(60, 160),
                life=random.uniform(2.2, 3.2), size=random.uniform(6, 10),
                color=random.choice(CONFETTI_COLORS), shape="paper",
                spin=random.uniform(-6, 6), gravity=120.0))

    def sparkle(self, center, count=14, power=190.0):
        for _ in range(count):
            if len(self.particles) >= self.MAX_PARTICLES:
                break
            angle = random.uniform(0, math.tau)
            speed = random.uniform(0.3, 1.0) * power
            self.particles.append(Particle(
                center[0], center[1], math.cos(angle) * speed, math.sin(angle) * speed,
                life=random.uniform(0.5, 0.9), size=random.uniform(6, 12),
                color=random.choice(SPARKLE_COLORS), shape="star",
                spin=random.uniform(-4, 4), gravity=60.0))

    # ============================================================ particles
    def _update_particles(self):
        alive = []
        for p in self.particles:
            p.age += self.dt
            if p.age >= p.life:
                continue
            p.vx *= 1.0 - min(1.0, 1.4 * self.dt)          # air drag
            p.vy += p.gravity * self.dt
            p.vy *= 1.0 - min(1.0, 0.6 * self.dt)
            p.x += p.vx * self.dt
            p.y += p.vy * self.dt
            p.angle += p.spin * self.dt
            alive.append(p)
        self.particles = alive

    def draw_particles(self, surface, clip=None):
        if not self.particles:
            return
        old_clip = surface.get_clip()
        if clip is not None:
            surface.set_clip(clip)
        for p in self.particles:
            fade = 1.0 - clamp01((p.age / p.life - 0.7) / 0.3)     # shrink in the last 30%
            size = p.size * fade
            if size < 1:
                continue
            if p.shape == "star":
                self._draw_star(surface, p, size)
            else:
                self._draw_paper(surface, p, size)
        surface.set_clip(old_clip)

    @staticmethod
    def _draw_paper(surface, p, size):
        # a tumbling rectangle: its width shrinks and grows as it "flips"
        flip = abs(math.cos(p.angle * 1.7)) * 0.8 + 0.2
        w, h = size * flip, size * 0.55
        cos_a, sin_a = math.cos(p.angle), math.sin(p.angle)
        corners = []
        for dx, dy in ((-w, -h), (w, -h), (w, h), (-w, h)):
            corners.append((p.x + dx * cos_a - dy * sin_a, p.y + dx * sin_a + dy * cos_a))
        pygame.draw.polygon(surface, p.color, corners)

    @staticmethod
    def _draw_star(surface, p, size):
        points = []
        for i in range(8):                                  # 4-point star
            radius = size if i % 2 == 0 else size * 0.28
            a = p.angle + i * math.pi / 4
            points.append((p.x + math.cos(a) * radius, p.y + math.sin(a) * radius))
        pygame.draw.polygon(surface, p.color, points)

    # ============================================================ ambience
    def _overlay(self, size):
        key = tuple(size)
        surface = self._overlay_cache.get(key)
        if surface is None:
            surface = pygame.Surface(size, pygame.SRCALPHA)
            self._overlay_cache[key] = surface
        surface.fill((0, 0, 0, 0))
        return surface

    def ambient(self, surface, area, color=None, count=14):
        """Soft translucent bubbles drifting upward - cheap, always-on motion."""
        color = color or config.COLORS["accent"]
        overlay = self._overlay(area.size)
        for i in range(count):
            seed = i * 12.9898
            speed = 0.03 + 0.04 * ((math.sin(seed) + 1) / 2)          # screens per second
            progress = (self.now * speed + (i / count)) % 1.0
            x = (0.08 + 0.84 * ((math.sin(seed * 3.1) + 1) / 2)) * area.width
            x += math.sin(self.now * 0.8 + seed) * 18
            y = area.height * (1.05 - progress * 1.15)
            radius = 6 + 14 * ((math.sin(seed * 1.7) + 1) / 2)
            alpha = int(90 * math.sin(math.pi * progress))              # fade in and out
            pygame.draw.circle(overlay, (*color, alpha), (int(x), int(y)), int(radius))
        surface.blit(overlay, area.topleft)

    def pulse_ring(self, surface, rect, color=None, radius=22, period=1.6):
        """An expanding, fading outline around `rect` - 'this is the next thing to do'."""
        color = color or config.COLORS["accent"]
        phase = (self.now / period) % 1.0
        grow = int(26 * ease_out_cubic(phase))
        alpha = int(150 * (1.0 - phase))
        ring_rect = rect.inflate(grow * 2, grow * 2)
        overlay = self._overlay(ring_rect.inflate(8, 8).size)
        inner = overlay.get_rect().inflate(-8, -8)
        pygame.draw.rect(overlay, (*color, alpha), inner, width=4, border_radius=radius + grow)
        surface.blit(overlay, ring_rect.inflate(8, 8).topleft)
