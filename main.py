#!/usr/bin/env python3
"""Procedural 1024x1024 PNG for make.fun news-image-01.

"THE WORLD" -- a one-page newspaper front page summing up Friday
13 November 2026, drawn entirely in code from the day's reported
facts (gathered from BBC/Al Jazeera-linked briefings and news wires
on 13 Nov 2026):

  LEAD   Europe joins the next round of Ukraine peace talks; US
         envoys Kushner and Witkoff say so after meeting Putin in
         Moscow and Zelenskyy near Dublin; the war's biggest
         prisoner swap is being prepared.
  GULF   Iran says it struck a US radar site in Bahrain; tankers
         hit in the Strait of Hormuz.
  NVIDIA Jensen Huang resigns as chief executive; shares fall 16%;
         CFO Colette Kress named interim chief.
  MICROSOFT Outlook and Teams fail worldwide in a Microsoft 365
         outage.
  CRYPTO DOJ wins court approval to seize $1.2bn from the Binance
         hack blamed on North Korea's TraderTraitor unit; FBI says
         $400m was stolen through fake video calls.
  GAZA   Israeli strike on Khan Younis hospital kills six, a
         surgeon among them, at Nasser hospital.
  SPORT  Harry Kane's 126th cap sets England's appearance record;
         England beat Croatia to reach the Nations League QFs.
  ALSO   Record 483,200 US deportations in 2026; Pope Leo meets
         abuse survivors in Peru; Storm Charles hits Portugal;
         Democrat wins the Kansas governor race; Google unveils
         Gemini 4 "Hydrogen" for search.

Pure standard library (math, os, struct, zlib, pathlib). Fully
deterministic: the same bytes on every run. Renders at 2x
supersampling into a 2048x2048 RGB buffer, box-downsamples to
1024x1024, and writes the PNG with a hand-rolled encoder (filter
byte 0 per row, 8-bit colour type 2).
"""

import math
import os
import struct
import zlib
from pathlib import Path

# ---------------------------------------------------------------------------
# Canvas: design space is 1024x1024; the buffer is 2x supersampled.
# ---------------------------------------------------------------------------
W = 1024
S = 2
IW = W * S  # 2048

buf = bytearray(IW * IW * 3)

# Palette: newsprint.
PAPER = (247, 242, 231)
PAPER_DIM = (238, 231, 214)
INK = (17, 17, 17)
RED = (178, 32, 44)
BLUE = (29, 78, 137)
NAVY = (18, 44, 84)
GOLD = (201, 162, 39)
GREEN = (46, 125, 50)
TEAL = (14, 116, 144)
GREY = (110, 110, 104)
LIGHT_GREY = (214, 210, 198)
WHITE = (255, 255, 255)
SKY = (214, 232, 244)
SEA = (46, 111, 164)


def _clip(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def span(y, x0, x1, color):
    """Fill design-row y (in buffer rows) from x0 to x1 (buffer px)."""
    if y < 0 or y >= IW:
        return
    x0 = _clip(x0, 0, IW)
    x1 = _clip(x1, 0, IW)
    if x1 <= x0:
        return
    base = (y * IW + x0) * 3
    r, g, b = color
    for x in range(x0, x1):
        i = base + (x - x0) * 3
        buf[i] = r
        buf[i + 1] = g
        buf[i + 2] = b


def _ix(v):
    return int(round(v * S))


def fill_rect(x, y, w, h, color):
    x0, y0 = _ix(x), _ix(y)
    x1, y1 = _ix(x + w), _ix(y + h)
    for yy in range(y0, y1):
        span(yy, x0, x1, color)


def disc(cx, cy, r, color):
    cx, cy, r = _ix(cx), _ix(cy), _ix(r)
    r2 = r * r
    for yy in range(cy - r, cy + r + 1):
        dy = yy - cy
        dx = int(math.sqrt(max(0, r2 - dy * dy)))
        span(yy, cx - dx, cx + dx + 1, color)


def ellipse(cx, cy, rx, ry, color):
    cx, cy, rx, ry = _ix(cx), _ix(cy), _ix(rx), _ix(ry)
    for yy in range(cy - ry, cy + ry + 1):
        dy = (yy - cy) / max(1, ry)
        dx = int(rx * math.sqrt(max(0.0, 1.0 - dy * dy)))
        span(yy, cx - dx, cx + dx + 1, color)


def rrect(x, y, w, h, r, color):
    fill_rect(x + r, y, w - 2 * r, h, color)
    fill_rect(x, y + r, w, h - 2 * r, color)
    disc(x + r, y + r, r, color)
    disc(x + w - r, y + r, r, color)
    disc(x + r, y + h - r, r, color)
    disc(x + w - r, y + h - r, r, color)


def polygon(points, color):
    """Scanline-fill a polygon given in design coordinates."""
    pts = [(_ix(x), _ix(y)) for x, y in points]
    ys = [p[1] for p in pts]
    for yy in range(min(ys), max(ys) + 1):
        xs = []
        n = len(pts)
        for i in range(n):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % n]
            if (y0 <= yy < y1) or (y1 <= yy < y0):
                t = (yy - y0) / (y1 - y0)
                xs.append(int(x0 + t * (x1 - x0)))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            span(yy, xs[i], xs[i + 1] + 1, color)


