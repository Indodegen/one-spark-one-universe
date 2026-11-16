#!/usr/bin/env python3
"""One Spark, One Universe — entry for make.fun ai-excited-01 (v6).

A single matchstick is struck diagonally across a deep indigo night.
The stick itself burns, embers streaming off its edge; where the match
head burns, the flame sweeps up in a great tongue with a clear edge
and breaks apart into bright stars that stream into a swirling
teal-violet galaxy — a whole universe held by one small spark. Flame
and galaxy meet but stay two shapes, a dark crescent between them.
Light rays burst from the junction; a comet streaks the upper sky.
One idea, one diagonal, one burst of awe across the whole frame.

Standard library only. Deterministic: every random choice comes from a
fixed seed, so two runs write byte-identical files.

Writes entry.png (1024x1024) into $MAKEFUN_OUTPUT_DIR (default /output).
"""

import math
import os
import random
import struct
import zlib

W = 1024
H = 1024
SEED = 20261116

# ---------------------------------------------------------------- palette
# deep indigo night (deeper than v3)
BG_TL = (5, 7, 24)         # top-left, darkest
BG_BR = (18, 25, 66)       # bottom-right, slightly lighter
VIGNETTE = 0.42            # edge darkening strength
# flame (hotter than v3)
FLAME_OUTER = (255, 106, 0)
FLAME_MID = (255, 179, 71)
FLAME_CORE = (255, 242, 176)
FLAME_HOT = (255, 250, 235)
EMBER = (255, 90, 31)
# galaxy (more vivid teal + violet)
TEAL = (45, 226, 197)
CYAN = (25, 184, 216)
VIOLET = (150, 90, 255)
GALAXY_CORE = (190, 250, 240)
# match wood
WOOD_TAIL = (150, 96, 50)
WOOD_HEAD = (214, 154, 88)
WOOD_LIGHT = (233, 178, 110)
WOOD_DARK = (104, 64, 32)
CHAR = (46, 20, 13)

# ---------------------------------------------------------------- geometry
# matchstick axis: tail (bottom-left) -> head (upper-right)
TAIL = (150.0, 880.0)
HEAD = (640.0, 400.0)
HALF_W = 15.0
# galaxy centre, just beyond the match head along the same diagonal
GALAXY = (775.0, 255.0)
# glow centres
GLOW_FLAME = (660.0, 385.0)
GLOW_GALAXY = (775.0, 255.0)
# firelight along the matchstick, so the lower half is lit too
GLOW_MATCH = (400.0, 640.0)
# light-burst junction: where flame tip meets the galaxy
JUNCTION = (738.0, 250.0)


# ---------------------------------------------------------------- buffer
buf = bytearray(W * H * 3)


def _idx(x, y):
    return (y * W + x) * 3


def blend_alpha(x, y, r, g, b, a):
    """Source-over blend of one pixel; a in 0..1."""
    if x < 0 or x >= W or y < 0 or y >= H or a <= 0.0:
        return
    i = _idx(x, y)
    ia = 1.0 - a
    buf[i] = int(r * a + buf[i] * ia + 0.5)
    buf[i + 1] = int(g * a + buf[i + 1] * ia + 0.5)
    buf[i + 2] = int(b * a + buf[i + 2] * ia + 0.5)


def blend_add(x, y, r, g, b, a):
    """Additive blend of one pixel; a in 0..1."""
    if x < 0 or x >= W or y < 0 or y >= H or a <= 0.0:
        return
    i = _idx(x, y)
    buf[i] = min(255, int(buf[i] + r * a + 0.5))
    buf[i + 1] = min(255, int(buf[i + 1] + g * a + 0.5))
    buf[i + 2] = min(255, int(buf[i + 2] + b * a + 0.5))


