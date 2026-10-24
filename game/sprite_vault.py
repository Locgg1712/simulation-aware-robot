# game/sprite_vault.py
"""
Bộ nạp và quản lý tài nguyên ảnh Pixel-Art (.png) từ nguồn thư mục `sprites/sprites`.
Hỗ trợ: co giãn + cache, tô màu (tint) cho nội thất từng nhà, khung 9-slice cho giao diện,
và cắt ô địa hình liền mạch (seamless) để mặt đất không bị lặp lại.
"""

from __future__ import annotations

from pathlib import Path
import pygame


class SpriteVault:
    """Tự động nạp và cache các bức ảnh PNG từ `sprites/sprites`."""

    def __init__(self, root_dir: str | Path | None = None):
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
            p = self.root / f"{clean}.png"
            if not p.exists():
                p = self.root / f"{clean}.PNG"
            if p.exists():
                self._raw[rel_path] = pygame.image.load(str(p)).convert_alpha()
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
        else:
            spr = self.scaled("icon_parcel", size, size)
            if spr is not None:
                surf = spr
            else:
                pygame.draw.rect(surf, (212, 158, 82), (4, 4, size - 8, size - 8), border_radius=4)

        self._item_icons[cache_key] = surf
        return surf
