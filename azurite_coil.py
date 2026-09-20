#!/usr/bin/env python3
"""Azurite Coil — neon rotating-needle gate-threader for ElbowOS."""
from __future__ import annotations

import math
import os
import random
import subprocess
import sys

import pygame

W, H = 1080, 1920
FPS = 30
TITLE = "AZURITE COIL"
HANDLE = "x.com/ElbowOS"
CX = W // 2
NEEDLE_Y = 1280
WELL_R = 390

INK = (4, 10, 22)
TEAL = (20, 210, 200)
AZU = (40, 120, 255)
COPPER = (255, 168, 64)
LIME = (170, 255, 90)
CREAM = (230, 248, 255)
MAG = (210, 70, 255)
NAVY = (8, 28, 58)


def lerp(a, b, t):
    return a + (b - a) * t


class Gate:
    def __init__(self, y: float, gap: float, span: float, spin: float, speed: float):
        self.y = y
        self.gap = gap  # centre of opening, radians
        self.span = span  # half-width of opening
        self.spin = spin
        self.speed = speed
        self.alive = True
        self.scored = False
        self.flash = 0.0
        self.missed = False
        self.r = WELL_R

    def update(self, dt: float):
        self.y += self.speed * dt
        self.gap = (self.gap + self.spin * dt) % (math.pi * 2)
        if self.flash:
            self.flash = max(0.0, self.flash - dt * 5)
        if self.y > NEEDLE_Y + 160:
            self.alive = False