def soft_disc(cx, cy, rad, rgb, alpha, additive=False, power=2.0):
    """Soft-edged disc with quadratic falloff."""
    if rad <= 0:
        return
    blend = blend_add if additive else blend_alpha
    r, g, b = rgb
    x0 = max(0, int(cx - rad))
    x1 = min(W - 1, int(cx + rad) + 1)
    y0 = max(0, int(cy - rad))
    y1 = min(H - 1, int(cy + rad) + 1)
    rr = rad * rad
    for y in range(y0, y1 + 1):
        dy = y - cy
        for x in range(x0, x1 + 1):
            dx = x - cx
            d2 = dx * dx + dy * dy
            if d2 < rr:
                f = 1.0 - d2 / rr
                blend(x, y, r, g, b, alpha * (f ** power))


def disc(cx, cy, rad, rgb, alpha, additive=False):
    """Disc with a 1px soft edge."""
    soft_disc(cx, cy, rad, rgb, alpha, additive=additive, power=0.6)


def line(x0, y0, x1, y1, rgb, thick, alpha, additive=False):
    """Thick line drawn as a chain of soft discs."""
    dx = x1 - x0
    dy = y1 - y0
    length = math.hypot(dx, dy)
    if length == 0:
        return
    steps = max(2, int(length / max(1.0, thick * 0.6)))
    for i in range(steps + 1):
        t = i / steps
        soft_disc(x0 + dx * t, y0 + dy * t, thick * 0.5, rgb,
                  alpha, additive=additive, power=1.5)


def sparkle(cx, cy, size, rgb, alpha):
    """Four-point star sparkle."""
    line(cx - size, cy, cx + size, cy, rgb, 1.6, alpha, additive=True)
    line(cx, cy - size, cx, cy + size, rgb, 1.6, alpha, additive=True)
    disc(cx, cy, 2.2, (255, 255, 255), min(1.0, alpha + 0.3), additive=True)


def lerp_col(c1, c2, t):
    """Linear blend between two rgb colours."""
    return (int(c1[0] + (c2[0] - c1[0]) * t + 0.5),
            int(c1[1] + (c2[1] - c1[1]) * t + 0.5),
            int(c1[2] + (c2[2] - c1[2]) * t + 0.5))


def fill_poly(points, rgb, alpha=1.0):
    """Scanline fill of a polygon (list of (x, y)); crisp edges."""
    ys = [p[1] for p in points]
    y0, y1 = int(min(ys)), int(max(ys))
    n = len(points)
    r, g, b = rgb
    for y in range(y0, y1 + 1):
        xs = []
        for i in range(n):
            x_a, y_a = points[i]
            x_b, y_b = points[(i + 1) % n]
            if (y_a <= y < y_b) or (y_b <= y < y_a):
                t = (y - y_a) / (y_b - y_a)
                xs.append(x_a + t * (x_b - x_a))
        if len(xs) < 2:
            continue
        xa, xb = min(xs), max(xs)
        for x in range(int(xa), int(xb) + 1):
            blend_alpha(x, y, r, g, b, alpha)


