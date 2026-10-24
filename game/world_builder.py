# game/world_builder.py
"""
Bộ công cụ dựng bản đồ phong cách Stardew Valley:
- Tô vùng địa hình (chữ nhật, elip, đường đi), rừng viền bản đồ, vách đá.
- Đặt nhà cửa (có thảm đỏ trước cửa), cây cối, đồ trang trí, hàng rào.
- Tạo thửa ruộng có rào bao quanh + điểm thu hoạch, cây ăn quả, chuồng thú.
"""

from __future__ import annotations

import math
import random
import pygame

from .constants import (
    T_CLIFF,
    T_CROP,
    T_FOREST,
    T_GRASS,
    TILE_SIZE,
    WORLD_COLS,
    WORLD_ROWS,
)
from .entities import FarmAnimal, HarvestSpot, PropObject

T = TILE_SIZE


class WorldBuilder:
    """Ghi trực tiếp vào trạng thái game (tiles, props, harvest_spots, animals...)."""

    def __init__(self, game, seed: int):
        self.game = game
        self.vault = game.vault
        self.rng = random.Random(seed)
        self.cols = WORLD_COLS
        self.rows = WORLD_ROWS
        game.tiles = [[T_GRASS for _ in range(self.cols)] for _ in range(self.rows)]
        game.decals = []          # Ảnh dán xuống nền (cầu, hoa...) được nướng vào terrain
        game.ground_props = []    # Vật thể sát đất vẽ trước nhân vật (cây trồng trong ruộng...)

    # ------------------------------------------------------------------
    # Tô địa hình
    # ------------------------------------------------------------------
    def in_bounds(self, c: int, r: int) -> bool:
        return 0 <= c < self.cols and 0 <= r < self.rows

    def set(self, c: int, r: int, t: int):
        if self.in_bounds(c, r):
            self.game.tiles[r][c] = t

    def get(self, c: int, r: int) -> int | None:
        if self.in_bounds(c, r):
            return self.game.tiles[r][c]
        return None

    def fill(self, c0: int, r0: int, c1: int, r1: int, t: int):
        for r in range(max(0, r0), min(self.rows, r1 + 1)):
            for c in range(max(0, c0), min(self.cols, c1 + 1)):
                self.game.tiles[r][c] = t

    def ellipse(self, cx: float, cy: float, rx: float, ry: float, t: int, only: tuple | None = None):
        for r in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for c in range(int(cx - rx) - 1, int(cx + rx) + 2):
                if not self.in_bounds(c, r):
                    continue
                dx = (c + 0.5 - cx) / max(0.01, rx)
                dy = (r + 0.5 - cy) / max(0.01, ry)
                if dx * dx + dy * dy <= 1.0:
                    if only is None or self.game.tiles[r][c] in only:
                        self.game.tiles[r][c] = t

    def path(self, points: list[tuple[int, int]], width: int, t: int, only: tuple | None = None):
        """Vẽ đường đi dày `width` ô qua các điểm (cột, hàng)."""
        for (c0, r0), (c1, r1) in zip(points, points[1:]):
            steps = max(abs(c1 - c0), abs(r1 - r0), 1)
            for i in range(steps + 1):
                c = round(c0 + (c1 - c0) * i / steps)
                r = round(r0 + (r1 - r0) * i / steps)
                for dc in range(width):
                    for dr in range(width):
                        cc, rr = c + dc - width // 2, r + dr - width // 2
                        if self.in_bounds(cc, rr):
                            if only is None or self.game.tiles[rr][cc] in only:
                                self.game.tiles[rr][cc] = t

    def ring(self, src: int, ring_t: int, thickness: int = 1, only: tuple = (T_GRASS,)):
        """Tạo viền (bờ cát) bao quanh vùng địa hình `src`."""
        for _ in range(thickness):
            marks = []
            for r in range(self.rows):
                for c in range(self.cols):
                    if self.game.tiles[r][c] not in only:
                        continue
                    for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
                        if self.get(c + dc, r + dr) == src:
                            marks.append((c, r))
                            break
            for c, r in marks:
                self.game.tiles[r][c] = ring_t
            src = ring_t

    def forest_border(self, depth: int = 2, gaps: dict | None = None):
        """Rừng rậm viền 4 cạnh bản đồ, chừa lối đi cho cổng chuyển map."""
        gaps = gaps or {}
        for r in range(self.rows):
            for c in range(self.cols):
                edge = None
                if r < depth:
                    edge = "N"
                elif r >= self.rows - depth:
                    edge = "S"
                elif c < depth:
                    edge = "W"
                elif c >= self.cols - depth:
                    edge = "E"
                if edge is None:
                    continue
                lo_hi = gaps.get(edge)
                idx = c if edge in ("N", "S") else r
                if lo_hi and lo_hi[0] <= idx <= lo_hi[1]:
                    continue
                self.game.tiles[r][c] = T_FOREST

    def plant_forest_trees(self):
        """Phủ cây rừng (thông, sồi, anh đào) lên các ô rừng rậm."""
        for r in range(0, self.rows, 2):
            for c in range(0, self.cols, 2):
                if self.get(c, r) != T_FOREST:
                    continue
                jitter_x = self.rng.randint(-6, 6)
                jitter_y = self.rng.randint(-4, 8)
                kind = self.rng.choices(("tree_pine", "tree_oak", "tree_cherry"), (5, 4, 1))[0]
                self.tree(kind, c * T + T + jitter_x, r * T + T + 14 + jitter_y,
                          h=self.rng.randint(118, 150), solid=False)

    def cliff_band(self, c0: int, c1: int, r: int, height: int = 2):
        self.fill(c0, r, c1, r + height - 1, T_CLIFF)

    # ------------------------------------------------------------------
    # Đặt vật thể
    # ------------------------------------------------------------------
    def prop(
        self,
        sprite: str,
        cx: float,
        base_y: float,
        h: int | None = None,
        w: int | None = None,
        solid: bool = True,
        collider_w: float = 0.7,
        collider_h: int = 14,
        kind: str = "prop",
        flip: bool = False,
    ) -> PropObject | None:
        """Đặt vật thể có tâm đáy tại (cx, base_y) — dùng cho Y-sorting."""
        spr = self.vault.scaled(sprite, w, h, flip_x=flip)
        if spr is None:
            return None
        sw, sh = spr.get_size()
        x = int(cx - sw / 2)
        y = int(base_y - sh)
        cw = max(6, int(sw * collider_w))
        col = pygame.Rect(int(cx - cw / 2), int(base_y - collider_h), cw, collider_h)
        p = PropObject(kind=kind, x=x, y=y, sprite=spr, collider=col, solid=solid)
        self.game.props.append(p)
        return p

    def tree(self, kind: str, cx: float, base_y: float, h: int = 150, solid: bool = True) -> PropObject | None:
        p = self.prop(kind, cx, base_y + 6, h=h, solid=solid, collider_w=0.2, collider_h=16, kind="tree")
        return p

    def building(
        self,
        sprite: str,
        cx: float,
        bottom: float,
        scale: float,
        house_id: str = "",
        interior_type: str = "",
        title: str = "",
        owner_name: str = "",
        owner_folder: str = "npc_01_orange_boy",
        owner_role: str = "",
        door: bool = True,
        door_dx: int = 0,
    ) -> PropObject | None:
        raw = self.vault.raw(sprite)
        if raw is None:
            return None
        w = int(raw.get_width() * scale)
        h = int(raw.get_height() * scale)
        spr = self.vault.scaled(sprite, w, h)
        x = int(cx - w / 2)
        y = int(bottom - h)
        col = pygame.Rect(x + 8, y + int(h * 0.40), w - 16, int(h * 0.60) - 6)
        door_rect = pygame.Rect(int(cx - 20 + door_dx), int(bottom - 4), 40, 24) if door else None
        p = PropObject(
            kind="building",
            x=x,
            y=y,
            sprite=spr,
            collider=col,
            door_rect=door_rect,
            house_id=house_id,
            interior_type=interior_type,
            title=title,
            owner_name=owner_name,
            owner_folder=owner_folder,
            owner_role=owner_role,
        )
        self.game.props.append(p)
        return p

    def decal(self, sprite: str, x: int, y: int, w: int | None = None, h: int | None = None):
        """Ảnh dán phẳng xuống nền (nướng vào bề mặt địa hình)."""
        self.game.decals.append((sprite, x, y, w, h))

    # ------------------------------------------------------------------
    # Hàng rào
    # ------------------------------------------------------------------
    def fence_h(self, c0: int, c1: int, r: int, style: str = "rail", gaps: tuple = ()):
        """Hàng rào nằm ngang dọc theo cạnh trên của hàng r."""
        sprite = {"rail": "fence_rail_1", "rail2": "fence_rail_2", "picket": "fence_picket"}[style]
        for c in range(c0, c1 + 1):
            if c in gaps:
                continue
            base_y = r * T + 10
            spr = self.vault.scaled(sprite, T + 2, 26)
            if spr is None:
                continue
            col = pygame.Rect(c * T, base_y - 8, T, 8)
            self.game.props.append(
                PropObject(kind="fence", x=c * T - 1, y=base_y - 26, sprite=spr, collider=col)
            )

    def fence_v(self, c: int, r0: int, r1: int, gaps: tuple = ()):
        """Hàng rào dọc: các cọc gỗ xếp thẳng hàng ở giữa cột c."""
        posts = ("fence_post_1", "fence_post_2", "fence_post_3")
        for r in range(r0, r1 + 1):
            if r in gaps:
                continue
            for half in (0, 1):
                spr = self.vault.scaled(posts[(r + half) % 3], 10, 26)
                if spr is None:
                    continue
                base_y = r * T + half * 16 + 14
                col = pygame.Rect(c * T + T // 2 - 5, base_y - 8, 10, 8)
                self.game.props.append(
                    PropObject(kind="fence", x=c * T + T // 2 - 5, y=base_y - 26, sprite=spr, collider=col)
                )

    def fence_box(
        self,
        c0: int,
        r0: int,
        c1: int,
        r1: int,
        style: str = "rail",
        gate: tuple[str, int] | None = None,
        open_side: str | None = None,
    ):
        """Rào bao quanh vùng ô [c0..c1] x [r0..r1]. gate=("S", cột) đặt cổng; open_side bỏ trống 1 cạnh."""
        gaps_n = gaps_s = gaps_w = gaps_e = ()
        if gate:
            side, idx = gate
            if side == "S":
                gaps_s = (idx, idx + 1)
            elif side == "N":
                gaps_n = (idx, idx + 1)
            elif side == "W":
                gaps_w = (idx,)
            elif side == "E":
                gaps_e = (idx,)
        if open_side != "N":
            self.fence_h(c0, c1, r0, style, gaps_n)
        if open_side != "S":
            self.fence_h(c0, c1, r1 + 1, style, gaps_s)
        if open_side != "W":
            self.fence_v(c0 - 1, r0, r1, gaps_w)
        if open_side != "E":
            self.fence_v(c1 + 1, r0, r1, gaps_e)
        if gate and gate[0] == "S":
            self.prop("fence_gate", (gate[1] + 1) * T, (r1 + 1) * T + 10, w=2 * T, h=28,
                      solid=True, collider_w=1.0, collider_h=8)

    # ------------------------------------------------------------------
    # Ruộng, cây ăn quả, chuồng thú
    # ------------------------------------------------------------------
    def field(
        self,
        c0: int,
        r0: int,
        c1: int,
        r1: int,
        crop: str,
        spot_id: str | None = None,
        title: str = "",
        item_key: str | None = None,
        fence: bool = True,
        scarecrow: bool = False,
        sprinkler: bool = False,
    ) -> HarvestSpot | None:
        """Thửa ruộng đất xới có cây trồng theo hàng; nếu có spot_id thì có thể thu hoạch ở mép dưới."""
        self.fill(c0, r0, c1, r1, T_CROP)
        rect = pygame.Rect(c0 * T, r0 * T, (c1 - c0 + 1) * T, (r1 - r0 + 1) * T)
        if fence:
            self.fence_box(c0, r0, c1, r1, style="rail", open_side="S")
        if scarecrow:
            self.prop("scarecrow", rect.centerx + self.rng.randint(-20, 20), rect.centery + 16,
                      h=60, solid=False)
        if sprinkler:
            self.prop("sprinkler", rect.x + 1.5 * T, rect.bottom - 0.6 * T, h=26, solid=False)
        spot = HarvestSpot(
            spot_id=spot_id or f"deco_{crop}_{c0}_{r0}",
            title=title or f"Ruộng {crop}",
            item_key=item_key or crop,
            x=float(rect.centerx),
            y=float(rect.bottom + 18),
            kind="crop_plot",
            crop_name=crop,
            field_rect=rect,
        )
        if spot_id:
            self.game.harvest_spots.append(spot)
        else:
            # Ruộng trang trí: cây phát triển ở các giai đoạn khác nhau cho sinh động
            spot.has_produce = self.rng.random() < 0.5
            spot.regrow_timer = self.rng.uniform(2.0, 14.0)
            self.game.deco_fields.append(spot)
        return spot

    def fruit_tree(self, spot_id: str, title: str, item_key: str, cx: float, base_y: float,
                   sprite: str = "tree_oak", h: int = 132):
        p = self.tree(sprite, cx, base_y, h=h, solid=True)
        if p is None:
            return
        spot = HarvestSpot(
            spot_id=spot_id,
            title=title,
            item_key=item_key,
            x=float(cx),
            y=float(base_y + 30),
            kind="fruit_tree",
            tree_sprite=sprite,
            tree_x=float(p.x),
            tree_y=float(p.y),
            tree_w=p.sprite.get_width(),
            tree_h=p.sprite.get_height(),
        )
        p.harvest = spot
        self.game.harvest_spots.append(spot)

    def pasture(self, c0: int, r0: int, c1: int, r1: int, animals: list[tuple[str, int]], gate_col: int | None = None):
        self.fence_box(c0, r0, c1, r1, style="rail2", gate=("S", gate_col) if gate_col is not None else None)
        bounds = pygame.Rect(c0 * T, r0 * T, (c1 - c0 + 1) * T, (r1 - r0 + 1) * T)
        for sprite, size in animals:
            ax = self.rng.uniform(bounds.left + 30, bounds.right - 30)
            ay = self.rng.uniform(bounds.top + 30, bounds.bottom - 16)
            self.game.animals.append(FarmAnimal(sprite, ax, ay, bounds, size))
        # Chặn Robot đi vào trong chuồng (thú nuôi không phải đối tượng phục vụ)
        self.game.extra_blockers.append(bounds.inflate(-4, -4))

    def flower_bed(self, c0: int, r0: int, c1: int, r1: int):
        flowers = ("flower_blue", "flower_pink", "flower_white", "flower_yellow_1", "flower_yellow_2", "flower_green")
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                f = flowers[(c * 3 + r * 5) % len(flowers)]
                self.prop(f, c * T + T // 2 + self.rng.randint(-3, 3), r * T + T - 2, h=24, solid=False)

    def scatter(self, sprites: list[str], area: tuple[int, int, int, int], count: int, h: int,
                solid: bool = True, allowed: tuple = (T_GRASS,)):
        """Rải ngẫu nhiên vật trang trí (đá, bụi, gốc cây...) lên các ô cỏ trống."""
        c0, r0, c1, r1 = area
        placed = 0
        tries = 0
        while placed < count and tries < count * 30:
            tries += 1
            c = self.rng.randint(c0, c1)
            r = self.rng.randint(r0, r1)
            if self.get(c, r) not in allowed:
                continue
            px, py = c * T + T // 2, r * T + T - 4
            probe = pygame.Rect(px - 24, py - 24, 48, 36)
            if any(p.collider.colliderect(probe) or (p.kind == "building" and p.view_rect.colliderect(probe))
                   for p in self.game.props):
                continue
            self.prop(self.rng.choice(sprites), px, py, h=h, solid=solid, collider_w=0.6)
            placed += 1

    def lamp(self, cx: float, base_y: float):
        self.prop("lamp_post", cx, base_y, h=78, collider_w=0.5, collider_h=10)

