# asset_builder.py
"""
Bộ sinh tài nguyên đồ họa 16-bit Pixel-Art (.png) tự động cho Stardew Valley RPG Game.
Tự động tạo thư mục assets/stardew/ và lưu các spritesheet/tileset .png có độ chi tiết cao.
"""

from pathlib import Path
import math
import random
import pygame


ASSET_DIR = Path("assets/stardew")


def _px(surf: pygame.Surface, x: int, y: int, col: tuple):
    if 0 <= x < surf.get_width() and 0 <= y < surf.get_height():
        surf.set_at((x, y), col)


def _build_terrain_tiles() -> None:
    """Sinh các tile địa hình 32x32 pixel với độ nhiễu hạt (dithering) tự nhiên."""
    rng = random.Random(101)

    # 1. Cỏ xanh đa sắc độ (4 biến thể)
    for idx in range(4):
        s = pygame.Surface((32, 32), pygame.SRCALPHA)
        base = (98, 168, 64)
        s.fill(base)
        for y in range(32):
            for x in range(32):
                v = rng.random()
                if v < 0.18:
                    _px(s, x, y, (118, 188, 78))
                elif v < 0.32:
                    _px(s, x, y, (82, 148, 52))
                elif v < 0.35:
                    _px(s, x, y, (136, 202, 92))
        # Vài nhánh cỏ & hoa nhỏ trên tile
        if idx in (1, 2):
            fx, fy = rng.randint(6, 24), rng.randint(8, 24)
            pygame.draw.line(s, (64, 128, 42), (fx, fy), (fx - 2, fy - 4), 1)
            pygame.draw.line(s, (64, 128, 42), (fx, fy), (fx + 2, fy - 4), 1)
        if idx == 3:
            fx, fy = 14, 14
            pygame.draw.rect(s, (255, 225, 85), (fx - 2, fy - 2, 5, 5))
            _px(s, fx, fy, (245, 150, 40))
        pygame.image.save(s, str(ASSET_DIR / f"grass_{idx}.png"))

    # 2. Bãi cát vàng (Sand)
    sand = pygame.Surface((32, 32), pygame.SRCALPHA)
    sand.fill((236, 204, 138))
    for y in range(32):
        for x in range(32):
            v = rng.random()
            if v < 0.15:
                _px(sand, x, y, (246, 218, 158))
            elif v < 0.28:
                _px(sand, x, y, (214, 178, 112))
    pygame.image.save(sand, str(ASSET_DIR / "sand.png"))

    # 3. Đường đất mòn (Dirt path)
    dirt = pygame.Surface((32, 32), pygame.SRCALPHA)
    dirt.fill((208, 158, 96))
    for y in range(32):
        for x in range(32):
            v = rng.random()
            if v < 0.16:
                _px(dirt, x, y, (224, 176, 114))
            elif v < 0.30:
                _px(dirt, x, y, (182, 132, 74))
    pygame.image.save(dirt, str(ASSET_DIR / "dirt.png"))

    # 4. Đường lát đá cuội xám (Cobblestone Road - Ảnh 2 & Ảnh 3)
    cobble = pygame.Surface((32, 32), pygame.SRCALPHA)
    cobble.fill((102, 106, 116))
    stones = [
        (1, 1, 14, 9), (16, 1, 15, 9),
        (1, 11, 9, 10), (11, 11, 12, 10), (24, 11, 7, 10),
        (1, 22, 15, 9), (17, 22, 14, 9),
    ]
    for sx, sy, sw, sh in stones:
        pygame.draw.rect(cobble, (144, 148, 158), (sx, sy, sw, sh), border_radius=2)
        pygame.draw.line(cobble, (168, 172, 182), (sx + 1, sy + 1), (sx + sw - 2, sy + 1), 1)
        pygame.draw.line(cobble, (118, 122, 132), (sx + 1, sy + sh - 1), (sx + sw - 2, sy + sh - 1), 1)
    pygame.image.save(cobble, str(ASSET_DIR / "cobble.png"))

    # 5. Vách đá đồi 3D (Brown Cliff Wall - Ảnh 2, 3, 4)
    cliff = pygame.Surface((32, 32), pygame.SRCALPHA)
    cliff.fill((112, 74, 38))
    for rx, ry, rw, rh in [(2, 2, 13, 12), (16, 3, 14, 11), (1, 15, 15, 14), (17, 16, 13, 13)]:
        pygame.draw.rect(cliff, (138, 92, 48), (rx, ry, rw, rh), border_radius=3)
        pygame.draw.rect(cliff, (158, 108, 58), (rx + 2, ry + 1, rw - 4, 4), border_radius=2)
        pygame.draw.rect(cliff, (78, 48, 22), (rx, ry, rw, rh), 1, border_radius=3)
    # Viền cỏ rủ xuống mép trên vách đá
    pygame.draw.rect(cliff, (68, 132, 44), (0, 0, 32, 4))
    pygame.image.save(cliff, str(ASSET_DIR / "cliff.png"))

    # 6. Ô đất ruộng canh tác & cây trồng (Crop Plot)
    crop = pygame.Surface((32, 32), pygame.SRCALPHA)
    crop.fill((132, 78, 40))
    for y in range(4, 30, 8):
        pygame.draw.line(crop, (108, 60, 28), (2, y), (29, y), 2)
    for cy in (9, 23):
        for cx in (9, 23):
            pygame.draw.circle(crop, (56, 146, 52), (cx, cy), 5)
            pygame.draw.circle(crop, (88, 186, 72), (cx - 1, cy - 1), 3)
            pygame.draw.circle(crop, (238, 72, 64), (cx + 2, cy - 1), 2)
    pygame.image.save(crop, str(ASSET_DIR / "crop.png"))