# ---------------------------------------------------------------- background
def paint_background():
    """Diagonal indigo gradient + vignette + two soft glows."""
    # gaussian falloff lookup tables, indexed by squared distance / 256
    def make_lut(sigma):
        lut = []
        step = 256.0
        d2 = 0.0
        inv = 1.0 / (2.0 * sigma * sigma)
        while d2 < 700.0 * 700.0:
            lut.append(math.exp(-d2 * inv))
            d2 += step
        return lut

    lut_flame = make_lut(280.0)
    lut_galaxy = make_lut(380.0)
    lut_match = make_lut(200.0)
    fx, fy = GLOW_FLAME
    gx, gy = GLOW_GALAXY
    mx, my = GLOW_MATCH
    cx, cy = W / 2.0, H / 2.0
    maxd = math.hypot(cx, cy)

    for y in range(H):
        dy_c = y - cy
        row = y * W * 3
        for x in range(W):
            # diagonal gradient, top-left dark -> bottom-right lighter
            t = (x + y) / (W + H)
            r = BG_TL[0] + (BG_BR[0] - BG_TL[0]) * t
            g = BG_TL[1] + (BG_BR[1] - BG_TL[1]) * t
            b = BG_TL[2] + (BG_BR[2] - BG_TL[2]) * t
            # vignette: darken toward the corners
            dx_c = x - cx
            d = math.hypot(dx_c, dy_c) / maxd
            if d > 0.55:
                v = 1.0 - VIGNETTE * ((d - 0.55) / 0.45) ** 2
                r *= v
                g *= v
                b *= v
            # warm glow around the flame
            d2 = (x - fx) * (x - fx) + (y - fy) * (y - fy)
            gf = lut_flame[min(len(lut_flame) - 1, int(d2 / 256.0))]
            if gf > 0.004:
                r += 120.0 * gf
                g += 48.0 * gf
                b += 6.0 * gf
            # cool teal glow around the galaxy
            d2 = (x - gx) * (x - gx) + (y - gy) * (y - gy)
            gg = lut_galaxy[min(len(lut_galaxy) - 1, int(d2 / 256.0))]
            if gg > 0.004:
                r += 8.0 * gg
                g += 74.0 * gg
                b += 82.0 * gg
            # warm firelight along the matchstick, lighting the lower half
            d2 = (x - mx) * (x - mx) + (y - my) * (y - my)
            gm = lut_match[min(len(lut_match) - 1, int(d2 / 256.0))]
            if gm > 0.004:
                r += 70.0 * gm
                g += 26.0 * gm
                b += 4.0 * gm
            buf[row] = min(255, int(r + 0.5))
            buf[row + 1] = min(255, int(g + 0.5))
            buf[row + 2] = min(255, int(b + 0.5))
            row += 3


# ---------------------------------------------------------------- star field
def paint_stars(rng):
    for _ in range(520):
        x = rng.uniform(0, W)
        y = rng.uniform(0, H)
        # keep the brightest area (galaxy core) from getting cluttered
        if math.hypot(x - GALAXY[0], y - GALAXY[1]) < 70:
            continue
        rad = rng.uniform(0.6, 1.8)
        a = rng.uniform(0.25, 0.95)
        c = rng.choice([(255, 255, 255), (255, 255, 255),
                        (205, 216, 255), (255, 230, 190),
                        (150, 240, 225), (200, 180, 255)])
        disc(x, y, rad, c, a, additive=True)
    for _ in range(14):
        x = rng.uniform(30, W - 30)
        y = rng.uniform(30, H - 30)
        if math.hypot(x - GALAXY[0], y - GALAXY[1]) < 120:
            continue
        sparkle(x, y, rng.uniform(5.0, 11.0), (255, 255, 255),
                rng.uniform(0.35, 0.6))


# ---------------------------------------------------------------- comet + left glow
def paint_comet(rng):
    """A comet streaking the upper-left sky, its tail pointing at the
    galaxy, plus a very faint violet-teal nebula breath in the empty
    left-middle so the frame breathes without a second subject."""
    # faint nebula breath, far left-middle (kept very subtle)
    soft_disc(230, 530, 190, VIOLET, 0.10, additive=True)
    soft_disc(230, 530, 130, TEAL, 0.09, additive=True)
    # comet: bezier from head (185,165) toward the galaxy
    hx0, hy0 = (185.0, 165.0)
    cx1, cy1 = (300.0, 185.0)
    hx1, hy1 = (430.0, 320.0)
    for i in range(30):
        t = i / 29.0
        x = (1 - t) ** 2 * hx0 + 2 * (1 - t) * t * cx1 + t * t * hx1
        y = (1 - t) ** 2 * hy0 + 2 * (1 - t) * t * cy1 + t * t * hy1
        col = lerp_col((255, 255, 255), TEAL, t)
        disc(x, y, 4.2 - 2.8 * t, col, 0.85 - 0.6 * t, additive=True)
    # comet head: glow + bright core + tiny sparkle
    soft_disc(hx0, hy0, 26, (200, 240, 255), 0.5, additive=True)
    disc(hx0, hy0, 5.0, (255, 255, 255), 0.95, additive=True)
    sparkle(hx0, hy0, 10.0, (220, 245, 255), 0.5)


