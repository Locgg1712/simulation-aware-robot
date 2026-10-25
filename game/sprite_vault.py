# game/sprite_vault.py
"""
Bộ nạp và quản lý tài nguyên ảnh Pixel-Art (.png) từ nguồn thư mục `sprites/sprites`.
Hỗ trợ: co giãn + cache, tô màu (tint) cho nội thất từng nhà, khung 9-slice cho giao diện,
và cắt ô địa hình liền mạch (seamless) để mặt đất không bị lặp lại.
"""

from __future__ import annotations

from pathlib import Path
import pygame

FALLBACK_SPRITE_SIZES: dict[str, tuple[int, int]] = {
    "Agv back": (264, 298),
    "Agv front": (264, 305),
    "Agv left": (313, 297),
    "Agv right": (314, 297),
    "Agv up": (236, 300),
    "barrel": (47, 71),
    "bench": (83, 59),
    "bridge_stone": (110, 87),
    "bridge_wood": (108, 85),
    "bush_berry": (86, 80),
    "bush_green": (84, 77),
    "cabbage": (38, 37),
    "carrot": (29, 39),
    "cat": (48, 60),
    "chicken": (62, 66),
    "corn": (30, 44),
    "cow": (89, 75),
    "crate": (60, 62),
    "door_closed": (92, 87),
    "door_closing": (92, 87),
    "door_open": (93, 88),
    "door_opening": (93, 87),
    "fence_gate": (38, 32),
    "fence_picket": (73, 40),
    "fence_post_1": (17, 42),
    "fence_post_2": (18, 42),
    "fence_post_3": (19, 43),
    "fence_rail_1": (58, 42),
    "fence_rail_2": (58, 41),
    "fishpond": (149, 125),
    "floor_wood": (97, 93),
    "flower_blue": (31, 40),
    "flower_green": (32, 42),
    "flower_pink": (31, 35),
    "flower_white": (30, 35),
    "flower_yellow_1": (31, 35),
    "flower_yellow_2": (30, 40),
    "furn_bed": (86, 102),
    "furn_bookshelf": (106, 94),
    "furn_counter": (131, 88),
    "furn_fireplace": (108, 103),
    "furn_plant": (81, 99),
    "furn_rug": (119, 74),
    "furn_table": (107, 96),
    "furn_window": (93, 97),
    "greenhouse": (155, 177),
    "house_barn": (156, 187),
    "house_blue": (134, 170),
    "house_coop": (111, 158),
    "house_farm": (164, 187),
    "house_manor": (181, 186),
    "house_robot": (729, 488),
    "house_shed": (106, 130),
    "house_town": (128, 181),
    "icon_arrow": (37, 34),
    "icon_clock": (35, 34),
    "icon_coin": (31, 32),
    "icon_heart": (36, 33),
    "icon_house": (35, 38),
    "icon_key": (35, 36),
    "icon_parcel": (34, 36),
    "icon_warning": (39, 38),
    "jojamart": (164, 149),
    "lamp_post": (27, 110),
    "log": (126, 71),
    "mailbox": (39, 77),
    "npc_black": (48, 87),
    "npc_blonde": (56, 85),
    "npc_brown": (49, 86),
    "npc_green": (43, 87),
    "npc_old": (45, 84),
    "npc_purple": (59, 85),
    "npc_red": (51, 86),
    "pig": (71, 67),
    "pumpkin": (42, 41),
    "red_mat": (100, 53),
    "rh_barrel_blue1": (54, 81),
    "rh_barrel_blue2": (56, 84),
    "rh_battery_box": (51, 58),
    "rh_bin": (54, 97),
    "rh_bollard": (48, 102),
    "rh_chair_blue": (62, 101),
    "rh_chair_blue2": (66, 104),
    "rh_charging_dock": (177, 168),
    "rh_computer_desk": (171, 157),
    "rh_cone": (64, 85),
    "rh_cooling_unit": (115, 110),
    "rh_crate_low": (72, 83),
    "rh_crate_mid": (94, 97),
    "rh_crate_open": (150, 83),
    "rh_crate_single": (62, 84),
    "rh_crate_tall": (62, 132),
    "rh_crate_top": (94, 91),
    "rh_diag_table": (174, 100),
    "rh_exit_mat": (137, 162),
    "rh_extinguisher": (47, 93),
    "rh_floor_tile": (181, 159),
    "rh_hazard_mat": (114, 164),
    "rh_plant_small": (63, 72),
    "rh_plant_tall": (90, 130),
    "rh_round_table": (175, 142),
    "rh_sensor_post": (37, 115),
    "rh_server_1": (56, 113),
    "rh_server_2": (58, 113),
    "rh_shelf_narrow": (75, 211),
    "rh_shelf_parts": (127, 214),
    "rh_shelf_wide": (197, 212),
    "rh_shutter_wide": (270, 107),
    "rh_solder_station": (130, 96),
    "rh_stool_1": (53, 54),
    "rh_stool_2": (53, 60),
    "rh_stool_3": (50, 68),
    "rh_terminal": (107, 102),
    "rh_tool_cabinet": (91, 129),
    "rh_upgrade_station": (191, 246),
    "rh_wall_arch": (132, 168),
    "rh_wall_doors": (240, 168),
    "rh_wall_screen": (112, 168),
    "rh_wall_vent": (126, 167),
    "rh_whiteboard": (222, 118),
    "rh_workbench_green": (140, 147),
    "robot_collision": (59, 93),
    "robot_down": (57, 90),
    "robot_left": (53, 90),
    "robot_right": (54, 92),
    "robot_up": (56, 89),
    "rock_1": (40, 39),
    "rock_2": (44, 44),
    "rock_3": (45, 45),
    "rock_4": (44, 44),
    "saloon": (127, 174),
    "scarecrow": (67, 98),
    "sheep": (82, 65),
    "shop_pierre": (133, 177),
    "signpost": (58, 83),
    "silo": (99, 196),
    "sprinkler": (55, 52),
    "strawberry": (34, 40),
    "stump": (108, 78),
    "sunflower": (31, 46),
    "tomato": (31, 36),
    "tree_cherry": (135, 172),
    "tree_oak": (144, 186),
    "tree_pine": (121, 187),
    "ui_button_hover": (57, 43),
    "ui_button_normal": (55, 43),
    "ui_button_pressed": (57, 43),
    "ui_panel": (145, 90),
    "wallpaper": (95, 92),
    "well": (72, 93),
    "well_roof": (55, 95),
    "wheat": (28, 45),
    "windmill": (113, 179),
}