def thick_line(x0, y0, x1, y1, width, color):
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy)
    if length == 0:
        disc(x0, y0, width / 2, color)
        return
    nx, ny = -dy / length * width / 2, dx / length * width / 2
    polygon([(x0 + nx, y0 + ny), (x1 + nx, y1 + ny),
             (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)], color)


def arc(cx, cy, r, a0, a1, width, color):
    steps = max(8, int(abs(a1 - a0) * r / 3))
    prev = None
    for i in range(steps + 1):
        a = a0 + (a1 - a0) * i / steps
        p = (cx + r * math.cos(a), cy + r * math.sin(a))
        if prev is not None:
            thick_line(prev[0], prev[1], p[0], p[1], width, color)
        prev = p


def star(cx, cy, r, color, points=8):
    pts = []
    for i in range(points * 2):
        ang = -math.pi / 2 + i * math.pi / points
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    polygon(pts, color)


def ring(cx, cy, r, width, color):
    steps = 64
    for i in range(steps):
        a0 = 2 * math.pi * i / steps
        a1 = 2 * math.pi * (i + 1) / steps
        thick_line(cx + r * math.cos(a0), cy + r * math.sin(a0),
                   cx + r * math.cos(a1), cy + r * math.sin(a1), width, color)


# ---------------------------------------------------------------------------
# PNG encoder: 8-bit RGB, filter 0 per row, zlib level 9.
# ---------------------------------------------------------------------------
def _chunk(kind, data):
    c = struct.pack(">I", len(data)) + kind + data
    return c + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def encode_png(rgb, w, h):
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        raw += rgb[y * w * 3:(y + 1) * w * 3]
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr)
            + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + _chunk(b"IEND", b""))


def downsample():
    out = bytearray(W * W * 3)
    for y in range(W):
        for x in range(W):
            sr = sg = sb = 0
            for dy in range(S):
                base = ((y * S + dy) * IW + x * S) * 3
                for dx in range(S):
                    i = base + dx * 3
                    sr += buf[i]
                    sg += buf[i + 1]
                    sb += buf[i + 2]
            o = (y * W + x) * 3
            out[o] = sr // (S * S)
            out[o + 1] = sg // (S * S)
            out[o + 2] = sb // (S * S)
    return out