# ---------------------------------------------------------------- galaxy
def paint_galaxy(rng):
    cx, cy = GALAXY
    # --- nebula glow: wide violet halo, teal mid, cyan heart ---
    soft_disc(cx, cy, 340, VIOLET, 0.11, additive=True)
    soft_disc(cx, cy, 260, (30, 180, 200), 0.12, additive=True)
    soft_disc(cx, cy, 180, (40, 210, 190), 0.14, additive=True)
    # --- glowing core, tamed so the spiral reads around it ---
    soft_disc(cx, cy, 62, (64, 220, 200), 0.28, additive=True)
    soft_disc(cx, cy, 36, GALAXY_CORE, 0.45, additive=True)
    disc(cx, cy, 13, (240, 255, 250), 0.90, additive=True)
    disc(cx, cy, 6, (255, 255, 255), 1.0, additive=True)

    # --- spiral arms with real body: a wide faint ribbon underneath,
    #     then a bright spine on top, so the galaxy reads as a mass,
    #     not a dotted arc ---
    rot = -0.55
    cr, sr = math.cos(rot), math.sin(rot)

    def arm_point(base, t):
        theta = base + t * 3.6
        rad = 26.0 + (t ** 1.6) * 330.0
        dx = rad * math.cos(theta)
        dy = rad * math.sin(theta) * 0.8
        return (cx + dx * cr - dy * sr, cy + dx * sr + dy * cr)

    for arm in range(2):
        base = arm * math.pi + 0.6
        # under-pass: the ribbon's body (wide, soft, teal -> violet)
        for i in range(170):
            t = i / 169.0
            x, y = arm_point(base, t)
            x += rng.uniform(-2.0, 2.0)
            y += rng.uniform(-2.0, 2.0)
            size = 18.0 * (1.0 - t * 0.50)
            col = lerp_col(TEAL, VIOLET, t)
            soft_disc(x, y, size, col, 0.36, additive=True, power=2.0)
        # spine: bright dots along the same curve (white -> teal -> cyan)
        for i in range(260):
            t = i / 259.0
            x, y = arm_point(base, t)
            x += rng.uniform(-3.5, 3.5)
            y += rng.uniform(-3.5, 3.5)
            size = 5.2 * (1.0 - t * 0.65) + rng.uniform(-0.8, 0.8)
            if size < 0.9:
                size = 0.9
            bright = 0.95 - t * 0.45
            col = rng.choice([TEAL, TEAL, CYAN, (255, 255, 255),
                              (125, 249, 232)])
            disc(x, y, size, col, bright, additive=True)
            if i % 9 == 0:
                sparkle(x, y, size + 4.0, (220, 255, 248), 0.35)
        # faint dust scattered along the arm
        for _ in range(120):
            t = rng.random()
            x, y = arm_point(base, t)
            x += rng.uniform(-16, 16)
            y += rng.uniform(-16, 16)
            disc(x, y, rng.uniform(0.7, 1.6), TEAL, 0.28, additive=True)


# ---------------------------------------------------------------- dark gap
def paint_gap():
    """A dark crescent between the flame tip and the galaxy core, so
    the two shapes read as two shapes meeting, not one white blob."""
    soft_disc(758, 252, 22, (6, 8, 26), 0.45)


