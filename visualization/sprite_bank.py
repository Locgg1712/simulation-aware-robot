# visualization/sprite_bank.py
"""
SpriteBank: thay thế StardewSpriteBank, vẽ bằng PNG pixel-art thay vì pygame.draw.
Giữ NGUYÊN API của StardewSpriteBank nên chỉ cần đổi import trong pygame_renderer.py.

Cấu trúc thư mục assets (giải nén sprites.zip vào assets/sprites/):
    assets/sprites/*.png                 nhà, cây, props, nội thất, UI, icon
    assets/sprites/characters/<npc>/     down|up|left|right|... .png
    assets/sprites/robot/                walk_<dir>_<0-5>, idle_<dir>, hit_<dir>
    assets/sprites/crops/<crop>/         stage_00..09.png, soil/
    assets/sprites/terrain/seamless/     grass_*, dirt_*, sand_*, water_*, cobble_*

Nếu thiếu thư mục assets, tự động lùi về StardewSpriteBank cũ (vẽ tay).
"""
from __future__ import annotations

import math
import random
from pathlib import Path

import pygame

def _find_default_sprite_root() -> Path:
    base = Path(__file__).resolve().parents[1]
    candidates = [
        base / "sprites" / "sprites",
        base / "sprites",
    ]
    for cand in candidates:
        if (cand / "house_farm.png").exists():
            return cand
    return candidates[0]


DEFAULT_ROOT = _find_default_sprite_root()

HOUSE_RULES = [  # (từ khóa trong tên, sprite)
    ("Barn", "house_barn"), ("Coop", "house_coop"), ("Shed", "house_shed"),
    ("Pierre", "shop_pierre"), ("Store", "shop_pierre"), ("Saloon", "saloon"),
    ("Manor", "house_manor"), ("Mayor", "house_manor"), ("Blue", "house_blue"),
    ("River", "house_blue"), ("Cabin", "house_town"), ("Cottage", "house_town"),
    ("Haley", "house_town"), ("Blacksmith", "house_shed"), ("Museum", "house_town"),
    ("Farmhouse", "house_farm"),
]
DEFAULT_HOUSES = ["house_farm", "house_town", "house_blue"]
STATE_TO_DOOR = {"CLOSED": "door_closed", "OPENING": "door_opening",
                 "OPEN": "door_open", "CLOSING": "door_closing"}


def _dir_from_theta(theta: float) -> str:
    c, s = math.cos(theta), math.sin(theta)       # y màn hình hướng xuống
    if abs(c) >= abs(s):
        return "right" if c > 0 else "left"
    return "down" if s > 0 else "up"


def _rounded(surf: pygame.Surface, radius: int) -> pygame.Surface:
    out = surf.convert_alpha()
    mask = pygame.Surface(out.get_size(), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius)
    out.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return out


class AssetManager:
    """Nạp PNG một lần, cache bản đã scale."""

    def __init__(self, root: str | Path | None = None):
        self.root = Path(root) if root else DEFAULT_ROOT
        self._raw: dict[str, pygame.Surface | None] = {}
        self._scaled: dict[tuple, pygame.Surface | None] = {}
        self._tiled: dict[tuple, pygame.Surface] = {}
        chars = self.root / "characters"
        self.characters = sorted(p.name for p in chars.iterdir() if p.is_dir()) if chars.exists() else []

    @property
    def available(self) -> bool:
        return self.root.exists() and (self.root / "house_farm.png").exists()

    def raw(self, rel: str) -> pygame.Surface | None:
        if rel not in self._raw:
            p = self.root / f"{rel}.png"
            if not p.exists():
                p = self.root / f"{rel}.PNG"
            self._raw[rel] = pygame.image.load(str(p)).convert_alpha() if p.exists() else None
        return self._raw[rel]

    def scaled(self, rel: str, w: int | None = None, h: int | None = None,
               flip: bool = False, rotate: int = 0) -> pygame.Surface | None:
        key = (rel, w, h, flip, rotate)
        if key in self._scaled:
            return self._scaled[key]
        src = self.raw(rel)
        out = None
        if src is not None:
            sw, sh = src.get_size()
            if w is None and h is None:
                w, h = sw, sh
            elif w is None:
                w = max(1, round(sw * h / sh))
            elif h is None:
                h = max(1, round(sh * w / sw))
            out = pygame.transform.smoothscale(src, (max(1, int(w)), max(1, int(h))))
            if flip:
                out = pygame.transform.flip(out, True, False)
            if rotate:
                out = pygame.transform.rotate(out, rotate)
        self._scaled[key] = out
        return out

    def tiled(self, rel: str, w: int, h: int, tile_px: int, dark: float = 1.0) -> pygame.Surface | None:
        key = (rel, w, h, tile_px, dark)
        if key in self._tiled:
            return self._tiled[key]
        t = self.scaled(rel, tile_px, tile_px)
        if t is None:
            return None
        out = pygame.Surface((max(1, w), max(1, h)), pygame.SRCALPHA)
        for y in range(0, h, tile_px):
            for x in range(0, w, tile_px):
                out.blit(t, (x, y))
        if dark < 1.0:
            v = int(255 * dark)
            out.fill((v, v, v, 255), special_flags=pygame.BLEND_RGBA_MULT)
        self._tiled[key] = out
        return out


