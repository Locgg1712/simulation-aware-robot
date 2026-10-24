# game/terrain.py
"""
Nướng (bake) bề mặt địa hình cho bản đồ ngoài trời:
- Kết cấu liền mạch trải dài nhiều ô (không lặp từng ô 32px).
- Viền chuyển tiếp cỏ <-> đường đất/đá, bờ nước có bọt sóng, vách đá có mép cỏ.
- Cầu gỗ / cầu tàu, đất ruộng đã xới, rừng rậm tối màu, hoa cỏ rải rác.
"""

from __future__ import annotations

import random
import pygame

from .constants import (
    T_BRIDGE,
    T_CLIFF,
    T_COBBLE,
    T_CROP,
    T_DIRT,
    T_FOREST,
    T_GRASS,
    T_SAND,
    T_TALL_GRASS,
    T_WATER,
    T_WOOD_DOCK,
    TILE_SIZE,
)

T = TILE_SIZE

TEXTURES = {
    T_GRASS: ("terrain/seamless/grass_1", 6),
    T_TALL_GRASS: ("terrain/seamless/grass_3", 4),
    T_FOREST: ("terrain/seamless/grass_4", 4),
    T_DIRT: ("terrain/seamless/dirt_1", 5),
    T_COBBLE: ("terrain/seamless/cobble_1", 4),
    T_SAND: ("terrain/seamless/sand_1", 5),
    T_WATER: ("terrain/seamless/water_1", 5),
}

FALLBACK = {
    T_GRASS: (104, 176, 72),
    T_TALL_GRASS: (88, 160, 62),
    T_FOREST: (52, 108, 46),
    T_DIRT: (196, 146, 86),
    T_COBBLE: (150, 146, 140),
    T_SAND: (232, 206, 142),
    T_WATER: (58, 142, 210),
}

WALKABLE_GROUND = (T_DIRT, T_COBBLE, T_SAND)


def _tile_at(tiles, c, r):
    if 0 <= r < len(tiles) and 0 <= c < len(tiles[0]):
        return tiles[r][c]
    return None


def _blit_texture(surf, vault, t, c, r):
    tex = TEXTURES.get(t)
    cell = None
    if tex:
        cell = vault.texture_cell(tex[0], c, r, T, tex[1])
    if cell is not None:
        surf.blit(cell, (c * T, r * T))
    else:
        pygame.draw.rect(surf, FALLBACK.get(t, (100, 170, 70)), (c * T, r * T, T, T))


def _draw_planks(surf, c, r, horizontal: bool):
    x, y = c * T, r * T
    pygame.draw.rect(surf, (168, 116, 66), (x, y, T, T))
    if horizontal:
        for i in range(0, T, 8):
            pygame.draw.line(surf, (110, 70, 36), (x + i, y), (x + i, y + T), 2)
            pygame.draw.line(surf, (196, 146, 92), (x + i + 2, y + 2), (x + i + 2, y + T - 3), 1)
        pygame.draw.rect(surf, (96, 58, 28), (x, y, T, 4))
        pygame.draw.rect(surf, (96, 58, 28), (x, y + T - 4, T, 4))
    else:
        for i in range(0, T, 8):
            pygame.draw.line(surf, (110, 70, 36), (x, y + i), (x + T, y + i), 2)
            pygame.draw.line(surf, (196, 146, 92), (x + 2, y + i + 2), (x + T - 3, y + i + 2), 1)
        pygame.draw.rect(surf, (96, 58, 28), (x, y, 4, T))
        pygame.draw.rect(surf, (96, 58, 28), (x + T - 4, y, 4, T))