# ---------------------------------------------------------------- matchstick
def paint_match():
    tx, ty = TAIL
    hx, hy = HEAD
    vx, vy = hx - tx, hy - ty
    length = math.hypot(vx, vy)
    ux, uy = vx / length, vy / length
    nx, ny = -uy, ux  # up-left normal
    hw = HALF_W
    # polygon corners: tail-left, head-left, head-right, tail-right
    corners = [
        (tx + nx * hw, ty + ny * hw),
        (hx + nx * hw, hy + ny * hw),
        (hx - nx * hw, hy - ny * hw),
        (tx - nx * hw, ty - ny * hw),
    ]
    # scanline fill with a wood gradient along the axis
    ys = sorted(set(int(c[1]) for c in corners))
    y0, y1 = min(ys), max(ys)
    for y in range(y0, y1 + 1):
        xs = []
        for i in range(4):
            x_a, y_a = corners[i]
            x_b, y_b = corners[(i + 1) % 4]
            if (y_a <= y < y_b) or (y_b <= y < y_a):
                t = (y - y_a) / (y_b - y_a)
                xs.append(x_a + t * (x_b - x_a))
        if len(xs) < 2:
            continue
        xa, xb = min(xs), max(xs)
        for x in range(int(xa), int(xb) + 1):
            s = ((x - tx) * ux + (y - ty) * uy) / length
            s = max(0.0, min(1.0, s))
            r = WOOD_TAIL[0] + (WOOD_HEAD[0] - WOOD_TAIL[0]) * s
            g = WOOD_TAIL[1] + (WOOD_HEAD[1] - WOOD_TAIL[1]) * s
            b = WOOD_TAIL[2] + (WOOD_HEAD[2] - WOOD_TAIL[2]) * s
            # cylindrical shading across the width
            off = ((x - tx) * nx + (y - ty) * ny) / hw  # -1..1
            if off > 0.25:
                f = (off - 0.25) / 0.75
                r = r + (WOOD_LIGHT[0] - r) * f * 0.7
                g = g + (WOOD_LIGHT[1] - g) * f * 0.7
                b = b + (WOOD_LIGHT[2] - b) * f * 0.7
            elif off < -0.25:
                f = (-off - 0.25) / 0.75
                r = r + (WOOD_DARK[0] - r) * f * 0.7
                g = g + (WOOD_DARK[1] - g) * f * 0.7
                b = b + (WOOD_DARK[2] - b) * f * 0.7
            i = _idx(x, y)
            buf[i] = int(r + 0.5)
            buf[i + 1] = int(g + 0.5)
            buf[i + 2] = int(b + 0.5)
    # rounded tail end
    disc(tx, ty, hw, WOOD_TAIL, 1.0)
    # wood grain: a few thin darker streaks along the axis
    for goff, ga in [(-6, 0.16), (0, 0.10), (6, 0.14)]:
        line(tx + nx * goff, ty + ny * goff,
             hx + nx * goff, hy + ny * goff,
             (90, 52, 24), 1.8, ga)
    # the stick itself burns: a glowing ember edge along its upper-left
    # edge, hotter toward the head, plus a faint firelight halo
    line(tx - nx * hw, ty - ny * hw, hx - nx * hw, hy - ny * hw,
         (255, 120, 40), 12.0, 0.10, additive=True)
    for i in range(14):
        t0 = i / 14.0
        t1 = (i + 1) / 14.0
        ex0 = tx + vx * t0 - nx * hw
        ey0 = ty + vy * t0 - ny * hw
        ex1 = tx + vx * t1 - nx * hw
        ey1 = ty + vy * t1 - ny * hw
        col = lerp_col((255, 110, 30), (255, 205, 110), t0)
        line(ex0, ey0, ex1, ey1, col, 1.6 + 3.2 * t0,
             0.25 + 0.45 * t0, additive=True)
    # charred head bulb
    disc(hx, hy, 32, CHAR, 1.0)
    disc(hx + 4, hy - 4, 23, (74, 32, 20), 0.9)
    soft_disc(hx + 8, hy - 8, 26, EMBER, 0.6, additive=True)
    # the head as a tiny glowing planet: halo + bright ring
    soft_disc(hx, hy, 48, EMBER, 0.45, additive=True)
    for k in range(64):
        ang = 2 * math.pi * k / 64.0
        disc(hx + math.cos(ang) * 34, hy + math.sin(ang) * 34, 2.0,
             (255, 222, 160), 0.7, additive=True)
    # bright strike point where flame meets the head
    soft_disc(hx + 10, hy - 12, 18, FLAME_CORE, 0.9, additive=True)