class SpriteVault:
    """Tự động nạp và cache các bức ảnh PNG từ `sprites/sprites` (hỗ trợ cả chế độ Headless trên Kaggle)."""

    def __init__(self, root_dir: str | Path | None = None, headless: bool = False):
        self.headless = bool(headless)
        if root_dir is not None and Path(root_dir).exists():
            self.root = Path(root_dir)
        else:
            project_root = Path(__file__).resolve().parents[1]
            candidates = [
                project_root / "sprites" / "sprites",
                project_root / "sprites",
            ]
            self.root = candidates[0]
            for cand in candidates:
                if (cand / "house_farm.png").exists():
                    self.root = cand
                    break

        self._raw: dict[str, pygame.Surface | None] = {}
        self._scaled: dict[tuple, pygame.Surface | None] = {}
        self._item_icons: dict[str, pygame.Surface] = {}
        self._missing: set[str] = set()

        chars_dir = self.root / "characters"
        self.npc_folders = (
            sorted(p.name for p in chars_dir.iterdir() if p.is_dir())
            if chars_dir.exists()
            else []
        )
        self.single_dir_npcs = sorted(
            p.stem for p in self.root.glob("npc_*.png") if p.is_file()
        )

    def get_npc_portrait(self, folder_or_sprite: str, h: int = 64) -> pygame.Surface | None:
        """Lấy ảnh chân dung cho cả NPC nhiều hướng (characters/npc_*) và NPC 1 hướng (npc_*.png)."""
        spr = self.scaled(f"characters/{folder_or_sprite}/down", None, h)
        if spr is not None:
            return spr
        spr = self.scaled(folder_or_sprite, None, h)
        if spr is not None:
            return spr
        if self.npc_folders:
            return self.scaled(f"characters/{self.npc_folders[0]}/down", None, h)
        return None

    # ------------------------------------------------------------------
    # Nạp ảnh gốc & co giãn
    # ------------------------------------------------------------------
    def raw(self, rel_path: str) -> pygame.Surface | None:
        if rel_path not in self._raw:
            clean = rel_path[:-4] if rel_path.lower().endswith(".png") else rel_path
            if self.headless or pygame.display.get_surface() is None:
                size = FALLBACK_SPRITE_SIZES.get(clean)
                if size is None and clean.startswith("characters/"):
                    size = (48, 86)
                if size is not None:
                    self._raw[rel_path] = pygame.Surface(size)
                    return self._raw[rel_path]

            p = self.root / f"{clean}.png"
            if not p.exists():
                p = self.root / f"{clean}.PNG"
            if p.exists():
                if pygame.display.get_surface() is not None:
                    self._raw[rel_path] = pygame.image.load(str(p)).convert_alpha()
                else:
                    self._raw[rel_path] = pygame.image.load(str(p))
            else:
                size = FALLBACK_SPRITE_SIZES.get(clean)
                if size is not None:
                    self._raw[rel_path] = pygame.Surface(size)
                else:
                    self._raw[rel_path] = None
                    self._missing.add(rel_path)
        return self._raw[rel_path]

    def exists(self, rel_path: str) -> bool:
        return self.raw(rel_path) is not None

    def scaled(
        self,
        rel_path: str,
        w: int | None = None,
        h: int | None = None,
        flip_x: bool = False,
        rotate_deg: int = 0,
    ) -> pygame.Surface | None:
        key = (rel_path, w, h, flip_x, rotate_deg)
        if key in self._scaled:
            return self._scaled[key]
        src = self.raw(rel_path)
        if src is None:
            self._scaled[key] = None
            return None
        sw, sh = src.get_size()
        if w is None and h is None:
            tw, th = sw, sh
        elif w is None:
            th = max(1, int(h))
            tw = max(1, int(round(sw * th / sh)))
        elif h is None:
            tw = max(1, int(w))
            th = max(1, int(round(sh * tw / sw)))
        else:
            tw, th = max(1, int(w)), max(1, int(h))

        out = pygame.transform.smoothscale(src, (tw, th))
        if flip_x:
            out = pygame.transform.flip(out, True, False)
        if rotate_deg:
            out = pygame.transform.rotate(out, rotate_deg)
        self._scaled[key] = out
        return out

    def tinted(
        self,
        rel_path: str,
        w: int | None,
        h: int | None,
        tint: tuple[int, int, int],
    ) -> pygame.Surface | None:
        """Ảnh co giãn được nhân màu (BLEND_RGB_MULT) để mỗi ngôi nhà có tông màu riêng."""
        key = ("__tint__", rel_path, w, h, tint)
        if key in self._scaled:
            return self._scaled[key]
        base = self.scaled(rel_path, w, h)
        if base is None:
            self._scaled[key] = None
            return None
        out = base.copy()
        out.fill((*tint, 255), special_flags=pygame.BLEND_RGBA_MULT)
        self._scaled[key] = out
        return out

    def texture_cell(
        self,
        rel_path: str,
        col: int,
        row: int,
        tile: int,
        span: int = 4,
    ) -> pygame.Surface | None:
        """
        Cắt 1 ô (tile x tile) từ ảnh địa hình liền mạch đã co về (span*tile).
        Nhờ vậy cùng một kết cấu trải dài span x span ô mà không bị lặp từng ô.
        """
        big = self.scaled(rel_path, tile * span, tile * span)
        if big is None:
            return None
        key = ("__cell__", rel_path, col % span, row % span, tile, span)
        if key in self._scaled:
            return self._scaled[key]
        sub = big.subsurface(
            pygame.Rect((col % span) * tile, (row % span) * tile, tile, tile)
        ).copy()
        self._scaled[key] = sub
        return sub

    def nine_slice(self, rel_path: str, w: int, h: int, border: int = 12) -> pygame.Surface | None:
        """Khung giao diện 9-slice: giữ nguyên 4 góc, kéo giãn cạnh và phần giữa."""
        key = ("__9s__", rel_path, w, h, border)
        if key in self._scaled:
            return self._scaled[key]
        src = self.raw(rel_path)
        if src is None:
            self._scaled[key] = None
            return None
        sw, sh = src.get_size()
        b = min(border, sw // 3, sh // 3)
        out = pygame.Surface((max(w, 2 * b + 1), max(h, 2 * b + 1)), pygame.SRCALPHA)
        ow, oh = out.get_size()

        def part(x, y, pw, ph):
            return src.subsurface(pygame.Rect(x, y, pw, ph))

        # 4 góc
        out.blit(part(0, 0, b, b), (0, 0))
        out.blit(part(sw - b, 0, b, b), (ow - b, 0))
        out.blit(part(0, sh - b, b, b), (0, oh - b))
        out.blit(part(sw - b, sh - b, b, b), (ow - b, oh - b))
        # 4 cạnh
        out.blit(pygame.transform.smoothscale(part(b, 0, sw - 2 * b, b), (ow - 2 * b, b)), (b, 0))
        out.blit(pygame.transform.smoothscale(part(b, sh - b, sw - 2 * b, b), (ow - 2 * b, b)), (b, oh - b))
        out.blit(pygame.transform.smoothscale(part(0, b, b, sh - 2 * b), (b, oh - 2 * b)), (0, b))
        out.blit(pygame.transform.smoothscale(part(sw - b, b, b, sh - 2 * b), (b, oh - 2 * b)), (ow - b, b))
        # Phần giữa
        out.blit(
            pygame.transform.smoothscale(part(b, b, sw - 2 * b, sh - 2 * b), (ow - 2 * b, oh - 2 * b)),
            (b, b),
        )
        self._scaled[key] = out
        return out

    # ------------------------------------------------------------------
    # Biểu tượng vật phẩm trong Khay Chứa Đồ
    # ------------------------------------------------------------------
    def get_item_icon(self, item_key: str, size: int = 32) -> pygame.Surface:
        cache_key = f"{item_key}_{size}"
        if cache_key in self._item_icons:
            return self._item_icons[cache_key]

        sprite_map = {
            "strawberry": "strawberry",
            "pumpkin": "pumpkin",
            "tomato": "tomato",
            "carrot": "carrot",
            "corn": "corn",
            "cabbage": "cabbage",
            "wheat": "wheat",
            "parcel": "icon_parcel",
            "mushroom": "mushroom_red",
            "wild_berry": "bush_berry",
            "golden_flower": "flower_yellow",
        }
        if item_key in sprite_map:
            spr = self.scaled(sprite_map[item_key], size, size)
            if spr is not None:
                self._item_icons[cache_key] = spr
                return spr

        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        cx, cy = size // 2, size // 2 + 2
        r = int(size * 0.36)

        if item_key == "apple":
            pygame.draw.circle(surf, (220, 42, 42), (cx, cy), r)
            pygame.draw.circle(surf, (255, 110, 100), (cx - r // 3, cy - r // 3), max(2, r // 3))
            pygame.draw.circle(surf, (130, 20, 20), (cx, cy), r, 2)
            pygame.draw.line(surf, (102, 58, 24), (cx, cy - r), (cx + 2, cy - r - 5), 2)
            pygame.draw.ellipse(surf, (76, 184, 62), (cx + 1, cy - r - 4, 8, 5))
        elif item_key == "orange":
            pygame.draw.circle(surf, (245, 142, 28), (cx, cy), r)
            pygame.draw.circle(surf, (255, 200, 85), (cx - r // 3, cy - r // 3), max(2, r // 3))
            pygame.draw.circle(surf, (168, 82, 12), (cx, cy), r, 2)
            pygame.draw.ellipse(surf, (68, 172, 54), (cx, cy - r - 3, 8, 5))
        elif item_key == "peach":
            pygame.draw.circle(surf, (252, 148, 168), (cx, cy), r)
            pygame.draw.circle(surf, (255, 210, 220), (cx - r // 3, cy - r // 3), max(2, r // 3))
            pygame.draw.circle(surf, (198, 72, 102), (cx, cy), r, 2)
            pygame.draw.ellipse(surf, (76, 184, 62), (cx, cy - r - 3, 8, 5))
        elif item_key == "fish":
            pygame.draw.ellipse(surf, (64, 168, 232), (4, cy - 7, size - 12, 14))
            pygame.draw.polygon(
                surf,
                (48, 132, 198),
                [(size - 10, cy), (size - 2, cy - 7), (size - 2, cy + 7)],
            )
            pygame.draw.ellipse(surf, (175, 230, 255), (7, cy - 4, size - 20, 6))
            pygame.draw.circle(surf, (20, 28, 38), (9, cy - 2), 2)
        elif item_key == "bread":
            pygame.draw.ellipse(surf, (218, 148, 68), (4, cy - 8, size - 8, 16))
            pygame.draw.ellipse(surf, (244, 188, 104), (6, cy - 6, size - 12, 10))
            pygame.draw.ellipse(surf, (132, 78, 28), (4, cy - 8, size - 8, 16), 2)
        elif item_key == "iridium_ore":
            pts = [
                (cx, cy - r - 2),
                (cx + r, cy - r // 3),
                (cx + r - 2, cy + r - 1),
                (cx - r + 2, cy + r - 1),
                (cx - r, cy - r // 3),
            ]
            pygame.draw.polygon(surf, (175, 58, 232), pts)
            pygame.draw.polygon(surf, (238, 175, 255), pts, 2)
            pygame.draw.circle(surf, (255, 230, 255), (cx - 2, cy - 3), max(2, r // 4))
        else:
            spr = self.scaled("icon_parcel", size, size)
            if spr is not None:
                surf = spr
            else:
                pygame.draw.rect(surf, (212, 158, 82), (4, 4, size - 8, size - 8), border_radius=4)

        self._item_icons[cache_key] = surf
        return surf
