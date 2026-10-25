# game/terrain.py
"""
Nướng (bake) bề mặt địa hình cho bản đồ ngoài trời:
- Sử dụng toàn bộ kho tài nguyên địa hình trong `sprites/sprites/terrain/` & `terrain/seamless/`:
  + Cỏ: `grass_1..4`, chuyển tiếp cỏ-đất `grass_dirt_1..2`
  + Đường đá: `cobble_1..6`
  + Đường đất: `dirt_1..5` + vết chân `dirt_footprints`
  + Bãi cát: `sand_1..6`
  + Bờ nước & mặt hồ: `shore_top`, `shore_bottom`, `shore_left`, `shore_right`,
    `shore_corner_tl`, `shore_corner_tr`, `water_1`, `water_dock`, `water_lily_1..2`, `water_rock_1..2`
- Phối hợp ngẫu nhiên có kiểm soát (spatial hash + xoay/lật nhẹ) để triệt tiêu hoàn toàn hiện tượng lặp ô.
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

GRASS_VARIANTS = (
    "terrain/grass_1",
    "terrain/grass_2",
    "terrain/grass_3",
    "terrain/grass_4",
    "terrain/seamless/grass_1",
    "terrain/seamless/grass_2",
    "terrain/seamless/grass_3",
    "terrain/seamless/grass_4",
)
GRASS_DIRT_VARIANTS = (
    "terrain/grass_dirt_1",
    "terrain/grass_dirt_2",
    "terrain/seamless/grass_dirt_1",
    "terrain/seamless/grass_dirt_2",
)
DIRT_VARIANTS = (
    "terrain/dirt_1",
    "terrain/dirt_2",
    "terrain/dirt_3",
    "terrain/dirt_4",
    "terrain/dirt_5",
    "terrain/seamless/dirt_1",
    "terrain/seamless/dirt_2",
    "terrain/seamless/dirt_3",
    "terrain/seamless/dirt_4",
    "terrain/seamless/dirt_5",
)
COBBLE_VARIANTS = (
    "terrain/cobble_1",
    "terrain/cobble_2",
    "terrain/cobble_3",
    "terrain/cobble_4",
    "terrain/cobble_5",
    "terrain/cobble_6",
    "terrain/seamless/cobble_1",
    "terrain/seamless/cobble_2",
    "terrain/seamless/cobble_3",
    "terrain/seamless/cobble_4",
    "terrain/seamless/cobble_5",
    "terrain/seamless/cobble_6",
)
SAND_VARIANTS = (
    "terrain/sand_1",
    "terrain/sand_2",
    "terrain/sand_3",
    "terrain/sand_4",
    "terrain/sand_5",
    "terrain/sand_6",
    "terrain/seamless/sand_1",
    "terrain/seamless/sand_2",
    "terrain/seamless/sand_3",
    "terrain/seamless/sand_4",
    "terrain/seamless/sand_5",
    "terrain/seamless/sand_6",
)

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


def _spatial_hash(c: int, r: int, seed: int = 0) -> int:
    """Băm vị trí (c, r) phi tuần hoàn để chọn biến thể không bị lặp theo hàng/cột."""
    h = (c * 374761393 + r * 668265263 + seed * 1442695041) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return h ^ (h >> 16)


def _blit_varied_tile(surf, vault, tiles, t: int, c: int, r: int, map_seed: int):
    h = _spatial_hash(c, r, map_seed)
    flip_x = bool((h >> 8) & 1)
    n = _tile_at(tiles, c, r - 1)
    s = _tile_at(tiles, c, r + 1)
    w = _tile_at(tiles, c - 1, r)
    e = _tile_at(tiles, c + 1, r)

    # 1. Mặt nước & bờ biển (sử dụng đầy đủ bộ shore_* và water_*)
    if t == T_WATER:
        is_land = lambda v: v is not None and v not in (T_WATER, T_BRIDGE, T_WOOD_DOCK)
        ln, ls, lw, le = is_land(n), is_land(s), is_land(w), is_land(e)
        shore_rel = None
        shore_flip = False
        if ln and lw:
            shore_rel = "terrain/shore_corner_tl"
        elif ln and le:
            shore_rel = "terrain/shore_corner_tr"
        elif ln:
            shore_rel = "terrain/shore_top"
            shore_flip = flip_x
        elif ls:
            shore_rel = "terrain/shore_bottom"
            shore_flip = flip_x
        elif lw:
            shore_rel = "terrain/shore_left"
        elif le:
            shore_rel = "terrain/shore_right"
        elif e == T_WOOD_DOCK or w == T_WOOD_DOCK:
            shore_rel = "terrain/water_dock"
            shore_flip = (w == T_WOOD_DOCK)

        if shore_rel is not None:
            spr = vault.scaled(shore_rel, T, T, flip_x=shore_flip)
            if spr is not None:
                surf.blit(spr, (c * T, r * T))
                return

        # Nước sâu: kết hợp seamless water_1 (span 2) và full water_1
        cell = vault.texture_cell("terrain/seamless/water_1", c + (h & 1), r + ((h >> 1) & 1), T, 2)
        if cell is not None:
            surf.blit(cell, (c * T, r * T))
        else:
            pygame.draw.rect(surf, FALLBACK[T_WATER], (c * T, r * T, T, T))
        return

    # 2. Cỏ thường / Cỏ cao / Rừng (kết hợp grass_1..4 và grass_dirt_1..2 ở rìa đường đất)
    if t in (T_GRASS, T_TALL_GRASS, T_FOREST):
        borders_dirt = any(nb in (T_DIRT, T_CROP) for nb in (n, s, w, e))
        if borders_dirt and (h % 3 != 0):
            rel = GRASS_DIRT_VARIANTS[h % len(GRASS_DIRT_VARIANTS)]
            spr = vault.scaled(rel, T, T, flip_x=flip_x)
            if spr is not None:
                surf.blit(spr, (c * T, r * T))
                return

        if t == T_FOREST:
            forest_pool = ("terrain/grass_4", "terrain/seamless/grass_4", "terrain/grass_3")
            rel = forest_pool[h % len(forest_pool)]
        elif t == T_TALL_GRASS:
            tall_pool = ("terrain/grass_3", "terrain/seamless/grass_3", "terrain/grass_2")
            rel = tall_pool[h % len(tall_pool)]
        else:
            rel = GRASS_VARIANTS[h % len(GRASS_VARIANTS)]

        if (h & 3) == 0:
            cell = vault.texture_cell(rel, c, r, T, 2)
            if cell is not None:
                surf.blit(cell, (c * T, r * T))
                return
        spr = vault.scaled(rel, T, T, flip_x=flip_x)
        if spr is not None:
            surf.blit(spr, (c * T, r * T))
        else:
            pygame.draw.rect(surf, FALLBACK.get(t, (100, 170, 70)), (c * T, r * T, T, T))
        return

    # 3. Đường lát đá cuội (sử dụng cả 6 mẫu cobble_1..6 ở tỷ lệ chuẩn 32x32 & 64x64)
    if t == T_COBBLE:
        rel = COBBLE_VARIANTS[h % len(COBBLE_VARIANTS)]
        if (h & 3) == 0:
            cell = vault.texture_cell(rel, c, r, T, 2)
            if cell is not None:
                surf.blit(cell, (c * T, r * T))
                return
        spr = vault.scaled(rel, T, T, flip_x=flip_x)
        if spr is not None:
            surf.blit(spr, (c * T, r * T))
        else:
            pygame.draw.rect(surf, FALLBACK[T_COBBLE], (c * T, r * T, T, T))
        return

    # 4. Đường đất (sử dụng cả 5 mẫu dirt_1..5 + vết chân dirt_footprints)
    if t == T_DIRT:
        if (h % 7) == 0:
            rel = "terrain/dirt_footprints" if (h & 1) else "terrain/seamless/dirt_footprints"
        else:
            rel = DIRT_VARIANTS[h % len(DIRT_VARIANTS)]
        spr = vault.scaled(rel, T, T, flip_x=flip_x)
        if spr is not None:
            surf.blit(spr, (c * T, r * T))
        else:
            pygame.draw.rect(surf, FALLBACK[T_DIRT], (c * T, r * T, T, T))
        return

    # 5. Bãi cát (sử dụng cả 6 mẫu sand_1..6)
    if t == T_SAND:
        rel = SAND_VARIANTS[h % len(SAND_VARIANTS)]
        spr = vault.scaled(rel, T, T, flip_x=flip_x)
        if spr is not None:
            surf.blit(spr, (c * T, r * T))
        else:
            pygame.draw.rect(surf, FALLBACK[T_SAND], (c * T, r * T, T, T))
        return

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
    for i in range(4, T, 9):
        pygame.draw.line(surf, (98, 68, 38), (x, y + i), (x + T, y + i + rng.randint(-1, 1)), 2)
    for _ in range(3):
        rx, ry = x + rng.randint(2, T - 8), y + rng.randint(2, T - 8)
        pygame.draw.ellipse(surf, (150, 112, 70), (rx, ry, 7, 4))
    if above != T_CLIFF:
        pygame.draw.rect(surf, (88, 156, 58), (x, y, T, 7))
        for i in range(0, T, 4):
            pygame.draw.polygon(
                surf,
                (88, 156, 58),
                [(x + i, y + 6), (x + i + 4, y + 6), (x + i + 2, y + 10 + rng.randint(0, 3))],
            )
        pygame.draw.line(surf, (60, 116, 40), (x, y + 7), (x + T, y + 7), 1)
    if below != T_CLIFF:
        pygame.draw.rect(surf, (82, 56, 30), (x, y + T - 5, T, 5))


def _edge_details(surf, tiles, c, r, t, rng):
    """Viền chuyển tiếp mềm mại giữa cỏ và đường đi."""
    x, y = c * T, r * T
    n = _tile_at(tiles, c, r - 1)
    s = _tile_at(tiles, c, r + 1)
    w = _tile_at(tiles, c - 1, r)
    e = _tile_at(tiles, c + 1, r)

    if t in (T_GRASS, T_TALL_GRASS, T_FOREST):
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
    map_seed = int(getattr(game, "current_map_id", 1)) * 7919
    rng = random.Random(map_seed)
    vault = game.vault

    # 1. Lớp kết cấu nền đa dạng (khai thác toàn bộ kho ảnh terrain/)
    for r in range(rows):
        for c in range(cols):
            t = tiles[r][c]
            if t in (T_BRIDGE, T_WOOD_DOCK):
                _blit_varied_tile(surf, vault, tiles, T_WATER, c, r, map_seed)
            elif t == T_CROP:
                soil = vault.scaled("crops/soil/tilled_soil", T, T)
                if soil is not None:
                    surf.blit(soil, (c * T, r * T))
                else:
                    pygame.draw.rect(surf, (120, 78, 44), (c * T, r * T, T, T))
            elif t == T_CLIFF:
                _draw_cliff(surf, tiles, c, r, rng)
            else:
                _blit_varied_tile(surf, vault, tiles, t, c, r, map_seed)

            # Biến thể mặt nước: lá sen, đá ngầm ở xa bờ (cả bản thường lẫn seamless)
            if t == T_WATER and rng.random() < 0.08:
                deep = all(_tile_at(tiles, c + dc, r + dr) == T_WATER for dc in (-1, 0, 1) for dr in (-1, 0, 1))
                if deep:
                    variant = rng.choice((
                        "terrain/water_lily_1",
                        "terrain/water_lily_2",
                        "terrain/water_rock_1",
                        "terrain/water_rock_2",
                        "terrain/seamless/water_lily_1",
                        "terrain/seamless/water_lily_2",
                        "terrain/seamless/water_rock_1",
                        "terrain/seamless/water_rock_2",
                    ))
                    img = vault.scaled(variant, T, T)
                    if img is not None:
                        surf.blit(img, (c * T, r * T))

    # 2. Mảng sáng tối ngẫu nhiên nhẹ làm dịu mắt trên thảm cỏ
    shade = pygame.Surface((cols * T, rows * T), pygame.SRCALPHA)
    for _ in range(cols * rows // 18):
        c, r = rng.randrange(cols), rng.randrange(rows)
        if tiles[r][c] in (T_GRASS, T_TALL_GRASS):
            rw, rh = rng.randint(40, 110), rng.randint(24, 60)
            col = (255, 255, 180, rng.randint(8, 18)) if rng.random() < 0.5 else (20, 60, 10, rng.randint(10, 22))
            pygame.draw.ellipse(shade, col, (c * T - rw // 2, r * T - rh // 2, rw, rh))
    for r in range(rows):
        for c in range(cols):
            if tiles[r][c] == T_FOREST:
                shade.fill((10, 30, 8, 65), (c * T, r * T, T, T))
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
    flowers = ("flower_blue", "flower_pink", "flower_white", "flower_yellow_1", "flower_yellow_2", "flower_green")
    for _ in range(cols * rows // 42):
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