# ---------------------------------------------------------------- flame
def paint_flame():
    hx, hy = HEAD
    # one big sweeping tongue: the centreline is a smooth Catmull-Rom
    # spline through control points, sampled densely, so the tongue
    # reads as a genuinely curved, organic flame — no faceted edges.
    # Flicker is baked in as a smooth sinusoidal lateral wave.
    # the tongue stops short of the galaxy now, so the two shapes meet
    # but never fuse: a dark crescent (paint_gap) sits between them.
    ctrl = [(hx + 2, hy - 6), (hx + 0, hy - 32), (hx + 6, hy - 58),
            (hx + 16, hy - 84), (hx + 30, hy - 108), (hx + 48, hy - 130),
            (hx + 68, hy - 148), (hx + 82, hy - 156),
            (hx + 94, hy - 162)]
    ctrl_r = [68, 64, 60, 54, 48, 40, 32, 20, 8]

    def catmull(p0, p1, p2, p3, t):
        t2 = t * t
        t3 = t2 * t
        return (0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t +
                       (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 +
                       (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3),
                0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t +
                       (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 +
                       (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3))

    # sample the spline: 12 samples per segment
    samples = []
    for s in range(len(ctrl) - 1):
        p0 = ctrl[max(0, s - 1)]
        p1 = ctrl[s]
        p2 = ctrl[s + 1]
        p3 = ctrl[min(len(ctrl) - 1, s + 2)]
        for k in range(12):
            samples.append(catmull(p0, p1, p2, p3, k / 12.0))
    samples.append(ctrl[-1])
    # smooth radius profile along the samples (linear between controls)
    radii = []
    for i in range(len(samples)):
        u = i / (len(samples) - 1) * (len(ctrl) - 1)
        j = min(int(u), len(ctrl) - 2)
        f = u - j
        radii.append(ctrl_r[j] * (1 - f) + ctrl_r[j + 1] * f)
    # baked-in flicker: a smooth sinusoidal lateral wave along the
    # centreline, deterministic, so the tongue waves gently
    path = []
    for i, (px, py) in enumerate(samples):
        u = i / (len(samples) - 1)
        path.append((px + math.sin(u * 9.0) * 3.0,
                     py + math.cos(u * 7.0) * 1.8))
    # crisp tongue silhouette: a filled polygon along the path, so the
    # flame has a defined edge instead of dissolving into the galaxy
    left, right = [], []
    for i, ((px, py), rad) in enumerate(zip(path, radii)):
        if i == 0:
            tx_, ty_ = path[1][0] - px, path[1][1] - py
        elif i == len(path) - 1:
            tx_, ty_ = px - path[i - 1][0], py - path[i - 1][1]
        else:
            tx_, ty_ = (path[i + 1][0] - path[i - 1][0],
                        path[i + 1][1] - path[i - 1][1])
        tl = math.hypot(tx_, ty_)
        tx_, ty_ = tx_ / tl, ty_ / tl
        nx_, ny_ = -ty_, tx_
        left.append((px + nx_ * rad, py + ny_ * rad))
        right.append((px - nx_ * rad, py - ny_ * rad))
    fill_poly(left + right[::-1], FLAME_OUTER, 1.0)
    # discs subsampled: they overlap heavily, so every third sample
    # keeps the same smooth fill at a third of the cost
    for (px, py), rad in list(zip(path, radii))[::3]:
        soft_disc(px, py, rad, FLAME_OUTER, 0.65, additive=True)
        soft_disc(px, py, rad * 0.66, FLAME_MID, 0.65, additive=True)
        soft_disc(px, py, rad * 0.38, FLAME_CORE, 0.70, additive=True)
    # white-hot heart: one continuous streak up the tongue, not dots
    for i in range(6):
        (x0, y0) = path[i * 9]
        (x1, y1) = path[(i + 1) * 9]
        line(x0, y0, x1, y1, FLAME_HOT, 10.0 - i * 1.2, 0.75, additive=True)
    # red-orange depth at the base
    soft_disc(hx + 8, hy - 12, 32, (255, 77, 0), 0.5, additive=True)
    # side tongues for a licking, alive flame (flickering edges)
    for (px, py), rad in [((hx - 30, hy - 40), 24),
                          ((hx + 66, hy - 56), 20),
                          ((hx - 18, hy - 88), 16),
                          ((hx + 78, hy - 104), 14)]:
        soft_disc(px, py, rad, FLAME_OUTER, 0.45, additive=True)
        soft_disc(px, py, rad * 0.6, FLAME_MID, 0.55, additive=True)
    # white-hot heart at the base, bigger than v3
    soft_disc(hx + 12, hy - 18, 13, (255, 255, 240), 0.95, additive=True)



# ---------------------------------------------------------------- light beams
def paint_beams():
    """Rays bursting from the flame-galaxy junction: thin, tapered,
    warm near the centre fading to teal at the tips."""
    jx, jy = JUNCTION
    beams = [(-2.9, 320.0), (-2.5, 200.0), (-1.8, 260.0), (-1.1, 230.0),
             (-0.4, 190.0), (0.5, 150.0), (0.9, 130.0)]
    for ang, length in beams:
        dx, dy = math.cos(ang), math.sin(ang)
        for i in range(16):
            t = i / 15.0
            x = jx + dx * t * length
            y = jy + dy * t * length
            col = lerp_col((255, 225, 160), (110, 235, 225), t)
            soft_disc(x, y, 5.5 * (1.0 - t) + 0.8, col,
                      0.32 * (1.0 - t) ** 1.6, additive=True, power=2.0)
    # hot flash right at the junction, tamed so the spiral reads around it
    soft_disc(jx, jy, 15, (255, 245, 220), 0.32, additive=True)
    disc(jx, jy, 4, (255, 255, 250), 0.85, additive=True)


# ---------------------------------------------------------------- star stream
def paint_starstream(rng):
    """The flame tip fragmenting into bright stars that stream off
    into the galaxy's spiral: the scale twist made legible — one
    spark becomes stars becomes a universe."""
    # fragment cluster right at the flame tip — bigger, brighter
    tx, ty = (734.0, 238.0)
    for _ in range(10):
        x = tx + rng.uniform(-16, 16)
        y = ty + rng.uniform(-14, 14)
        col = rng.choice([(255, 255, 255), (255, 240, 200),
                          (255, 210, 120)])
        disc(x, y, rng.uniform(1.8, 3.6), col, 0.95, additive=True)
        if rng.random() < 0.7:
            sparkle(x, y, rng.uniform(6.0, 10.0), col, 0.5)
    # glowing trail arcing from the tip down into the lower spiral arm,
    # routed BELOW the dark gap so flame and galaxy stay two shapes
    cx0, cy0 = (734.0, 238.0)
    cx1, cy1 = (768.0, 292.0)
    cx2, cy2 = (800.0, 312.0)
    for i in range(14):
        t = i / 13.0
        x = (1 - t) ** 2 * cx0 + 2 * (1 - t) * t * cx1 + t * t * cx2
        y = (1 - t) ** 2 * cy0 + 2 * (1 - t) * t * cy1 + t * t * cy2
        col = lerp_col((255, 220, 140), TEAL, t)
        soft_disc(x, y, 9.0 - 4.0 * t, col, 0.20, additive=True, power=2.0)
    # the stars themselves, bigger and brighter than v5
    for i in range(36):
        t = i / 35.0
        x = (1 - t) ** 2 * cx0 + 2 * (1 - t) * t * cx1 + t * t * cx2
        y = (1 - t) ** 2 * cy0 + 2 * (1 - t) * t * cy1 + t * t * cy2
        x += rng.uniform(-3.5, 3.5)
        y += rng.uniform(-3.5, 3.5)
        col = lerp_col((255, 220, 140), TEAL, t)
        if rng.random() < 0.35:
            col = (255, 255, 255)
        size = 4.4 - 1.8 * t + rng.uniform(-0.6, 0.6)
        disc(x, y, max(1.4, size), col, 0.95, additive=True)
        if i % 3 == 0:
            sparkle(x, y, size + 5.0, col, 0.5)


# ---------------------------------------------------------------- sparks
def paint_sparks(rng):
    hx, hy = HEAD
    # upward fan, longer trails than v3
    for _ in range(18):
        ang = rng.uniform(-2.7, -0.15)
        ln = rng.uniform(30, 110)
        x0 = hx + rng.uniform(-8, 14)
        y0 = hy + rng.uniform(-14, 8)
        x1 = x0 + math.cos(ang) * ln
        y1 = y0 + math.sin(ang) * ln
        col = rng.choice([(255, 200, 90), (255, 240, 200),
                          (255, 255, 255)])
        line(x0, y0, x1, y1, col, rng.uniform(1.4, 2.6),
             rng.uniform(0.5, 0.9), additive=True)
        disc(x1, y1, rng.uniform(1.2, 2.4), col, 0.9, additive=True)
    # embers drifting down-left along the matchstick
    for _ in range(20):
        ang = rng.uniform(2.2, 2.9)
        ln = rng.uniform(20, 60)
        s = rng.uniform(0.15, 0.85)
        x0 = hx + (TAIL[0] - hx) * s + rng.uniform(-6, 6)
        y0 = hy + (TAIL[1] - hy) * s + rng.uniform(-6, 6)
        x1 = x0 + math.cos(ang) * ln
        y1 = y0 + math.sin(ang) * ln
        col = rng.choice([(255, 140, 40), (255, 190, 90),
                          (255, 220, 150)])
        line(x0, y0, x1, y1, col, rng.uniform(1.2, 2.2),
             rng.uniform(0.45, 0.75), additive=True)
        disc(x1, y1, rng.uniform(1.0, 2.2), col, 0.85, additive=True)
        if rng.random() < 0.25:
            sparkle(x1, y1, 5.0, col, 0.4)
    # teal sparks escaping the galaxy
    for _ in range(8):
        ang = rng.uniform(-2.9, -0.2)
        ln = rng.uniform(20, 60)
        x0 = GALAXY[0] + rng.uniform(-70, 70)
        y0 = GALAXY[1] + rng.uniform(-60, 60)
        x1 = x0 + math.cos(ang) * ln
        y1 = y0 + math.sin(ang) * ln
        col = rng.choice([TEAL, (125, 249, 232), (255, 255, 255)])
        line(x0, y0, x1, y1, col, rng.uniform(1.2, 2.0),
             rng.uniform(0.45, 0.75), additive=True)
        disc(x1, y1, rng.uniform(1.0, 2.0), col, 0.85, additive=True)


# ---------------------------------------------------------------- png
def _chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def write_png(path):
    """Encode the buffer as PNG with per-row filter choice (None vs Up)."""
    rows = []
    prev = bytearray(W * 3)
    for y in range(H):
        row = bytes(buf[y * W * 3:(y + 1) * W * 3])
        f0 = b"\x00" + row
        up = bytearray(W * 3 + 1)
        up[0] = 2
        for i in range(W * 3):
            up[i + 1] = (row[i] - prev[i]) & 0xFF
        c0 = len(zlib.compress(f0, 6))
        c2 = len(zlib.compress(bytes(up), 6))
        rows.append(f0 if c0 <= c2 else bytes(up))
        prev = bytearray(row)
    raw = b"".join(rows)
    comp = zlib.compress(raw, 9)
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", ihdr)
    png += _chunk(b"IDAT", comp)
    png += _chunk(b"IEND", b"")
    with open(path, "wb") as fh:
        fh.write(png)
    return len(png)


def render():
    rng = random.Random(SEED)
    paint_background()
    paint_stars(rng)
    paint_comet(rng)
    paint_galaxy(rng)
    paint_gap()
    paint_match()
    paint_flame()
    paint_beams()
    paint_starstream(rng)
    paint_sparks(rng)


def main():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(outdir, exist_ok=True)
    render()
    path = os.path.join(outdir, "entry.png")
    size = write_png(path)
    print("wrote %s (%dx%d, %d bytes)" % (path, W, H, size))


if __name__ == "__main__":
    main()