def _draw_cliff(surf, tiles, c, r, rng):
    x, y = c * T, r * T
    above = _tile_at(tiles, c, r - 1)
    below = _tile_at(tiles, c, r + 1)
    pygame.draw.rect(surf, (128, 92, 54), (x, y, T, T))
    # Các tầng đá xếp lớp
    for i in range(4, T, 9):
        pygame.draw.line(surf, (98, 68, 38), (x, y + i), (x + T, y + i + rng.randint(-1, 1)), 2)
    for _ in range(3):
        rx, ry = x + rng.randint(2, T - 8), y + rng.randint(2, T - 8)
        pygame.draw.ellipse(surf, (150, 112, 70), (rx, ry, 7, 4))
    if above != T_CLIFF:
        # Mép cỏ phủ lên đỉnh vách đá
        pygame.draw.rect(surf, (88, 156, 58), (x, y, T, 7))
        for i in range(0, T, 4):
            pygame.draw.polygon(surf, (88, 156, 58), [(x + i, y + 6), (x + i + 4, y + 6), (x + i + 2, y + 10 + rng.randint(0, 3))])
        pygame.draw.line(surf, (60, 116, 40), (x, y + 7), (x + T, y + 7), 1)
    if below != T_CLIFF:
        pygame.draw.rect(surf, (82, 56, 30), (x, y + T - 5, T, 5))


def _edge_details(surf, tiles, c, r, t, rng):
    """Viền chuyển tiếp giữa các loại địa hình."""
    x, y = c * T, r * T
    n = _tile_at(tiles, c, r - 1)
    s = _tile_at(tiles, c, r + 1)
    w = _tile_at(tiles, c - 1, r)
    e = _tile_at(tiles, c + 1, r)

    if t == T_WATER:
        foam = (214, 240, 255)
        wet = (128, 104, 64)
        land = lambda v: v is not None and v not in (T_WATER, T_BRIDGE, T_WOOD_DOCK)
        if land(n):
            pygame.draw.rect(surf, wet, (x, y, T, 3))
            pygame.draw.line(surf, foam, (x, y + 4), (x + T, y + 4), 2)
        if land(s):
            pygame.draw.line(surf, foam, (x, y + T - 3), (x + T, y + T - 3), 2)
        if land(w):
            pygame.draw.rect(surf, wet, (x, y, 3, T))
            pygame.draw.line(surf, foam, (x + 4, y), (x + 4, y + T), 2)
        if land(e):
            pygame.draw.rect(surf, wet, (x + T - 3, y, 3, T))
            pygame.draw.line(surf, foam, (x + T - 5, y), (x + T - 5, y + T), 2)
        return

    if t in (T_GRASS, T_TALL_GRASS, T_FOREST):
        # Mép cỏ sẫm + ngọn cỏ chìa ra đường đi
        edge_col = (62, 122, 44)
        for nb, side in ((n, "n"), (s, "s"), (w, "w"), (e, "e")):
            if nb in WALKABLE_GROUND or nb == T_CROP:
                if side == "n":
                    pygame.draw.line(surf, edge_col, (x, y), (x + T, y), 2)
                elif side == "s":
                    pygame.draw.line(surf, edge_col, (x, y + T - 1), (x + T, y + T - 1), 2)
                    for i in range(2, T, 6):
                        h = rng.randint(3, 6)
                        pygame.draw.line(surf, (96, 170, 64), (x + i, y + T - 1), (x + i + 1, y + T + h - 2), 2)
                elif side == "w":
                    pygame.draw.line(surf, edge_col, (x, y), (x, y + T), 2)
                else:
                    pygame.draw.line(surf, edge_col, (x + T - 1, y), (x + T - 1, y + T), 2)

    if t == T_TALL_GRASS:
        for _ in range(5):
            gx, gy = x + rng.randint(2, T - 4), y + rng.randint(8, T - 2)
            pygame.draw.line(surf, (54, 128, 42), (gx, gy), (gx - 2, gy - 8), 2)
            pygame.draw.line(surf, (74, 152, 52), (gx + 2, gy), (gx + 3, gy - 9), 2)