class Game:
    def __init__(self, record: bool):
        self.record = record
        self.surf = pygame.Surface((W, H))
        self.clock = pygame.time.Clock()
        self.font_lg = pygame.font.Font(None, 86)
        self.font_md = pygame.font.Font(None, 54)
        self.font_sm = pygame.font.Font(None, 40)
        self.angle = 0.0
        self.omega = 0.0
        self.gates: list[Gate] = []
        self.score = 0
        self.combo = 0
        self.best = 0
        self.t = 0.0
        self.spawn_acc = 0.35
        self.sparks: list[list[float]] = []
        self.judges: list[tuple[str, float]] = []
        self.shake = 0.0
        self.running = True
        self.screen = None
        if not record:
            self.screen = pygame.display.set_mode((W, H))
            pygame.display.set_caption(TITLE)

    def spawn(self):
        span = random.uniform(0.38, 0.55)
        spin = random.choice((-1.4, -0.9, 0.9, 1.4, 1.8))
        speed = 240 + min(220, self.t * 9)
        gap = random.uniform(0, math.pi * 2)
        self.gates.append(Gate(-80, gap, span, spin, speed))

    def thread_check(self, g: Gate):
        if g.scored or g.missed:
            return
        if abs(g.y - NEEDLE_Y) > 28:
            return
        # three prongs at angle, angle+2pi/3, angle+4pi/3 — score if ANY prong in gap
        ok = False
        best_d = 99.0
        for k in range(3):
            a = (self.angle + k * 2 * math.pi / 3) % (math.pi * 2)
            d = abs((a - g.gap + math.pi) % (math.pi * 2) - math.pi)
            best_d = min(best_d, d)
            if d <= g.span:
                ok = True
        if ok:
            g.scored = True
            g.flash = 1.0
            tag = "PERFECT" if best_d < g.span * 0.35 else "THREAD"
            pts = 280 if tag == "PERFECT" else 140
            self.combo += 1
            self.best = max(self.best, self.combo)
            self.score += pts + self.combo * 12
            self.judges.append((tag, 0.8))
            col = COPPER if tag == "PERFECT" else TEAL
            for _ in range(14):
                ang = random.uniform(0, 6.28)
                self.sparks.append(
                    [CX, NEEDLE_Y, math.cos(ang) * 280, math.sin(ang) * 280, 0.45, *col]
                )
        else:
            g.missed = True
            self.combo = 0
            self.shake = 0.35
            self.judges.append(("CLANG", 0.7))

    def autoplay(self):
        # steer the nearest approaching gate's gap onto a prong
        upcoming = [g for g in self.gates if not g.scored and not g.missed and g.y < NEEDLE_Y + 10]
        if not upcoming:
            self.omega *= 0.9
            return
        g = max(upcoming, key=lambda x: x.y)
        target = g.gap
        # pick nearest prong offset
        best_off, best_d = 0, 99.0
        for k in range(3):
            a = (self.angle + k * 2 * math.pi / 3) % (math.pi * 2)
            d = (target - a + math.pi) % (math.pi * 2) - math.pi
            if abs(d) < best_d:
                best_d, best_off = abs(d), d
        self.omega = max(-4.6, min(4.6, best_off * 7.5))

    def update(self, dt: float):
        self.t += dt
        self.spawn_acc += dt
        gap = max(0.72, 1.15 - self.t * 0.018)
        if self.spawn_acc >= gap:
            self.spawn_acc = 0.0
            self.spawn()
        if self.record:
            self.autoplay()
        else:
            keys = pygame.key.get_pressed()
            steer = 0.0
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                steer -= 1.0
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                steer += 1.0
            self.omega = lerp(self.omega, steer * 4.2, min(1.0, dt * 8))
        self.angle = (self.angle + self.omega * dt) % (math.pi * 2)
        for g in self.gates:
            g.update(dt)
            self.thread_check(g)
        self.gates = [g for g in self.gates if g.alive or g.flash > 0]
        self.judges = [(s, life - dt) for s, life in self.judges if life - dt > 0]
        nxt = []
        for sp in self.sparks:
            sp[0] += sp[2] * dt
            sp[1] += sp[3] * dt
            sp[4] -= dt
            if sp[4] > 0:
                nxt.append(sp)
        self.sparks = nxt
        self.shake = max(0.0, self.shake - dt)

    def draw_bg(self, s: pygame.Surface):
        s.fill(INK)
        for i in range(22):
            y = (i * 110 + int(self.t * 55)) % (H + 110) - 55
            pygame.draw.line(s, (10, 28, 48), (0, y), (W, y), 2)
        pygame.draw.rect(s, NAVY, (0, 0, 56, H))
        pygame.draw.rect(s, NAVY, (W - 56, 0, 56, H))
        pygame.draw.rect(s, TEAL, (50, 0, 7, H))
        pygame.draw.rect(s, COPPER, (W - 57, 0, 7, H))
        rng = random.Random(11)
        for i in range(46):
            mx = rng.randint(80, W - 80)
            my = (rng.randint(0, H) + int(self.t * (28 + i % 24))) % H
            pygame.draw.circle(s, (18, 50, 90), (mx, my), 2 + i % 3)
        # well halo
        pygame.draw.circle(s, (12, 36, 70), (CX, NEEDLE_Y), WELL_R + 28, 10)
        pygame.draw.circle(s, AZU, (CX, NEEDLE_Y), WELL_R + 18, 3)

    def draw_gate(self, s: pygame.Surface, g: Gate):
        col = COPPER if g.flash > 0.2 else (MAG if g.missed else TEAL)
        if g.flash:
            col = (
                int(lerp(col[0], 255, g.flash)),
                int(lerp(col[1], 255, g.flash)),
                int(lerp(col[2], 220, g.flash)),
            )
        # ring as many short arcs, skip the gap
        steps = 56
        pts_out, pts_in = [], []
        for i in range(steps + 1):
            a = i / steps * math.pi * 2
            d = abs((a - g.gap + math.pi) % (math.pi * 2) - math.pi)
            if d < g.span:
                if pts_out:
                    if len(pts_out) > 1:
                        pygame.draw.lines(s, col, False, pts_out, 10)
                        pygame.draw.lines(s, CREAM, False, pts_in, 3)
                    pts_out, pts_in = [], []
                continue
            ox = CX + int(math.cos(a) * g.r)
            oy = int(g.y + math.sin(a) * 42)
            ix = CX + int(math.cos(a) * (g.r - 22))
            iy = int(g.y + math.sin(a) * 32)
            pts_out.append((ox, oy))
            pts_in.append((ix, iy))
        if len(pts_out) > 1:
            pygame.draw.lines(s, col, False, pts_out, 10)
            pygame.draw.lines(s, CREAM, False, pts_in, 3)
        # gap markers
        for sign in (-1, 1):
            a = g.gap + sign * g.span
            x = CX + int(math.cos(a) * g.r)
            y = int(g.y + math.sin(a) * 42)
            pygame.draw.circle(s, COPPER, (x, y), 9)

    def draw_coil(self, s: pygame.Surface):
        # hub
        pygame.draw.circle(s, NAVY, (CX, NEEDLE_Y), 54)
        pygame.draw.circle(s, AZU, (CX, NEEDLE_Y), 54, 5)
        pygame.draw.circle(s, TEAL, (CX, NEEDLE_Y), 22)
        for k in range(3):
            a = self.angle + k * 2 * math.pi / 3
            x2 = CX + int(math.cos(a) * (WELL_R - 8))
            y2 = NEEDLE_Y + int(math.sin(a) * 18)
            pygame.draw.line(s, TEAL, (CX, NEEDLE_Y), (x2, y2), 8)
            pygame.draw.circle(s, COPPER, (x2, y2), 16)
            pygame.draw.circle(s, CREAM, (x2, y2), 7)

    def draw(self, s: pygame.Surface):
        ox = int(math.sin(self.t * 40) * 10 * self.shake)
        self.draw_bg(s)
        for g in sorted(self.gates, key=lambda z: z.y):
            self.draw_gate(s, g)
        self.draw_coil(s)
        for sp in self.sparks:
            pygame.draw.circle(s, (int(sp[5]), int(sp[6]), int(sp[7])), (int(sp[0]), int(sp[1])), 6)
        title = self.font_lg.render(TITLE, True, COPPER)
        s.blit(title, title.get_rect(center=(W // 2 + ox, 72)))
        handle = self.font_sm.render(HANDLE, True, TEAL)
        s.blit(handle, handle.get_rect(center=(W // 2, 128)))
        sc = self.font_md.render(f"SCORE  {self.score}", True, CREAM)
        s.blit(sc, (90, 168))
        cb = self.font_md.render(f"COMBO  {self.combo}   BEST {self.best}", True, AZU)
        s.blit(cb, (90, 214))
        for tag, life in self.judges:
            col = COPPER if tag == "PERFECT" else (TEAL if tag == "THREAD" else MAG)
            img = self.font_md.render(tag, True, col)
            s.blit(img, img.get_rect(center=(CX, NEEDLE_Y - 120 - int((0.8 - life) * 50))))
        hint = self.font_sm.render("A / D  —  rotate the coil through the gap", True, (140, 190, 210))
        s.blit(hint, hint.get_rect(center=(W // 2, H - 48)))

    def handle(self, ev):
        if ev.type == pygame.QUIT:
            self.running = False
        elif ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                self.running = False
            elif ev.key == pygame.K_r:
                rec = self.record
                self.__init__(rec)

    def play(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            for ev in pygame.event.get():
                self.handle(ev)
            self.update(dt)
            self.draw(self.surf)
            self.screen.blit(self.surf, (0, 0))
            pygame.display.flip()

    def record_mp4(self, path: str):
        cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "20", "-preset", "fast", "-movflags", "+faststart", path,
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        frames = FPS * 15
        for i in range(frames):
            self.update(1.0 / FPS)
            self.draw(self.surf)
            proc.stdin.write(pygame.image.tostring(self.surf, "RGB"))
            if i % 30 == 0:
                print(f"frame {i}/{frames}", flush=True)
        proc.stdin.close()
        rc = proc.wait()
        if rc != 0:
            raise SystemExit(f"ffmpeg failed: {rc}")
        print("wrote", path)


def main():
    record = "--record" in sys.argv or os.environ.get("ELBOWOS_RECORD") == "1"
    if record:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.font.init()
    g = Game(record)
    if record:
        g.record_mp4("/home/workdir/artifacts/azurite_coil_ElbowOS.mp4")
    else:
        g.play()
    pygame.quit()


if __name__ == "__main__":
    main()