class SpriteBank:
    """Drop-in thay StardewSpriteBank (cùng tên phương thức và tham số)."""

    def __init__(self, scale: float, asset_root: str | Path | None = None):
        self.scale = scale
        self.assets = AssetManager(asset_root)
        self._shadow_cache: dict[tuple, pygame.Surface] = {}
        self._fb = None
        if not self.assets.available:
            try:
                from .stardew_sprites import StardewSpriteBank
                self._fb = StardewSpriteBank(scale)
                print("[SpriteBank] Không thấy assets/sprites, dùng đồ họa vẽ tay cũ.")
            except ImportError:
                print("[SpriteBank] Không thấy assets/sprites và không có StardewSpriteBank.")

    # ------------------------------------------------------------------ tiện ích
    def _m2px(self, m: float) -> int:
        return int(round(m * self.scale))

    def _rect(self, x, y, w, h):
        return (self._m2px(x), self._m2px(y), self._m2px(w), self._m2px(h))

    def _shadow(self, screen, cx, cy, w, h, alpha=70):
        key = (int(w), int(h), alpha)
        s = self._shadow_cache.get(key)
        if s is None:
            s = pygame.Surface((max(2, int(w)), max(2, int(h))), pygame.SRCALPHA)
            pygame.draw.ellipse(s, (14, 24, 12, alpha), s.get_rect())
            self._shadow_cache[key] = s
        screen.blit(s, (cx - s.get_width() // 2, cy - s.get_height() // 2))

    def _blit_bottom(self, screen, surf, cx, bottom):
        screen.blit(surf, (cx - surf.get_width() // 2, bottom - surf.get_height()))

    # ------------------------------------------------------------------ NỀN BẢN ĐỒ
    def build_background_surface(self, window_size, world_width, world_height, static_objects,
                                 start_pos, goal_pos, seed=42, topology_id=1):
        if self._fb:
            return self._fb.build_background_surface(window_size, world_width, world_height,
                                                     static_objects, start_pos, goal_pos, seed, topology_id)
        A, s = self.assets, window_size / world_width
        self.scale = s
        rng = random.Random(seed)
        bg = pygame.Surface((window_size, window_size))
        tile = max(48, self._m2px(2.0))
        base = A.tiled("terrain/seamless/grass_1", window_size, window_size, tile)
        bg.fill((106, 176, 72))
        if base:
            bg.blit(base, (0, 0))
        occupied: list[pygame.Rect] = []

        def zone(rel, x, y, w, h, radius=10, outline=(90, 70, 40), tile_m=1.6):
            rx, ry, rw, rh = self._rect(x, y, w, h)
            t = A.tiled(rel, rw, rh, self._m2px(tile_m))
            if t:
                bg.blit(_rounded(t, radius), (rx, ry))
                pygame.draw.rect(bg, outline, (rx, ry, rw, rh), 2, border_radius=radius)
            occupied.append(pygame.Rect(rx, ry, rw, rh))

        def field(x, y, w, h, sprinklers=False):
            rx, ry, rw, rh = self._rect(x, y, w, h)
            t = A.tiled("crops/soil/tilled_soil", rw, rh, self._m2px(1.2))
            if t:
                bg.blit(_rounded(t, 6), (rx, ry))
                pygame.draw.rect(bg, (70, 42, 20), (rx, ry, rw, rh), 2, border_radius=6)
            cell = self._m2px(0.9)
            crops = ["pumpkin", "strawberry", "tomato", "wheat", "corn", "carrot", "cabbage"]
            kind = rng.choice(crops)
            for cy in range(ry + cell // 2 + 4, ry + rh - cell // 3, cell):
                for cx in range(rx + cell // 2 + 2, rx + rw - cell // 3, cell):
                    st = A.scaled(f"crops/{kind}/stage_{rng.choice([6, 7, 8, 9]):02d}", None, int(cell * 0.85))
                    if st:
                        bg.blit(st, (cx - st.get_width() // 2, cy - st.get_height() // 2))
            if sprinklers:
                sp = A.scaled("sprinkler", None, self._m2px(0.7))
                if sp:
                    bg.blit(sp, (rx + rw // 2 - sp.get_width() // 2, ry + rh // 2 - sp.get_height() // 2))
            occupied.append(pygame.Rect(rx, ry, rw, rh))

        SAND, DIRT, COBBLE = "terrain/seamless/sand_1", "terrain/seamless/dirt_1", "terrain/seamless/cobble_1"
        SAND_O, DIRT_O, COB_O = (176, 128, 64), (110, 70, 30), (60, 58, 66)

        if topology_id == 1:
            zone(SAND, 9.2, 0.25, 10.5, 5.4, 14, SAND_O)
            zone(SAND, 2.4, 5.5, 3.0, 11.5, 12, SAND_O)
            zone(SAND, 9.5, 13.8, 9.8, 5.8, 14, SAND_O)
            field(4.8, 2.2, 2.0, 3.4)
            field(6.0, 7.6, 3.6, 3.4)
        elif topology_id == 2:
            field(5.6, 4.6, 4.8, 4.8, True)
            field(15.8, 14.8, 3.4, 4.2, True)
            for r in [(3.0, 9.4, 16.5, 1.7), (9.8, 5.2, 1.5, 4.5), (4.2, 10.8, 1.4, 8.5), (14.2, 10.8, 1.4, 8.5)]:
                zone(COBBLE, *r, radius=4, outline=COB_O, tile_m=1.4)
        elif topology_id == 3:
            for r in [(3.2, 4.4, 4.8, 6.4), (0.5, 4.2, 3.0, 1.2), (4.4, 10.6, 1.3, 6.2), (5.4, 12.8, 3.6, 1.2)]:
                zone(COBBLE, *r, radius=4, outline=COB_O, tile_m=1.4)
            pcx, pcy = self._m2px(5.2), self._m2px(7.8)
            pygame.draw.circle(bg, (186, 88, 76), (pcx, pcy), self._m2px(0.95))
            pygame.draw.circle(bg, (142, 62, 54), (pcx, pcy), self._m2px(0.95), 3)
            pygame.draw.circle(bg, (212, 122, 106), (pcx, pcy), self._m2px(0.55), 2)
            zone(DIRT, 10.8, 0.25, 3.3, 19.5, 8, DIRT_O)
            zone(COBBLE, 11.2, 4.15, 2.5, 1.65, 3, COB_O)
            zone(COBBLE, 11.2, 16.15, 2.5, 1.65, 3, COB_O)
        elif topology_id == 4:
            zone(SAND, 0.25, 1.5, 4.2, 7.2, 12, SAND_O)
            zone(DIRT, 4.5, 7.6, 14.8, 1.4, 6, DIRT_O)
            zone(DIRT, 9.2, 2.0, 1.4, 16.8, 6, DIRT_O)
            field(11.2, 7.8, 3.6, 4.2, True)
            field(3.2, 15.2, 8.8, 3.4, True)

        for px, py, pad in [(start_pos[0], start_pos[1], 1.0), (goal_pos[0], goal_pos[1], 1.1)]:
            zone(DIRT, px - pad, py - pad, pad * 2, pad * 2, 14, DIRT_O, tile_m=1.2)

        for o in static_objects:           # tránh rải hoa lên vật cản
            try:
                bx, by, bw, bh = o.bbox
                occupied.append(pygame.Rect(self._rect(bx - 0.3, by - 0.3, bw + 0.6, bh + 0.6)))
            except Exception:
                pass
        decor = [f"flower_{n}" for n in ["yellow_1", "white", "pink", "yellow_2", "blue"]] + ["rock_1", "rock_2"]
        placed, tries = 0, 0
        while placed < 70 and tries < 800:
            tries += 1
            fx = rng.randint(20, window_size - 20)
            fy = rng.randint(20, window_size - 20)
            if any(r.collidepoint(fx, fy) for r in occupied):
                continue
            name = rng.choice(decor)
            sp = A.scaled(name, None, self._m2px(0.38 if name.startswith("flower") else 0.34))
            if sp:
                bg.blit(sp, (fx - sp.get_width() // 2, fy - sp.get_height()))
                placed += 1
        return bg

    # ------------------------------------------------------------------ CÔNG TRÌNH, TƯỜNG, NƯỚC
    def _house_sprite(self, name: str, obj_id: int) -> str:
        for key, spr in HOUSE_RULES:
            if key.lower() in name.lower():
                return spr
        return DEFAULT_HOUSES[obj_id % 3]

    def _building(self, screen, rel, sx, sy, sw, sh, width_scale=1.1, min_h=None):
        w = max(8, int(sw * width_scale))
        spr = self.assets.scaled(rel, w, None)
        if spr is None:
            return False
        if min_h and spr.get_height() < min_h:
            spr = self.assets.scaled(rel, w, int(min_h))
        self._shadow(screen, sx + sw // 2, sy + sh, w * 0.95, max(8, w * 0.18))
        screen.blit(spr, (sx + sw // 2 - spr.get_width() // 2, sy + sh - spr.get_height() + 3))
        return True

    def draw_house_or_wall(self, screen, sx, sy, sw, sh, obj_id, name, font):
        if self._fb:
            return self._fb.draw_house_or_wall(screen, sx, sy, sw, sh, obj_id, name, font)
        A, n = self.assets, name
        if n.startswith("indoor_void_"):
            return
        if n.startswith("furniture_"):
            return self._draw_furniture(screen, sx, sy, sw, sh, n)
        if n.startswith("water_"):
            return self._draw_water(screen, sx, sy, sw, sh, n)
        if n.startswith("greenhouse"):
            if self._building(screen, "greenhouse", sx, sy, sw, sh, 1.05):
                return
        if n.startswith("windmill"):
            if self._building(screen, "windmill", sx, sy, sw, sh, 1.7):
                return
        if n.startswith("jojamart"):
            if self._building(screen, "jojamart", sx, sy, sw, sh, 1.05):
                return
        if n.startswith("fence"):
            return self._draw_fence(screen, sx, sy, sw, sh)
        if n.startswith(("wall_top", "wall_bottom", "wall_left", "wall_right")):
            return self._draw_fence(screen, sx, sy, sw, sh)
        if n.startswith("house_"):
            big = sw > self._m2px(4.2) or sh > self._m2px(3.6)
            if not big:
                if self._building(screen, self._house_sprite(n, obj_id), sx, sy, sw, sh, 1.12):
                    return
            else:
                return self._draw_house_block(screen, sx, sy, sw, sh, n, obj_id)
        self._draw_stone_wall(screen, sx, sy, sw, sh)

    def _draw_house_block(self, screen, sx, sy, sw, sh, name, obj_id):
        cols = max(1, round(sw / self._m2px(3.4)))
        rows = max(1, round(sh / self._m2px(2.8)))
        cw, ch = sw / cols, sh / rows
        k = 0
        for r in range(rows):
            for c in range(cols):
                rel = DEFAULT_HOUSES[(obj_id + k) % 3] if k % 2 else "house_farm"
                k += 1
                self._building(screen, rel, int(sx + c * cw), int(sy + r * ch), int(cw * 0.94), int(ch), 1.0)

    def _draw_stone_wall(self, screen, sx, sy, sw, sh):
        t = self.assets.tiled("terrain/seamless/cobble_1", sw, sh, self._m2px(0.9), dark=0.72)
        if t is None:
            pygame.draw.rect(screen, (96, 100, 110), (sx, sy, sw, sh), border_radius=2)
            return
        screen.blit(t, (sx, sy))
        pygame.draw.rect(screen, (40, 38, 46), (sx, sy, sw, sh), 2)

    def _draw_fence(self, screen, sx, sy, sw, sh):
        A = self.assets
        horizontal = sw >= sh
        if horizontal:
            th = max(26, int(sh * 2.4))
            tile = A.scaled("fence_rail_1", None, th)
            if tile is None:
                return self._draw_stone_wall(screen, sx, sy, sw, sh)
            y = sy + sh // 2 - th // 2
            x = sx
            while x < sx + sw:
                screen.blit(tile, (x, y), pygame.Rect(0, 0, min(tile.get_width(), sx + sw - x), th))
                x += tile.get_width() - 2
        else:
            tw = max(26, int(sw * 2.4))
            tile = A.scaled("fence_rail_1", None, tw, rotate=90)
            if tile is None:
                return self._draw_stone_wall(screen, sx, sy, sw, sh)
            x = sx + sw // 2 - tw // 2
            y = sy
            while y < sy + sh:
                screen.blit(tile, (x, y), pygame.Rect(0, 0, tile.get_width(), min(tile.get_height(), sy + sh - y)))
                y += tile.get_height() - 2

    def _draw_water(self, screen, sx, sy, sw, sh, name):
        if "fishpond" in name:
            spr = self.assets.scaled("fishpond", max(8, sw + 8), max(8, sh + 8))
            if spr:
                screen.blit(spr, (sx - 4, sy - 4))
                return
        t = self.assets.tiled("terrain/seamless/water_1", sw, sh, self._m2px(1.6))
        if t is None:
            pygame.draw.rect(screen, (52, 128, 196), (sx, sy, sw, sh), border_radius=4)
            return
        screen.blit(_rounded(t, 6), (sx, sy))
        pygame.draw.rect(screen, (30, 84, 150), (sx, sy, sw, sh), 2, border_radius=6)
        pygame.draw.rect(screen, (170, 220, 245), (sx + 3, sy + 3, sw - 6, sh - 6), 1, border_radius=5)

    def _draw_furniture(self, screen, sx, sy, sw, sh, name):
        rel = None
        for key, spr in [("bookshelf", "furn_bookshelf"), ("fireplace", "furn_fireplace"), ("bed", "furn_bed"),
                         ("table", "furn_table"), ("counter", "furn_counter")]:
            if key in name:
                rel = spr
        if rel is None:
            pygame.draw.rect(screen, (124, 72, 34), (sx, sy, sw, sh), border_radius=4)
            return
        spr = self.assets.scaled(rel, int(sw * 1.08), None)
        if spr is None:
            return
        if spr.get_height() < sh:
            spr = self.assets.scaled(rel, int(sw * 1.08), sh)
        screen.blit(spr, (sx + sw // 2 - spr.get_width() // 2, sy + sh - spr.get_height()))

    # ------------------------------------------------------------------ CÂY, SILO, CHẬU CÂY
    def draw_tree_sprite(self, screen, cx, cy, radius_px, obj_id=1, name="tree"):
        if self._fb:
            return self._fb.draw_tree_sprite(screen, cx, cy, radius_px, obj_id, name)
        A = self.assets
        if name.startswith("silo"):
            spr = A.scaled("silo", None, int(radius_px * 6.0))
        elif name.startswith("furniture_plant"):
            spr = A.scaled("furn_plant", None, int(radius_px * 3.4))
        else:
            if "cherry" in name:
                rel = "tree_cherry"
            elif "pine" in name:
                rel = "tree_pine"
            elif "oak" in name:
                rel = "tree_oak"
            else:
                rel = ["tree_oak", "tree_pine", "tree_cherry"][obj_id % 3]
            spr = A.scaled(rel, None, int(radius_px * 5.2))
        if spr is None:
            return
        bottom = cy + int(radius_px * 0.85)
        self._shadow(screen, cx, bottom - 2, radius_px * 2.4, radius_px * 0.9)
        self._blit_bottom(screen, spr, cx, bottom)

    # ------------------------------------------------------------------ NỘI THẤT TRONG NHÀ
    def draw_indoor_room_environment(self, screen, room_bounds, exit_portal, house_name, font):
        if self._fb:
            return self._fb.draw_indoor_room_environment(screen, room_bounds, exit_portal, house_name, font)
        A = self.assets
        w_scr, _ = screen.get_size()
        screen.fill((10, 8, 16))
        rx, ry, rw, rh = self._rect(*room_bounds)
        pygame.draw.rect(screen, (92, 54, 28), (rx - 10, ry - 10, rw + 20, rh + 20), border_radius=8)
        floor = A.tiled("floor_wood", rw, rh, self._m2px(1.2))
        if floor:
            screen.blit(floor, (rx, ry))
        else:
            pygame.draw.rect(screen, (214, 158, 98), (rx, ry, rw, rh))
        wall_h = max(30, self._m2px(1.0))
        wall = A.tiled("wallpaper", rw, wall_h, self._m2px(1.0))
        if wall:
            screen.blit(wall, (rx, ry))
        pygame.draw.line(screen, (124, 72, 34), (rx, ry + wall_h), (rx + rw, ry + wall_h), 3)
        for wx in (rx + rw // 4, rx + (3 * rw) // 4):
            win = A.scaled("furn_window", None, wall_h - 6)
            if win:
                screen.blit(win, (wx - win.get_width() // 2, ry + 3))
        rug = A.scaled("furn_rug", int(rw * 0.42), None)
        if rug:
            screen.blit(rug, (rx + rw // 2 - rug.get_width() // 2, ry + rh // 2 - rug.get_height() // 2 + 14))
        ex, ey = self._m2px(exit_portal[0]), self._m2px(exit_portal[1])
        mat = A.scaled("red_mat", self._m2px(1.2), None)
        if mat:
            screen.blit(mat, (ex - mat.get_width() // 2, ry + rh - mat.get_height() + 2))
        lbl = font.render("EXIT [E]", True, (255, 245, 200))
        screen.blit(lbl, (ex - lbl.get_width() // 2, ry + rh + 8))
        title = font.render(f"INSIDE: {house_name.upper()} (Press [E] or Walk to EXIT to leave)", True, (255, 230, 130))
        screen.blit(title, (w_scr // 2 - title.get_width() // 2, max(12, ry - 32)))

    # ------------------------------------------------------------------ ROBOT
    def draw_robot_character(self, screen, rx, ry, rad_px, theta, speed, sim_time,
                             is_collision=False, carrying_item=True):
        if self._fb:
            return self._fb.draw_robot_character(screen, rx, ry, rad_px, theta, speed, sim_time,
                                                 is_collision, carrying_item)
        d = _dir_from_theta(theta)
        h = int(rad_px * 3.1)
        if is_collision:
            rel = f"robot/hit_{d}"
        elif speed > 0.05:
            rel = f"robot/walk_{d}_{int(sim_time * 9) % 6}"
        else:
            rel = f"robot/idle_{d}"
        spr = self.assets.scaled(rel, None, h)
        if spr is None:
            return
        bottom = ry + int(rad_px * 0.95)
        self._shadow(screen, rx, bottom - 2, rad_px * 2.0, rad_px * 0.8)
        self._blit_bottom(screen, spr, rx, bottom)

    # ------------------------------------------------------------------ NPC DÂN LÀNG
    def draw_villager_npc(self, screen, cx, cy, rad_px, human, sim_time, small_font, debug_mode=False):
        if self._fb:
            return self._fb.draw_villager_npc(screen, cx, cy, rad_px, human, sim_time, small_font, debug_mode)
        A = self.assets
        hid = getattr(human, "id", getattr(human, "obj_id", 0))
        if not A.characters:
            return
        folder = A.characters[hid % len(A.characters)]
        d = _dir_from_theta(human.theta)
        h = int(rad_px * 4.4)
        spr = A.scaled(f"characters/{folder}/{d}", None, h)
        if spr is None:
            return
        moving = human.speed > 0.1
        bob = int(round(abs(math.sin(sim_time * 10.0 + hid)) * 3)) if moving else 0
        bottom = cy + int(rad_px * 1.0)
        self._shadow(screen, cx, bottom - 2, rad_px * 2.0, rad_px * 0.8)
        self._blit_bottom(screen, spr, cx, bottom - bob)
        if human.social_context.value == "INTERACTING" and not debug_mode:
            bx, by = cx + 8, bottom - spr.get_height() - 12
            pygame.draw.rect(screen, (255, 255, 255), (bx, by, 22, 13), border_radius=4)
            pygame.draw.rect(screen, (85, 65, 45), (bx, by, 22, 13), 1, border_radius=4)
            for i in range(3):
                pygame.draw.circle(screen, (95, 75, 55), (bx + 6 + i * 5, by + 6), 1)

    # ------------------------------------------------------------------ ĐÍCH GIAO HÀNG, AGV, CỬA
    def draw_delivery_goal(self, screen, gx, gy, grad_px, sim_time):
        if self._fb:
            return self._fb.draw_delivery_goal(screen, gx, gy, grad_px, sim_time)
        pulse = int(math.sin(sim_time * 4.0) * 3)
        mat = self.assets.scaled("red_mat", int(grad_px * 2.4), None)
        if mat:
            screen.blit(mat, (gx - mat.get_width() // 2, gy - mat.get_height() // 2))
        pygame.draw.circle(screen, (245, 215, 110), (gx, gy), grad_px + pulse, 2)
        box = self.assets.scaled("icon_parcel", int(grad_px * 1.5), None)
        bob = int(math.sin(sim_time * 6.0) * 4.0)
        if box:
            screen.blit(box, (gx - box.get_width() // 2, gy - box.get_height() - 4 + bob))

    def draw_agv_cart(self, screen, cx, cy, rad_px, theta):
        if self._fb:
            return self._fb.draw_agv_cart(screen, cx, cy, rad_px, theta)
        c, s = math.cos(theta), math.sin(theta)
        if abs(c) >= abs(s):
            rel = "Agv right" if c >= 0 else "Agv left"
            spr = self.assets.scaled(rel, None, int(rad_px * 2.6))
            if spr is None:
                spr = self.assets.scaled("agv_side", None, int(rad_px * 2.6), flip=c < 0)
        else:
            rel = "Agv front" if s >= 0 else "Agv back"
            spr = self.assets.scaled(rel, None, int(rad_px * 2.6))
            if spr is None:
                spr = self.assets.scaled("agv_front", None, int(rad_px * 2.6))
        if spr is None:
            return
        bottom = cy + int(rad_px * 0.9)
        self._shadow(screen, cx, bottom - 2, rad_px * 2.0, rad_px * 0.7)
        self._blit_bottom(screen, spr, cx, bottom)

    def draw_door(self, screen, sx, sy, sw, sh, state_name: str):
        """Vẽ cửa bán tĩnh theo trạng thái FSM: CLOSED / OPENING / OPEN / CLOSING."""
        rel = STATE_TO_DOOR.get(state_name, "door_closed")
        if sh > sw:   # cửa dọc: xoay 90 độ
            spr = self.assets.scaled(rel, None, max(22, int(sw * 1.6)), rotate=90)
            if spr:
                spr = pygame.transform.smoothscale(spr, (spr.get_width(), max(8, sh)))
        else:
            spr = self.assets.scaled(rel, max(8, sw), None)
        if spr:
            screen.blit(spr, (sx + sw // 2 - spr.get_width() // 2, sy + sh // 2 - spr.get_height() // 2))