def bake_terrain_surface(game) -> pygame.Surface:
    tiles = game.tiles
    rows, cols = len(tiles), len(tiles[0])
    surf = pygame.Surface((cols * T, rows * T)).convert()
    rng = random.Random(game.current_map_id * 7919)
    vault = game.vault

    # 1. Lớp kết cấu nền
    for r in range(rows):
        for c in range(cols):
            t = tiles[r][c]
            if t in (T_BRIDGE, T_WOOD_DOCK):
                _blit_texture(surf, vault, T_WATER, c, r)
            elif t == T_CROP:
                soil = vault.scaled("crops/soil/tilled_soil", T, T)
                if soil is not None:
                    surf.blit(soil, (c * T, r * T))
                else:
                    pygame.draw.rect(surf, (120, 78, 44), (c * T, r * T, T, T))
            elif t == T_CLIFF:
                _draw_cliff(surf, tiles, c, r, rng)
            else:
                _blit_texture(surf, vault, t, c, r)

            # Biến thể mặt nước: lá sen, đá ngầm ở xa bờ
            if t == T_WATER and rng.random() < 0.035:
                deep = all(_tile_at(tiles, c + dc, r + dr) == T_WATER for dc in (-1, 0, 1) for dr in (-1, 0, 1))
                if deep:
                    variant = rng.choice(("water_lily_1", "water_lily_2", "water_rock_1", "water_rock_2"))
                    img = vault.scaled(f"terrain/seamless/{variant}", T, T)
                    if img is not None:
                        surf.blit(img, (c * T, r * T))

    # 2. Mảng sáng tối ngẫu nhiên phá vỡ sự lặp lại của cỏ
    shade = pygame.Surface((cols * T, rows * T), pygame.SRCALPHA)
    for _ in range(cols * rows // 18):
        c, r = rng.randrange(cols), rng.randrange(rows)
        if tiles[r][c] in (T_GRASS, T_TALL_GRASS):
            rw, rh = rng.randint(40, 110), rng.randint(24, 60)
            col = (255, 255, 180, rng.randint(10, 22)) if rng.random() < 0.5 else (20, 60, 10, rng.randint(12, 26))
            pygame.draw.ellipse(shade, col, (c * T - rw // 2, r * T - rh // 2, rw, rh))
    for r in range(rows):
        for c in range(cols):
            if tiles[r][c] == T_FOREST:
                shade.fill((10, 30, 8, 70), (c * T, r * T, T, T))
    surf.blit(shade, (0, 0))

    # 3. Viền chuyển tiếp, cầu gỗ
    for r in range(rows):
        for c in range(cols):
            t = tiles[r][c]
            if t in (T_BRIDGE, T_WOOD_DOCK):
                horiz = _tile_at(tiles, c - 1, r) in (T_BRIDGE, T_WOOD_DOCK) or _tile_at(tiles, c + 1, r) in (T_BRIDGE, T_WOOD_DOCK)
                vert = _tile_at(tiles, c, r - 1) in (T_BRIDGE, T_WOOD_DOCK) or _tile_at(tiles, c, r + 1) in (T_BRIDGE, T_WOOD_DOCK)
                _draw_planks(surf, c, r, horizontal=horiz and not (vert and not horiz))
            else:
                _edge_details(surf, tiles, c, r, t, rng)

    # 4. Hoa dại & cỏ nhỏ rải rác
    flowers = ("flower_blue", "flower_pink", "flower_white", "flower_yellow_1", "flower_yellow_2")
    for _ in range(cols * rows // 45):
        c, r = rng.randrange(cols), rng.randrange(rows)
        if tiles[r][c] == T_GRASS:
            img = vault.scaled(rng.choice(flowers), None, rng.randint(14, 18))
            if img is not None:
                surf.blit(img, (c * T + rng.randint(0, 14), r * T + rng.randint(0, 12)))

    # 5. Ảnh dán (cầu đá, cầu gỗ...)
    for sprite, x, y, w, h in getattr(game, "decals", []):
        img = vault.scaled(sprite, w, h)
        if img is not None:
            surf.blit(img, (x, y))

    return surf