def _build_tree_sprites() -> None:
    """Sinh 3 loại cây Pixel-Art lớn có tán lá đa tầng & bóng đổ (Cherry Blossom, Oak, Pine)."""
    tree_specs = [
        ("tree_cherry.png", (184, 78, 126), (228, 124, 168), (252, 176, 210), (255, 222, 238)),
        ("tree_oak.png", (34, 96, 46), (54, 138, 62), (82, 172, 74), (114, 198, 96)),
        ("tree_pine.png", (26, 78, 58), (38, 112, 76), (58, 146, 94), (86, 174, 114)),
    ]
    rng = random.Random(202)

    for fname, c_dark, c_mid, c_light, c_hi in tree_specs:
        w, h = 76, 96
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        cx = w // 2

        # Bóng đổ dưới gốc
        sh = pygame.Surface((52, 22), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (16, 28, 14, 95), (0, 0, 52, 22))
        surf.blit(sh, (cx - 26, h - 24))

        # Thân gỗ & rễ cây
        pygame.draw.rect(surf, (108, 62, 30), (cx - 8, h - 42, 16, 30), border_radius=3)
        pygame.draw.rect(surf, (148, 92, 48), (cx - 5, h - 42, 7, 28), border_radius=2)
        pygame.draw.line(surf, (78, 42, 18), (cx - 8, h - 42), (cx - 8, h - 14), 2)

        if "pine" in fname:
            # Cây thông 3 tầng tam giác bầu
            layers = [(cx, 48, 30, 26), (cx, 34, 25, 24), (cx, 20, 18, 20)]
            for lx, ly, rx, ry in layers:
                pygame.draw.ellipse(surf, c_dark, (lx - rx, ly - ry // 2, rx * 2, ry + 6))
                pygame.draw.ellipse(surf, c_mid, (lx - rx + 3, ly - ry // 2, rx * 2 - 6, ry))
                pygame.draw.ellipse(surf, c_light, (lx - rx + 6, ly - ry // 2 + 1, rx * 2 - 12, ry - 5))
        else:
            # Tán cây tròn nhiều cụm lá kiểu Stardew Valley
            blobs = [
                (cx, 42, 28), (cx - 16, 40, 20), (cx + 16, 40, 20),
                (cx - 10, 26, 21), (cx + 10, 26, 21), (cx, 22, 22),
            ]
            for bx, by, br in blobs:
                pygame.draw.circle(surf, c_dark, (bx, by + 3), br)
            for bx, by, br in blobs:
                pygame.draw.circle(surf, c_mid, (bx, by), int(br * 0.88))
            for bx, by, br in blobs[2:]:
                pygame.draw.circle(surf, c_light, (bx, by - 2), int(br * 0.72))

            # Hạt lá chi tiết (Leaf clusters)
            for _ in range(95):
                ang = rng.uniform(0, math.tau)
                rad = rng.uniform(2, 25)
                px = int(cx + math.cos(ang) * rad * 1.1)
                py = int(32 + math.sin(ang) * rad * 0.85)
                col = c_hi if py < 30 else (c_light if rng.random() < 0.6 else c_dark)
                pygame.draw.circle(surf, col, (px, py), rng.randint(2, 3))

        pygame.image.save(surf, str(ASSET_DIR / fname))


def _build_building_sprites() -> None:
    """Sinh các công trình kiến trúc Stardew Valley (.png nền trong suốt)."""

    def make_cottage(
        fname: str,
        w: int,
        h: int,
        roof_col: tuple,
        roof_dark: tuple,
        wall_col: tuple,
        is_barn: bool = False,
        sign_text: str = "",
    ):
        surf = pygame.Surface((w + 12, h + 12), pygame.SRCALPHA)
        # Bóng đổ
        pygame.draw.rect(surf, (16, 26, 14, 95), (8, 10, w, h), border_radius=6)

        roof_h = int(h * 0.54)
        wall_y = roof_h - 4
        wall_h = h - wall_y

        # Tường nhà
        pygame.draw.rect(surf, wall_col, (4, wall_y, w - 4, wall_h), border_radius=3)
        for wy in range(wall_y + 6, wall_y + wall_h - 4, 6):
            pygame.draw.line(surf, (195, 168, 130) if not is_barn else (152, 44, 38), (6, wy), (w - 4, wy), 1)
        pygame.draw.rect(surf, (92, 52, 24), (4, wall_y, w - 4, wall_h), 2, border_radius=3)

        # Ống khói
        if not is_barn and w >= 110:
            pygame.draw.rect(surf, (148, 72, 62), (w - 28, 2, 14, 22))
            pygame.draw.rect(surf, (96, 44, 38), (w - 30, 2, 18, 5))

        # Mái ngói dốc có vân ngói
        pygame.draw.rect(surf, roof_col, (2, 6, w, roof_h), border_radius=5)
        for ry in range(12, roof_h + 2, 6):
            pygame.draw.line(surf, roof_dark, (5, ry), (w - 2, ry), 2)
        for rx in range(10, w - 6, 12):
            pygame.draw.line(surf, roof_dark, (rx, 8), (rx, roof_h + 3), 1)
        pygame.draw.rect(surf, (78, 42, 18), (2, 6, w, roof_h), 2, border_radius=5)
        pygame.draw.line(surf, (255, 220, 180), (6, 9), (w - 4, 9), 2)

        # Cửa ra vào + Thảm đỏ chào mừng
        door_w = 34 if is_barn else 24
        door_h = 34 if is_barn else 32
        door_x = 2 + w // 2 - door_w // 2
        door_y = h - door_h
        pygame.draw.rect(surf, (82, 46, 20), (door_x, door_y, door_w, door_h), border_radius=3)
        pygame.draw.rect(surf, (168, 108, 56), (door_x + 3, door_y + 3, door_w - 6, door_h - 3), border_radius=2)
        if is_barn:
            # Cửa chuồng gia súc chữ X trắng
            pygame.draw.line(surf, (245, 240, 230), (door_x + 3, door_y + 3), (door_x + door_w - 4, door_y + door_h - 2), 2)
            pygame.draw.line(surf, (245, 240, 230), (door_x + door_w - 4, door_y + 3), (door_x + 3, door_y + door_h - 2), 2)
        else:
            pygame.draw.circle(surf, (255, 215, 65), (door_x + door_w - 6, door_y + door_h // 2), 2)

        # Thảm đỏ trước cửa
        pygame.draw.rect(surf, (208, 64, 58), (door_x - 3, h, door_w + 6, 7), border_radius=2)
        pygame.draw.rect(surf, (250, 210, 110), (door_x - 3, h, door_w + 6, 7), 1, border_radius=2)

        # Cửa sổ phát sáng vàng ấm áp
        win_y = wall_y + 10
        for wx in [16, w - 38]:
            if abs(wx - door_x) > 22:
                pygame.draw.rect(surf, (255, 236, 142), (wx, win_y, 22, 20))
                pygame.draw.rect(surf, (88, 48, 22), (wx, win_y, 22, 20), 2)
                pygame.draw.line(surf, (88, 48, 22), (wx + 11, win_y), (wx + 11, win_y + 20), 2)
                pygame.draw.line(surf, (88, 48, 22), (wx, win_y + 10), (wx + 22, win_y + 10), 2)

        pygame.image.save(surf, str(ASSET_DIR / fname))

    # 1. Nhà chính nông trại (Farmhouse), Chuồng Bò (Barn), Nhà Xanh, Quán Saloon, Biệt thự
    make_cottage("house_farm.png", 136, 108, (204, 72, 58), (152, 44, 36), (244, 224, 186))
    make_cottage("house_barn.png", 128, 104, (178, 56, 48), (128, 36, 30), (202, 68, 58), is_barn=True)
    make_cottage("house_blue.png", 116, 98, (68, 116, 176), (44, 78, 126), (218, 232, 248))
    make_cottage("house_town.png", 132, 106, (186, 84, 52), (136, 54, 32), (246, 218, 178))
    make_cottage("house_manor.png", 138, 110, (92, 74, 118), (62, 48, 84), (238, 232, 224))

    # 2. Nhà Kính Trong Suốt (Glass Greenhouse - Ảnh 2 & Ảnh 4)
    gh_w, gh_h = 116, 128
    gh = pygame.Surface((gh_w + 10, gh_h + 10), pygame.SRCALPHA)
    pygame.draw.rect(gh, (16, 28, 14, 85), (6, 8, gh_w, gh_h), border_radius=8)
    pygame.draw.rect(gh, (188, 228, 244, 215), (2, 4, gh_w, gh_h), border_radius=8)
    # Cây xanh lấp ló bên trong nhà kính
    for py in range(26, gh_h - 24, 18):
        for px in range(18, gh_w - 14, 20):
            pygame.draw.circle(gh, (76, 168, 82, 190), (px, py), 7)
    # Khung kính trắng xanh
    for gx in range(18, gh_w, 18):
        pygame.draw.line(gh, (238, 250, 255), (gx, 6), (gx, gh_h), 2)
    for gy in range(22, gh_h, 20):
        pygame.draw.line(gh, (238, 250, 255), (4, gy), (gh_w, gy), 2)
    pygame.draw.rect(gh, (104, 148, 172), (2, 4, gh_w, gh_h), 3, border_radius=8)
    # Cửa nhà kính + Thảm đỏ
    dx = 2 + gh_w // 2 - 12
    pygame.draw.rect(gh, (124, 78, 40), (dx, gh_h - 26, 24, 30), border_radius=3)
    pygame.draw.rect(gh, (208, 64, 58), (dx - 2, gh_h + 2, 28, 6), border_radius=2)
    pygame.image.save(gh, str(ASSET_DIR / "greenhouse.png"))

    # 3. Tháp Ủ Cỏ Đỏ (Red Brick Silo - Ảnh 2 & Ảnh 4)
    silo = pygame.Surface((54, 112), pygame.SRCALPHA)
    pygame.draw.ellipse(silo, (16, 28, 14, 90), (4, 92, 46, 16))
    pygame.draw.rect(silo, (176, 66, 56), (8, 26, 38, 76), border_radius=4)
    for by in range(32, 98, 7):
        pygame.draw.line(silo, (136, 46, 38), (10, by), (44, by), 1)
    pygame.draw.circle(silo, (212, 76, 64), (27, 26), 19)
    pygame.draw.arc(silo, (122, 36, 30), (8, 7, 38, 38), 0, math.pi, 3)
    pygame.draw.rect(silo, (118, 38, 32), (8, 26, 38, 76), 2, border_radius=4)
    pygame.image.save(silo, str(ASSET_DIR / "silo.png"))

    # 4. Siêu thị JojaMart (Ảnh 3)
    jm_w, jm_h = 148, 104
    jm = pygame.Surface((jm_w + 10, jm_h + 10), pygame.SRCALPHA)
    pygame.draw.rect(jm, (16, 28, 14, 90), (6, 8, jm_w, jm_h), border_radius=6)
    pygame.draw.rect(jm, (58, 108, 178), (2, 4, jm_w, jm_h), border_radius=5)
    pygame.draw.rect(jm, (212, 234, 252), (6, 8, jm_w - 8, 32), border_radius=4)
    pygame.draw.rect(jm, (34, 68, 124), (2, 4, jm_w, jm_h), 3, border_radius=5)
    dx = 2 + jm_w // 2 - 16
    pygame.draw.rect(jm, (165, 225, 255), (dx, jm_h - 30, 32, 34), border_radius=2)
    pygame.draw.rect(jm, (208, 64, 58), (dx - 2, jm_h + 2, 36, 6), border_radius=2)
    pygame.image.save(jm, str(ASSET_DIR / "jojamart.png"))

    # 5. Hồ nuôi cá viền đá (Fish Pond - Ảnh 4)
    fp = pygame.Surface((68, 68), pygame.SRCALPHA)
    pygame.draw.rect(fp, (112, 118, 128), (2, 2, 64, 64), border_radius=10)
    pygame.draw.rect(fp, (48, 128, 192), (8, 8, 52, 52), border_radius=7)
    pygame.draw.rect(fp, (84, 168, 228), (14, 14, 40, 40), border_radius=5)
    pygame.draw.rect(fp, (78, 84, 94), (2, 2, 64, 64), 2, border_radius=10)
    pygame.image.save(fp, str(ASSET_DIR / "fishpond.png"))


def ensure_assets() -> Path:
    """Kiểm tra và tự động sinh toàn bộ file .png nếu chưa tồn tại."""
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    required = [
        "grass_0.png", "sand.png", "cobble.png", "cliff.png", "crop.png",
        "tree_cherry.png", "tree_oak.png", "tree_pine.png",
        "house_farm.png", "house_barn.png", "greenhouse.png", "silo.png", "jojamart.png", "fishpond.png",
    ]
    if all((ASSET_DIR / f).exists() for f in required):
        return ASSET_DIR

    print("[AssetBuilder] Generating Pixel-Art assets in 'assets/stardew/'...")
    _build_terrain_tiles()
    _build_tree_sprites()
    _build_building_sprites()
    print("[AssetBuilder] Pixel-Art assets generated successfully.")
    return ASSET_DIR


if __name__ == "__main__":
    pygame.init()
    ensure_assets()
    pygame.quit()