# ---------------------------------------------------------------------------
# 5x7 bitmap font. 7 rows of 5 bits, '1' = filled.
# ---------------------------------------------------------------------------
FONT = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "G": ["01110", "10001", "10000", "10111", "10001", "10001", "01111"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["01110", "00100", "00100", "00100", "00100", "00100", "01110"],
    "J": ["00111", "00010", "00010", "00010", "00010", "10010", "01100"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "W": ["10001", "10001", "10001", "10101", "10101", "10101", "01010"],
    "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00110", "01000", "10000", "11111"],
    "3": ["11111", "00010", "00100", "00010", "00001", "10001", "01110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    "6": ["00110", "01000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00010", "01100"],
    " ": ["00000", "00000", "00000", "00000", "00000", "00000", "00000"],
    ".": ["00000", "00000", "00000", "00000", "00000", "01100", "01100"],
    ",": ["00000", "00000", "00000", "00000", "01100", "00100", "01000"],
    ":": ["00000", "01100", "01100", "00000", "01100", "01100", "00000"],
    ";": ["00000", "01100", "01100", "00000", "01100", "00100", "01000"],
    "!": ["00100", "00100", "00100", "00100", "00100", "00000", "00100"],
    "?": ["01110", "10001", "00001", "00110", "00100", "00000", "00100"],
    "'": ["00100", "00100", "01000", "00000", "00000", "00000", "00000"],
    "-": ["00000", "00000", "00000", "01110", "00000", "00000", "00000"],
    "$": ["00100", "01111", "10100", "01110", "00101", "11110", "00100"],
    "%": ["11001", "11010", "00010", "00100", "01000", "01011", "10011"],
    "(": ["00010", "00100", "01000", "01000", "01000", "00100", "00010"],
    ")": ["01000", "00100", "00010", "00010", "00010", "00100", "01000"],
    "/": ["00001", "00010", "00010", "00100", "01000", "01000", "10000"],
    "+": ["00000", "00100", "00100", "11111", "00100", "00100", "00000"],
    "=": ["00000", "00000", "11111", "00000", "11111", "00000", "00000"],
    "&": ["01100", "10010", "10100", "01000", "10101", "10010", "01101"],
    '"': ["01010", "01010", "00000", "00000", "00000", "00000", "00000"],
    "#": ["01010", "01010", "11111", "01010", "11111", "01010", "01010"],
    "*": ["00000", "10101", "01110", "10101", "00000", "00000", "00000"],
    "•": ["00000", "00000", "01110", "01110", "01110", "00000", "00000"],
}


def draw_text(text, x, y, scale, color):
    """Draw text; one font pixel is a scale x scale design-px block."""
    cx = x
    for ch in text:
        glyph = FONT.get(ch)
        if glyph:
            for r, row in enumerate(glyph):
                for c, bit in enumerate(row):
                    if bit == "1":
                        fill_rect(cx + c * scale, y + r * scale, scale, scale, color)
        cx += 6 * scale


def text_width(text, scale):
    return len(text) * 6 * scale - scale


def draw_text_centered(text, y, scale, color, cx=W // 2):
    draw_text(text, cx - text_width(text, scale) // 2, y, scale, color)


def wrap_text(text, scale, max_w):
    """Greedy word wrap; returns a list of lines fitting max_w design px."""
    lines, cur = [], ""
    for word in text.split(" "):
        trial = word if not cur else cur + " " + word
        if text_width(trial, scale) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_block(lines, x, y, scale, color, leading=None, align="left", width=None):
    """Draw lines of text; align left/center within width (default: from x)."""
    lh = leading if leading is not None else 9 * scale
    for i, line in enumerate(lines):
        if align == "center":
            lx = x + (width - text_width(line, scale)) // 2 if width else x
        else:
            lx = x
        draw_text(line, lx, y + i * lh, scale, color)
    return y + len(lines) * lh

# ---------------------------------------------------------------------------
# Pictograms, drawn in a box of roughly 150x110 design px centred at (cx, cy).
# ---------------------------------------------------------------------------

def pic_tanker(cx, cy):
    # Explosion starburst above the ship.
    star(cx, cy - 42, 26, GOLD)
    star(cx, cy - 42, 14, RED)
    # Hull.
    polygon([(cx - 62, cy - 6), (cx + 62, cy - 6), (cx + 48, cy + 22),
             (cx - 48, cy + 22)], (122, 44, 34))
    fill_rect(cx - 62, cy - 6, 124, 5, (90, 30, 24))
    # Containers.
    fill_rect(cx - 52, cy - 34, 26, 28, BLUE)
    fill_rect(cx - 22, cy - 34, 26, 28, GOLD)
    fill_rect(cx + 8, cy - 34, 26, 28, TEAL)
    # Bridge.
    fill_rect(cx + 38, cy - 40, 20, 34, WHITE)
    fill_rect(cx + 42, cy - 36, 12, 5, INK)
    fill_rect(cx + 42, cy - 27, 12, 5, INK)
    # Smoke puffs from the bridge.
    disc(cx + 46, cy - 46, 4, GREY)
    disc(cx + 52, cy - 54, 5, GREY)
    disc(cx + 58, cy - 62, 6, GREY)
    # Waves.
    for i, wx in enumerate(range(cx - 70, cx + 71, 24)):
        arc(wx + 12, cy + 30, 11, math.pi, 2 * math.pi, 4, SEA)


def pic_chip(cx, cy):
    # Pins.
    for i in range(4):
        px = cx - 30 + i * 20
        fill_rect(px, cy - 52, 8, 14, INK)
        fill_rect(px, cy + 38, 8, 14, INK)
    for i in range(4):
        py = cy - 30 + i * 20
        fill_rect(cx - 52, py, 14, 8, INK)
        fill_rect(cx + 38, py, 14, 8, INK)
    # Body + die.
    rrect(cx - 40, cy - 40, 80, 80, 6, INK)
    rrect(cx - 26, cy - 26, 52, 52, 4, (42, 42, 48))
    fill_rect(cx - 26, cy - 4, 52, 3, GOLD)
    fill_rect(cx - 4, cy - 26, 3, 52, GOLD)
    disc(cx, cy, 8, GOLD)
    disc(cx, cy, 4, RED)


def pic_envelope(cx, cy):
    rrect(cx - 58, cy - 38, 116, 76, 6, WHITE)
    fill_rect(cx - 58, cy - 38, 116, 3, INK)
    fill_rect(cx - 58, cy + 35, 116, 3, INK)
    fill_rect(cx - 58, cy - 38, 3, 76, INK)
    fill_rect(cx + 55, cy - 38, 3, 76, INK)
    thick_line(cx - 58, cy - 38, cx, cy + 2, 4, INK)
    thick_line(cx + 58, cy - 38, cx, cy + 2, 4, INK)
    # Red X over it: the outage.
    thick_line(cx - 34, cy - 24, cx + 34, cy + 24, 9, RED)
    thick_line(cx + 34, cy - 24, cx - 34, cy + 24, 9, RED)


def pic_padlock(cx, cy):
    arc(cx, cy - 12, 26, math.pi, 2 * math.pi, 10, GOLD)
    rrect(cx - 38, cy - 14, 76, 56, 6, INK)
    rrect(cx - 32, cy - 8, 64, 44, 4, (42, 42, 48))
    disc(cx, cy + 6, 9, GOLD)
    fill_rect(cx - 3, cy + 6, 6, 14, GOLD)


def pic_hospital(cx, cy):
    fill_rect(cx - 46, cy - 40, 92, 84, WHITE)
    fill_rect(cx - 46, cy - 40, 92, 4, INK)
    fill_rect(cx - 46, cy + 40, 92, 4, INK)
    fill_rect(cx - 46, cy - 40, 4, 84, INK)
    fill_rect(cx + 42, cy - 40, 4, 84, INK)
    # Red cross.
    fill_rect(cx - 9, cy - 32, 18, 46, RED)
    fill_rect(cx - 21, cy - 20, 42, 18, RED)
    # Windows.
    for wx in (cx - 36, cx - 12, cx + 14):
        fill_rect(wx, cy + 12, 16, 14, SKY)
    # Ground line.
    fill_rect(cx - 56, cy + 46, 112, 4, INK)


def pic_football(cx, cy):
    disc(cx, cy, 42, WHITE)
    ring(cx, cy, 42, 4, INK)
    polygon([(cx, cy - 14), (cx + 13, cy - 4), (cx + 8, cy + 12),
             (cx - 8, cy + 12), (cx - 13, cy - 4)], INK)
    for ang in (-90, -18, 54, 126, 198):
        a = math.radians(ang)
        thick_line(cx + 15 * math.cos(a), cy + 15 * math.sin(a),
                   cx + 38 * math.cos(a), cy + 38 * math.sin(a), 3, INK)


def pic_flags(cx, cy):
    # Two crossed flagpoles: EU (left) and Ukraine (right).
    thick_line(cx - 52, cy + 44, cx - 8, cy - 44, 5, INK)
    thick_line(cx + 52, cy + 44, cx + 8, cy - 44, 5, INK)
    # EU flag: blue field, ring of gold stars.
    polygon([(cx - 6, cy - 44), (cx - 52, cy - 30), (cx - 52, cy - 2),
             (cx - 6, cy - 16)], BLUE)
    for i in range(6):
        a = -math.pi / 2 + i * math.pi / 3
        disc(cx - 29 + 11 * math.cos(a), cy - 23 + 8 * math.sin(a), 2, GOLD)
    # Ukraine flag: blue over yellow.
    polygon([(cx + 6, cy - 44), (cx + 52, cy - 30), (cx + 52, cy - 16),
             (cx + 6, cy - 30)], (0, 87, 184))
    polygon([(cx + 6, cy - 30), (cx + 52, cy - 16), (cx + 52, cy - 2),
             (cx + 6, cy - 16)], (255, 213, 0))
    # Olive branch below.
    thick_line(cx - 34, cy + 52, cx + 34, cy + 52, 4, GREEN)
    for lx in (-24, -8, 8, 24):
        ellipse(lx + cx, cy + 46, 9, 4, GREEN)

# ---------------------------------------------------------------------------
# Layout: a one-page newspaper front page.
# ---------------------------------------------------------------------------

def rule(x0, x1, y, h, color=INK):
    fill_rect(x0, y, x1 - x0, h, color)


def draw_panel(px, py, kicker, color, pic_fn, head1, head2, cap1, cap2):
    w, h = 314, 244
    cx = px + w // 2
    # Border.
    fill_rect(px, py, w, 2, INK)
    fill_rect(px, py + h - 2, w, 2, INK)
    fill_rect(px, py, 2, h, INK)
    fill_rect(px + w - 2, py, 2, h, INK)
    # Kicker band.
    fill_rect(px + 2, py + 2, w - 4, 30, color)
    draw_text_centered(kicker, py + 10, 2, WHITE, cx)
    # Pictogram.
    pic_fn(cx, py + 86)
    # Headline, two lines.
    draw_text_centered(head1, py + 142, 3, INK, cx)
    draw_text_centered(head2, py + 169, 3, INK, cx)
    # Caption, two lines.
    draw_text_centered(cap1, py + 202, 2, INK, cx)
    draw_text_centered(cap2, py + 220, 2, INK, cx)


def build():
    fill_rect(0, 0, W, W, PAPER)
    # Double outer border.
    fill_rect(10, 10, W - 20, 4, INK)
    fill_rect(10, W - 14, W - 20, 4, INK)
    fill_rect(10, 10, 4, W - 20, INK)
    fill_rect(W - 14, 10, 4, W - 20, INK)
    fill_rect(22, 22, W - 44, 2, INK)
    fill_rect(22, W - 24, W - 44, 2, INK)
    fill_rect(22, 22, 2, W - 44, INK)
    fill_rect(W - 24, 22, 2, W - 44, INK)

    # Masthead.
    draw_text_centered("THE WORLD", 30, 10, INK)
    rule(24, 1000, 116, 4)
    draw_text_centered("FRIDAY 13 NOVEMBER 2026", 128, 3, INK)
    draw_text_centered("THE DAY'S WORLD NEWS IN ONE PICTURE", 156, 2, RED)
    rule(24, 1000, 178, 2)

    # Lead story: Ukraine peace talks.
    draw_text("LEAD STORY", 40, 196, 2, RED)
    draw_text("EUROPE JOINS", 40, 222, 4, INK)
    draw_text("UKRAINE TALKS", 40, 254, 4, INK)
    draw_text("US ENVOYS: EUROPE WILL JOIN", 40, 292, 2, INK)
    draw_text("THE NEXT ROUND OF TALKS;", 40, 310, 2, INK)
    draw_text("BIGGEST PRISONER SWAP READIED", 40, 328, 2, INK)
    fill_rect(620, 192, 3, 156, INK)
    pic_flags(810, 262)

    rule(24, 1000, 362, 3)

    # Six stories.
    draw_panel(24, 378, "GULF ON EDGE", RED, pic_tanker,
               "IRAN SAYS IT HIT", "ON US RADAR",
               "BAHRAIN SITE STRUCK, IRAN", "TANKERS HIT IN HORMUZ")
    draw_panel(354, 378, "NVIDIA", NAVY, pic_chip,
               "HUANG RESIGNS", "AT NVIDIA",
               "SHARES FALL 16%; CFO", "KRESS NAMED INTERIM CHIEF")
    draw_panel(684, 378, "MICROSOFT DOWN", TEAL, pic_envelope,
               "OUTLOOK & TEAMS", "FAIL WORLDWIDE",
               "GLOBAL MICROSOFT 365", "OUTAGE HITS WORKPLACES")
    draw_panel(24, 636, "CRYPTO HEIST", GREEN, pic_padlock,
               "DOJ SEIZES $1.2BN", "IN N. KOREA HACK",
               "BINANCE THEFT BLAMED ON", "TRADERTRAITOR UNIT: FBI")
    draw_panel(354, 636, "GAZA", (122, 44, 34), pic_hospital,
               "HOSPITAL HIT IN", "KHAN YOUNIS",
               "ISRAELI STRIKE KILLS 6,", "SURGEON AMONG THE DEAD")
    draw_panel(684, 636, "SPORT", BLUE, pic_football,
               "KANE'S 126TH CAP", "SETS ENGLAND MARK",
               "ENGLAND BEAT CROATIA", "TO REACH NATIONS QFS")

    # Footer ticker: the rest of the day.
    fill_rect(24, 892, 976, 76, INK)
    draw_text_centered("ALSO: RECORD 483,200 US DEPORTATIONS IN 2026 - POPE LEO IN PERU",
                       902, 2, WHITE)
    draw_text_centered("STORM CHARLES HITS PORTUGAL - DEMOCRAT WINS KANSAS GOVERNOR RACE",
                       924, 2, WHITE)
    draw_text_centered("GOOGLE UNVEILS GEMINI 4 FOR SEARCH", 946, 2, WHITE)

    draw_text_centered("DRAWN IN CODE - THE WORLD - FRIDAY 13 NOVEMBER 2026",
                       978, 2, INK)


def main():
    build()
    rgb = downsample()
    data = encode_png(rgb, W, W)
    out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "entry.png"
    out_path.write_bytes(data)
    print(f"wrote {out_path} ({len(data)} bytes, {W}x{W})")


if __name__ == "__main__":
    main()
