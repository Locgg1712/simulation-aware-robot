# visualization/stardew_sprites.py
"""
Bộ tạo Sprite và Texture phong cách Stardew Valley Pixel-Art (16-bit RPG).
Cung cấp đồ họa đỉnh cao cho:
- Robot (Farm Automaton / Steampunk Helper với mắt LED cảm xúc, xích xe, ăng-ten ngọc).
- Con người (Villagers & Farmers: Nông dân mũ rơm, Cô gái thị trấn cài hoa, Bác sĩ, Thợ mỏ,
  đầy đủ khuôn mặt, mắt, má hồng, hoạt ảnh bước đi, bong bóng cảm xúc).
- Xe goòng mỏ (Minecart chở đá thạch anh tím lấp lánh & đèn lồng hổ phách).
- Chướng ngại vật (Thùng ủ rượu sồi, Tường đá rêu phong leo dây thường xuân).
- Vùng đích (Grand Stardrop Shrine: Bệ đá rune, vòng hoa cổ tích, Sao vàng lơ lửng, biển gỗ GOAL).
- Terrain (Đồng cỏ Stardew 8 biến thể hoa dại, sỏi đá, lối mòn).
"""

import math
import random
import pygame


# ═══════════════════════════════════════════════════════════════════════════
#  BẢNG MÀU CHUẨN STARDEW VALLEY (Earthy, Warm, Pastoral 16-bit)
# ═══════════════════════════════════════════════════════════════════════════
PALETTE = {
    # Cỏ & Thực vật
    "grass_dark": (50, 115, 30),
    "grass_mid": (72, 148, 38),
    "grass_light": (102, 186, 52),
    "grass_bright": (132, 214, 68),
    "grass_tuft": (42, 95, 24),
    "flower_yellow": (255, 220, 60),
    "flower_white": (250, 250, 240),
    "flower_red": (230, 75, 75),
    "flower_blue": (100, 160, 245),
    "flower_pink": (255, 160, 190),
    "flower_stem": (38, 90, 22),

    # Đất & Đường mòn
    "dirt_light": (214, 175, 120),
    "dirt_mid": (178, 134, 82),
    "dirt_dark": (130, 92, 52),
    "dirt_shadow": (95, 65, 35),

    # Đá & Tường đá (Cobblestone)
    "stone_light": (185, 180, 170),
    "stone_mid": (135, 130, 120),
    "stone_dark": (95, 90, 82),
    "stone_shadow": (55, 50, 45),
    "moss_green": (75, 145, 45),
    "moss_bright": (115, 185, 55),

    # Gỗ (Rustic Oak & Pine)
    "wood_light": (190, 140, 85),
    "wood_mid": (145, 95, 48),
    "wood_dark": (100, 62, 30),
    "wood_shadow": (65, 38, 18),
    "iron_band": (75, 75, 85),
    "iron_highlight": (130, 130, 145),

    # Robot (Maru's Farm Automaton / Junimo-bot)
    "bot_brass": (225, 170, 60),
    "bot_brass_dark": (160, 110, 30),
    "bot_copper": (210, 125, 70),
    "bot_copper_dark": (145, 75, 35),
    "bot_metal": (115, 135, 160),
    "bot_metal_light": (165, 190, 215),
    "bot_metal_dark": (60, 75, 95),
    "bot_screen": (22, 35, 45),
    "bot_eye_glow": (80, 245, 225),
    "bot_eye_blink": (35, 110, 100),
    "bot_antenna_glow": (255, 235, 90),
    "bot_collision": (230, 55, 55),

    # NPC Villagers
    "skin_light": (255, 222, 188),
    "skin_mid": (240, 190, 150),
    "skin_shadow": (205, 150, 110),
    "skin_blush": (255, 165, 165),
    "hair_brown": (105, 62, 32),
    "hair_blonde": (240, 205, 95),
    "hair_red": (200, 75, 45),
    "hair_black": (45, 40, 48),
    "hat_straw": (235, 210, 120),
    "hat_straw_band": (185, 45, 45),
    "cloth_farmer_blue": (55, 110, 195),
    "cloth_farmer_shirt": (215, 75, 60),
    "cloth_dress_green": (60, 150, 88),
    "cloth_coat_brown": (130, 88, 52),
    "boot_leather": (70, 45, 25),

    # Xe mỏ (Minecart)
    "cart_wood": (125, 78, 42),
    "cart_iron": (65, 65, 75),
    "cart_wheel": (45, 45, 55),
    "crystal_purple": (195, 95, 245),
    "crystal_sparkle": (245, 215, 255),
    "gold_ore": (255, 220, 65),

    # Điểm đích (Stardrop / Golden Star)
    "star_gold_light": (255, 250, 165),
    "star_gold_mid": (255, 215, 40),
    "star_gold_dark": (215, 155, 20),
    "star_outline": (160, 105, 10),
    "stardrop_purple": (175, 55, 225),
    "pedestal_stone": (145, 140, 130),
    "pedestal_dark": (88, 82, 76),

    # UI / HUD
    "parchment_bg": (248, 238, 210),
    "hud_wood_base": (45, 26, 14),
    "hud_wood_mid": (105, 68, 38),
    "hud_wood_light": (160, 112, 65),
    "hud_wood_dark": (30, 16, 8),
    "hud_gold_trim": (230, 190, 65),
    "hud_text_parchment": (250, 242, 220),
}


class StardewSpriteEngine:
    """Hệ thống tạo & bộ đệm (cache) sprite pixel-art phong cách Stardew Valley cao cấp."""

    def __init__(self, scale: float):
        self.scale = scale  # pixels / mét
        self._cache = {}
        self._tile_cache = None

    # ═══════════════════════════════════════════════════════════════════════
    #  TERRAIN TILES (Đồng cỏ Stardew hoa dại, sỏi đá)
    # ═══════════════════════════════════════════════════════════════════════

    def get_terrain_tile(self, tile_type: int) -> pygame.Surface:
        """Lấy tile cỏ 32x32 với các biến thể hoa cúc, hoa trắng, cỏ lau, sỏi đá."""
        if self._tile_cache is None:
            self._init_terrain_tiles()
        return self._tile_cache[tile_type % len(self._tile_cache)]

    def _init_terrain_tiles(self):
        """Khởi tạo 8 biến thể tile cỏ đồng quê Stardew Valley rực rỡ."""
        self._tile_cache = []
        tile_size = 32

        for variant in range(8):
            surf = pygame.Surface((tile_size, tile_size))
            surf.fill(PALETTE["grass_mid"])
            rng = random.Random(variant * 101 + 42)

            # Dithering cỏ tự nhiên
            for y in range(tile_size):
                for x in range(tile_size):
                    val = rng.random()
                    if val < 0.18:
                        surf.set_at((x, y), PALETTE["grass_dark"])
                    elif val < 0.35:
                        surf.set_at((x, y), PALETTE["grass_light"])
                    elif val < 0.42:
                        surf.set_at((x, y), PALETTE["grass_bright"])

            # Cụm lá cỏ nhọn
            num_blades = rng.randint(2, 5)
            for _ in range(num_blades):
                bx = rng.randint(2, tile_size - 4)
                by = rng.randint(4, tile_size - 4)
                surf.set_at((bx, by), PALETTE["grass_tuft"])
                surf.set_at((bx, by - 1), PALETTE["grass_tuft"])
                surf.set_at((bx + 1, by - 2), PALETTE["grass_bright"])
                surf.set_at((bx - 1, by - 1), PALETTE["grass_dark"])

            # Các loại hoa & sỏi
            if variant in (1, 5):  # Hoa cúc vàng Dandelion
                fx, fy = rng.randint(6, 26), rng.randint(6, 26)
                surf.set_at((fx, fy), PALETTE["flower_yellow"])
                surf.set_at((fx + 1, fy), PALETTE["flower_yellow"])
                surf.set_at((fx, fy + 1), PALETTE["flower_yellow"])
                surf.set_at((fx + 1, fy + 1), (255, 185, 40))
                surf.set_at((fx, fy + 2), PALETTE["flower_stem"])

            elif variant in (2, 6):  # Hoa cúc trắng White Daisy
                fx, fy = rng.randint(6, 26), rng.randint(6, 26)
                surf.set_at((fx, fy), PALETTE["flower_white"])
                surf.set_at((fx - 1, fy), (230, 230, 220))
                surf.set_at((fx + 1, fy), (230, 230, 220))
                surf.set_at((fx, fy - 1), (230, 230, 220))
                surf.set_at((fx, fy + 1), (230, 230, 220))
                surf.set_at((fx, fy), PALETTE["flower_yellow"])

            elif variant == 3:  # Hoa chuông xanh Bluebell
                fx, fy = rng.randint(6, 26), rng.randint(6, 26)
                surf.set_at((fx, fy), PALETTE["flower_blue"])
                surf.set_at((fx + 1, fy), (150, 190, 255))
                surf.set_at((fx, fy + 1), PALETTE["flower_stem"])

            elif variant == 4:  # Viên sỏi nhẵn & mầm cỏ non
                px, py = rng.randint(6, 24), rng.randint(6, 24)
                surf.set_at((px, py), PALETTE["stone_mid"])
                surf.set_at((px + 1, py), PALETTE["stone_light"])
                surf.set_at((px, py + 1), PALETTE["stone_dark"])
                surf.set_at((px + 1, py + 1), PALETTE["stone_shadow"])

            self._tile_cache.append(surf)

    # ═══════════════════════════════════════════════════════════════════════
    #  ROBOT SPRITE (Maru's Farm Automaton / Steampunk Helper)
    # ═══════════════════════════════════════════════════════════════════════

    def get_robot_sprite(
        self,
        radius_px: int,
        theta: float,
        frame_count: int,
        is_collision: bool = False,
    ) -> pygame.Surface:
        """
        Tạo sprite Robot Automaton chân thực phong cách Stardew:
        - Thân hình hộp bo tròn mạ đồng/thau, góc đinh tán kim loại.
        - Xích xe lăn 2 bên có rãnh cao su xoay chuyển.
        - Màn hình CRT hiển thị đôi mắt pixel LED xanh ngọc biết biểu cảm & chớp mắt.
        - Ăng-ten lò xo đỉnh đầu gắn bóng ngọc phát tín hiệu vàng hổ phách.
        - Cánh tay cơ khí nhỏ mạ thau hai bên.
        - Mũi tên định hướng xoay theo góc robot theta.
        """
        w = max(42, radius_px * 2 + 20)
        h = max(42, radius_px * 2 + 20)
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        cx, cy = w // 2, h // 2
        r = radius_px

        # 1. Bóng đổ mềm dưới chân (Drop shadow)
        shadow_w, shadow_h = int(r * 2.5), int(r * 1.2)
        shadow_surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (20, 25, 15, 80), shadow_surf.get_rect())
        surf.blit(shadow_surf, (cx - shadow_w // 2, cy + int(r * 0.35)))

        # 2. Xích xe lăn 2 bên (Dual Treads)
        tread_w = max(5, int(r * 0.35))
        tread_h = int(r * 1.8)
        # Bánh trái và bánh phải
        for side in (-1, 1):
            tx = cx - int(r * 1.1) if side == -1 else cx + int(r * 1.1) - tread_w
            ty = cy - tread_h // 2
            tread_rect = pygame.Rect(tx, ty, tread_w, tread_h)
            pygame.draw.rect(surf, PALETTE["bot_metal_dark"], tread_rect, border_radius=2)
            pygame.draw.rect(surf, (35, 45, 55), tread_rect, 1, border_radius=2)
            # Rãnh xích xoay chuyển
            t_offset = (frame_count % 4)
            for gy in range(ty + t_offset, ty + tread_h, 4):
                pygame.draw.line(surf, PALETTE["bot_metal_light"], (tx, gy), (tx + tread_w - 1, gy), 1)

        # 3. Thân máy cơ khí chính (Rounded brass chassis)
        body_col = PALETTE["bot_collision"] if is_collision else PALETTE["bot_brass"]
        dark_col = (150, 30, 30) if is_collision else PALETTE["bot_brass_dark"]

        body_rect = pygame.Rect(cx - r, cy - r, r * 2, r * 2)
        pygame.draw.rect(surf, dark_col, body_rect, border_radius=7)
        inner_rect = body_rect.inflate(-4, -4)
        pygame.draw.rect(surf, body_col, inner_rect, border_radius=6)

        # Viền kim loại bóng nổi
        pygame.draw.line(surf, (255, 235, 140), (body_rect.left + 5, body_rect.top + 2),
                         (body_rect.right - 5, body_rect.top + 2), 2)
        pygame.draw.line(surf, dark_col, (body_rect.left + 3, body_rect.bottom - 2),
                         (body_rect.right - 3, body_rect.bottom - 2), 2)

        # 4 đinh tán đồng 4 góc
        for rx_off, ry_off in [(-r + 4, -r + 4), (r - 6, -r + 4),
                               (-r + 4, r - 6), (r - 6, r - 6)]:
            pygame.draw.circle(surf, PALETTE["iron_highlight"], (cx + rx_off, cy + ry_off), 2)
            surf.set_at((cx + rx_off, cy + ry_off), (255, 255, 255))

        # Cánh tay gắp cơ khí nhỏ 2 bên
        for side in (-1, 1):
            arm_x = cx + side * (r + 1)
            pygame.draw.rect(surf, PALETTE["bot_brass_dark"], (arm_x - 1, cy - 3, 3, 6), border_radius=1)
            pygame.draw.circle(surf, PALETTE["bot_brass"], (arm_x, cy), 3)

        # 4. Màn hình kính CRT hiển thị mắt
        screen_w = max(14, int(r * 1.25))
        screen_h = max(10, int(r * 0.85))
        screen_rect = pygame.Rect(cx - screen_w // 2, cy - screen_h // 2 - 1, screen_w, screen_h)
        pygame.draw.rect(surf, PALETTE["bot_screen"], screen_rect, border_radius=3)
        pygame.draw.rect(surf, (15, 25, 30), screen_rect, 1, border_radius=3)

        # Mắt LED phát sáng & chớp mắt
        is_blinking = (frame_count % 80) in (0, 1, 2)
        eye_col = (255, 80, 80) if is_collision else (PALETTE["bot_eye_blink"] if is_blinking else PALETTE["bot_eye_glow"])
        eye_sz = max(2, int(r * 0.22))
        eye_y = cy - 1

        for side in (-1, 1):
            eye_x = cx + side * int(screen_w * 0.26)
            if is_collision:
                # Mắt hình chữ X khi va chạm
                pygame.draw.line(surf, eye_col, (eye_x - 2, eye_y - 2), (eye_x + 2, eye_y + 2), 2)
                pygame.draw.line(surf, eye_col, (eye_x - 2, eye_y + 2), (eye_x + 2, eye_y - 2), 2)
            elif is_blinking:
                pygame.draw.line(surf, eye_col, (eye_x - eye_sz, eye_y), (eye_x + eye_sz, eye_y), 2)
            else:
                pygame.draw.circle(surf, eye_col, (eye_x, eye_y), eye_sz)
                surf.set_at((eye_x - 1, eye_y - 1), (255, 255, 255))

        # 5. Ăng-ten lò xo với bóng ngọc phát sáng
        ant_x = cx
        ant_top = cy - r - 5
        pygame.draw.line(surf, PALETTE["iron_highlight"], (ant_x, cy - r), (ant_x, ant_top), 2)
        pulse = 0.5 + 0.5 * math.sin(frame_count * 0.25)
        glow_r = int(2 + 2 * pulse)
        glow_surf = pygame.Surface((glow_r * 2 + 2, glow_r * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*PALETTE["bot_antenna_glow"], int(140 + 115 * pulse)),
                           (glow_r + 1, glow_r + 1), glow_r)
        surf.blit(glow_surf, (ant_x - glow_r - 1, ant_top - glow_r - 1))
        pygame.draw.circle(surf, (255, 255, 240), (ant_x, ant_top), 2)

        # 6. Mũi tên định hướng mạ vàng xoay theo góc theta
        arrow_len = int(r * 1.35)
        hx = cx + int(arrow_len * math.cos(theta))
        hy = cy + int(arrow_len * math.sin(theta))
        pygame.draw.line(surf, PALETTE["hud_gold_trim"], (cx, cy), (hx, hy), 3)
        pygame.draw.circle(surf, (255, 255, 220), (hx, hy), 3)
        pygame.draw.circle(surf, (160, 110, 20), (hx, hy), 4, 1)

        return surf

    # ═══════════════════════════════════════════════════════════════════════
    #  HUMAN NPC SPRITES (Dân làng & Nông dân Stardew Valley chuẩn 3/4)
    # ═══════════════════════════════════════════════════════════════════════

    def get_human_sprite(
        self,
        radius_px: int,
        theta: float,
        speed: float,
        activity_str: str,
        human_id: int,
        frame_count: int,
        is_talking: bool = False,
    ) -> pygame.Surface:
        """
        Tạo sprite nhân vật người Stardew Valley nhìn góc 3/4 top-down:
        - Khuôn mặt rõ ràng, mắt đen có điểm sáng, hai gò má ửng hồng.
        - Mũ rơm nông dân nghiêng ra sau, tóc vàng/nâu/đỏ buông lọn.
        - Áo sơ mi kẻ, quần yếm bò với cúc đồng, hoặc váy xanh dịu dàng.
        - Hoạt ảnh bước chân nhún nhảy và vung chân so le.
        - Bong bóng thoại tương tác biểu cảm ('...', '♥', '♪').
        """
        w = max(44, radius_px * 2 + 22)
        h = max(52, radius_px * 2 + 30)
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        cx = w // 2
        cy = h // 2 + 5
        r = radius_px

        variant = human_id % 4

        # Hoạt ảnh nhún bước (Bobbing cycle)
        is_moving = speed > 0.05
        bob_offset = int(math.sin(frame_count * 0.45 + human_id) * 2) if is_moving else 0
        cy += bob_offset

        # 1. Bóng đổ dưới chân (Drop shadow)
        shadow_w, shadow_h = int(r * 2.3), int(r * 1.0)
        shadow_surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (20, 25, 15, 75), shadow_surf.get_rect())
        surf.blit(shadow_surf, (cx - shadow_w // 2, cy + int(r * 0.6)))

        # 2. Chân & Giày da (Bước chân so le)
        foot_stride = int(math.sin(frame_count * 0.5 + human_id) * 4) if is_moving else 0
        boot_col = PALETTE["boot_leather"]
        pygame.draw.ellipse(surf, boot_col, (cx - 7, cy + r - 3 + foot_stride, 5, 7))
        pygame.draw.ellipse(surf, boot_col, (cx + 2, cy + r - 3 - foot_stride, 5, 7))

        # 3. Phối màu theo từng nhân vật
        if variant == 0:  # Nông dân (Farmer)
            shirt_col = PALETTE["cloth_farmer_shirt"]
            pants_col = PALETTE["cloth_farmer_blue"]
            hair_col = PALETTE["hair_brown"]
            hat_type = "straw"
        elif variant == 1:  # Nữ cư dân thị trấn váy xanh cài hoa
            shirt_col = PALETTE["cloth_dress_green"]
            pants_col = (45, 95, 60)
            hair_col = PALETTE["hair_red"]
            hat_type = "flower"
        elif variant == 2:  # Bác sĩ / Học giả áo khoác dài
            shirt_col = PALETTE["cloth_coat_brown"]
            pants_col = (40, 40, 50)
            hair_col = PALETTE["hair_blonde"]
            hat_type = "none"
        else:  # Thợ mỏ đội mũ bảo hộ
            shirt_col = (210, 145, 45)
            pants_col = (50, 50, 60)
            hair_col = PALETTE["hair_black"]
            hat_type = "miner"

        # 4. Thân áo & Quần (Torso & Overalls)
        torso_w = int(r * 1.45)
        torso_h = int(r * 1.35)
        torso_rect = pygame.Rect(cx - torso_w // 2, cy - torso_h // 2, torso_w, torso_h)
        pygame.draw.rect(surf, shirt_col, torso_rect, border_radius=3)

        # Quần yếm / Váy
        overalls_h = torso_h // 2 + 2
        overalls_rect = pygame.Rect(cx - torso_w // 2, cy, torso_w, overalls_h)
        pygame.draw.rect(surf, pants_col, overalls_rect, border_radius=2)
        # Dây yếm với cúc đồng
        pygame.draw.line(surf, pants_col, (cx - torso_w // 4, cy - torso_h // 2), (cx - torso_w // 4, cy), 2)
        pygame.draw.line(surf, pants_col, (cx + torso_w // 4, cy - torso_h // 2), (cx + torso_w // 4, cy), 2)
        surf.set_at((cx - torso_w // 4, cy - 1), (255, 215, 60))
        surf.set_at((cx + torso_w // 4, cy - 1), (255, 215, 60))

        # Hai bàn tay nhỏ hai bên
        hand_col = PALETTE["skin_light"]
        pygame.draw.circle(surf, hand_col, (cx - torso_w // 2 - 1, cy + 2), 2)
        pygame.draw.circle(surf, hand_col, (cx + torso_w // 2 + 1, cy + 2), 2)

        # 5. Đầu & Tóc sau (Head & Back Hair)
        head_r = max(5, int(r * 0.72))
        head_y = cy - int(r * 0.85)

        # Tóc nền phía sau
        pygame.draw.circle(surf, hair_col, (cx, head_y - 2), head_r + 2)

        # Khuôn mặt tông da ấm
        pygame.draw.circle(surf, PALETTE["skin_shadow"], (cx, head_y + 1), head_r)
        pygame.draw.circle(surf, PALETTE["skin_light"], (cx, head_y), head_r)

        # 6. Đôi mắt và má hồng dễ thương Stardew
        eye_y = head_y
        surf.set_at((cx - 3, eye_y), (40, 30, 25))
        surf.set_at((cx - 3, eye_y - 1), (20, 15, 10))
        surf.set_at((cx + 2, eye_y), (40, 30, 25))
        surf.set_at((cx + 2, eye_y - 1), (20, 15, 10))
        # Điểm sáng trong mắt
        surf.set_at((cx - 4, eye_y - 1), (255, 255, 255))
        surf.set_at((cx + 1, eye_y - 1), (255, 255, 255))

        # Má hồng ửng dễ thương (Blushing cheeks)
        surf.set_at((cx - 5, eye_y + 2), PALETTE["skin_blush"])
        surf.set_at((cx + 4, eye_y + 2), PALETTE["skin_blush"])

        # 7. Mũ hoặc Kiểu tóc
        if hat_type == "straw":
            # Mũ rơm nghiêng ra sau (không che mất mắt và mặt)
            hat_w = int(head_r * 2.5)
            hat_h = int(head_r * 1.1)
            hat_rect = pygame.Rect(cx - hat_w // 2, head_y - head_r - 4, hat_w, hat_h)
            pygame.draw.ellipse(surf, PALETTE["hat_straw"], hat_rect)
            pygame.draw.ellipse(surf, (190, 165, 80), hat_rect, 1)
            # Chóp mũ & Ruy băng đỏ
            crown_rect = pygame.Rect(cx - head_r, head_y - head_r - 8, head_r * 2, head_r + 2)
            pygame.draw.ellipse(surf, PALETTE["hat_straw"], crown_rect)
            pygame.draw.line(surf, PALETTE["hat_straw_band"], (cx - head_r + 2, head_y - head_r - 2),
                             (cx + head_r - 2, head_y - head_r - 2), 2)

        elif hat_type == "flower":
            # Tóc dày gợn sóng + Bông hoa hồng cài tóc
            hair_rect = pygame.Rect(cx - head_r - 2, head_y - head_r - 2, head_r * 2 + 4, head_r + 4)
            pygame.draw.ellipse(surf, hair_col, hair_rect)
            # Bông hoa cài bên tai
            pygame.draw.circle(surf, PALETTE["flower_pink"], (cx + head_r, head_y - 3), 3)
            pygame.draw.circle(surf, (255, 255, 255), (cx + head_r, head_y - 3), 1)

        elif hat_type == "miner":
            # Mũ bảo hộ thợ mỏ vàng có đèn
            helmet_rect = pygame.Rect(cx - head_r - 1, head_y - head_r - 6, head_r * 2 + 2, head_r + 4)
            pygame.draw.ellipse(surf, (240, 200, 45), helmet_rect)
            pygame.draw.ellipse(surf, (180, 140, 20), helmet_rect, 1)
            # Đèn pha trên mũ
            pygame.draw.circle(surf, (255, 255, 240), (cx, head_y - head_r - 4), 2)

        else:
            # Tóc bồng bềnh phong trần
            hair_rect = pygame.Rect(cx - head_r - 1, head_y - head_r - 4, head_r * 2 + 2, head_r + 5)
            pygame.draw.ellipse(surf, hair_col, hair_rect)

        # 8. Bong bóng thoại cảm xúc khi tương tác nói chuyện (Emote Balloon)
        if is_talking:
            bubble_y = head_y - head_r - 19
            bubble_w, bubble_h = 24, 16
            bubble_rect = pygame.Rect(cx - bubble_w // 2, bubble_y, bubble_w, bubble_h)
            pygame.draw.rect(surf, PALETTE["parchment_bg"], bubble_rect, border_radius=4)
            pygame.draw.rect(surf, (80, 50, 30), bubble_rect, 1, border_radius=4)
            # Đuôi bóng thoại
            pygame.draw.polygon(surf, PALETTE["parchment_bg"],
                                [(cx - 3, bubble_y + bubble_h),
                                 (cx + 3, bubble_y + bubble_h),
                                 (cx, bubble_y + bubble_h + 4)])
            pygame.draw.lines(surf, (80, 50, 30), False,
                              [(cx - 3, bubble_y + bubble_h),
                               (cx, bubble_y + bubble_h + 4),
                               (cx + 3, bubble_y + bubble_h)], 1)

            # Ba chấm động "..." hoặc trái tim đỏ
            if human_id % 2 == 0:
                dot_phase = (frame_count // 10) % 3
                for i in range(3):
                    dy = bubble_y + bubble_h // 2 - (2 if i == dot_phase else 0)
                    pygame.draw.circle(surf, (70, 45, 25), (cx - 6 + i * 6, dy), 2)
            else:
                # Trái tim đỏ nhỏ
                hy = bubble_y + 4
                pygame.draw.circle(surf, (230, 60, 60), (cx - 2, hy), 2)
                pygame.draw.circle(surf, (230, 60, 60), (cx + 2, hy), 2)
                pygame.draw.polygon(surf, (230, 60, 60), [(cx - 4, hy + 1), (cx + 4, hy + 1), (cx, hy + 6)])

        return surf

    # ═══════════════════════════════════════════════════════════════════════
    #  DYNAMIC OBSTACLE SPRITE (Xe goòng hầm mỏ Minecart)
    # ═══════════════════════════════════════════════════════════════════════

    def get_minecart_sprite(
        self,
        radius_px: int,
        theta: float,
        frame_count: int,
    ) -> pygame.Surface:
        """
        Tạo xe goòng hầm mỏ Stardew Valley:
        - Thùng gỗ ép gia cố thanh thép đen và đinh tán góc.
        - Chứa đầy thạch anh tím & quặng vàng lấp lánh.
        - Đèn bão bập bùng phía trước tỏa ánh sáng ấm.
        - 4 bánh xe sắt xoay chuyển.
        """
        w = max(40, radius_px * 2 + 18)
        h = max(40, radius_px * 2 + 18)
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        cx, cy = w // 2, h // 2
        r = radius_px

        # Bóng đổ
        shadow_w, shadow_h = int(r * 2.4), int(r * 1.1)
        shadow_surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (20, 25, 15, 80), shadow_surf.get_rect())
        surf.blit(shadow_surf, (cx - shadow_w // 2, cy + int(r * 0.4)))

        # Bánh xe sắt 4 góc
        wheel_r = max(2, int(r * 0.3))
        for wx, wy in [(-r + 2, -r + 2), (r - 4, -r + 2),
                       (-r + 2, r - 4), (r - 4, r - 4)]:
            pygame.draw.circle(surf, PALETTE["cart_wheel"], (cx + wx, cy + wy), wheel_r)
            pygame.draw.circle(surf, PALETTE["iron_band"], (cx + wx, cy + wy), wheel_r, 1)

        # Thùng gỗ xe goòng
        cart_rect = pygame.Rect(cx - r, cy - r + 2, r * 2, r * 2 - 4)
        pygame.draw.rect(surf, PALETTE["cart_wood"], cart_rect, border_radius=4)
        pygame.draw.rect(surf, PALETTE["cart_iron"], cart_rect, 2, border_radius=4)
        pygame.draw.line(surf, PALETTE["cart_iron"], (cart_rect.left, cy), (cart_rect.right, cy), 2)

        # Đinh tán góc
        for rx, ry in [(cart_rect.left + 2, cart_rect.top + 2),
                       (cart_rect.right - 3, cart_rect.top + 2),
                       (cart_rect.left + 2, cart_rect.bottom - 3),
                       (cart_rect.right - 3, cart_rect.bottom - 3)]:
            surf.set_at((rx, ry), PALETTE["iron_highlight"])

        # Khoáng thạch lấp lánh
        gem_rect = cart_rect.inflate(-6, -6)
        pygame.draw.rect(surf, (30, 20, 35), gem_rect)
        rng = random.Random(77)
        for _ in range(8):
            gx = rng.randint(gem_rect.left + 2, gem_rect.right - 4)
            gy = rng.randint(gem_rect.top + 2, gem_rect.bottom - 4)
            gem_col = PALETTE["crystal_purple"] if rng.random() > 0.35 else PALETTE["gold_ore"]
            pygame.draw.rect(surf, gem_col, (gx, gy, 3, 3))
            if (frame_count + gx) % 20 < 4:
                surf.set_at((gx, gy), PALETTE["crystal_sparkle"])

        # Đèn bão treo phía trước (Lantern)
        lx = cx + int(r * 1.15 * math.cos(theta))
        ly = cy + int(r * 1.15 * math.sin(theta))
        lantern_glow = pygame.Surface((20, 20), pygame.SRCALPHA)
        pygame.draw.circle(lantern_glow, (255, 200, 60, 95), (10, 10), 9)
        surf.blit(lantern_glow, (lx - 10, ly - 10))
        pygame.draw.circle(surf, (255, 240, 160), (lx, ly), 3)
        pygame.draw.circle(surf, (160, 90, 20), (lx, ly), 4, 1)

        return surf

    # ═══════════════════════════════════════════════════════════════════════
    #  STATIC OBSTACLES (Thùng rượu sồi & Tường đá Cobblestone)
    # ═══════════════════════════════════════════════════════════════════════

    def get_barrel_pillar_sprite(self, radius_px: int) -> pygame.Surface:
        """Tạo thùng ủ rượu gỗ sồi (Oak Wine Barrel) Stardew Valley."""
        key = ("barrel", radius_px)
        if key in self._cache:
            return self._cache[key]

        w = radius_px * 2 + 12
        h = radius_px * 2 + 12
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        cx, cy = w // 2, h // 2
        r = radius_px

        # Bóng đổ
        shadow_w, shadow_h = int(r * 2.3), int(r * 1.1)
        shadow_surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (20, 25, 15, 75), shadow_surf.get_rect())
        surf.blit(shadow_surf, (cx - shadow_w // 2, cy + int(r * 0.4)))

        # Thân thùng tròn
        pygame.draw.circle(surf, PALETTE["wood_dark"], (cx, cy), r)
        pygame.draw.circle(surf, PALETTE["wood_mid"], (cx, cy), max(2, r - 2))

        # Các nan gỗ cong
        for dy in range(-r + 4, r - 3, max(4, r // 3)):
            half_x = int(math.sqrt(max(0, r * r - dy * dy)) * 0.88)
            pygame.draw.line(surf, PALETTE["wood_dark"], (cx - half_x, cy + dy),
                             (cx + half_x, cy + dy), 1)

        # Đai sắt gia cố
        pygame.draw.circle(surf, PALETTE["iron_band"], (cx, cy), int(r * 0.65), 2)
        pygame.draw.circle(surf, PALETTE["iron_highlight"], (cx - 2, cy - 2), int(r * 0.65), 1)
        pygame.draw.circle(surf, PALETTE["iron_band"], (cx, cy), int(r * 0.35), 1)

        # Lỗ thùng rượu
        pygame.draw.circle(surf, PALETTE["wood_shadow"], (cx, cy), max(2, r // 6))
        pygame.draw.circle(surf, PALETTE["wood_light"], (cx - 1, cy - 1), max(1, r // 8))

        # Viền thùng
        pygame.draw.circle(surf, PALETTE["wood_shadow"], (cx, cy), r, 2)
        self._cache[key] = surf
        return surf

    def draw_cobblestone_wall(
        self,
        target_surf: pygame.Surface,
        sx: int,
        sy: int,
        sw: int,
        sh: int,
    ):
        """Vẽ tường đá phong cách Stardew Valley (Cobblestone masonry có phủ rêu)."""
        rect = pygame.Rect(sx, sy, sw, sh)
        pygame.draw.rect(target_surf, PALETTE["stone_mid"], rect)

        # Hoa văn gạch đá so le
        brick_h = max(5, min(14, sh // max(1, sh // 10)))
        brick_w = max(8, min(20, sw // max(1, sw // 12)))

        row_idx = 0
        for y in range(sy, sy + sh, brick_h):
            row_idx += 1
            cur_h = min(brick_h, sy + sh - y)
            pygame.draw.line(target_surf, PALETTE["stone_shadow"], (sx, y), (sx + sw, y), 1)

            offset = (brick_w // 2) if row_idx % 2 == 0 else 0
            for x in range(sx + offset, sx + sw, brick_w):
                pygame.draw.line(target_surf, PALETTE["stone_dark"], (x, y), (x, y + cur_h), 1)
                target_surf.set_at((x + 2, y + 2), PALETTE["stone_light"])

        # Nẹp gỗ đỉnh tường
        pygame.draw.line(target_surf, PALETTE["wood_mid"], (sx, sy), (sx + sw - 1, sy), 2)
        pygame.draw.line(target_surf, PALETTE["wood_light"], (sx, sy + 1), (sx + sw - 1, sy + 1), 1)

        # Đốm rêu xanh
        rng = random.Random(sx * 31 + sy * 17)
        for _ in range(max(1, (sw * sh) // 280)):
            mx = rng.randint(sx + 2, sx + max(3, sw - 4))
            my = rng.randint(sy + 2, sy + max(3, sh - 4))
            target_surf.set_at((mx, my), PALETTE["moss_green"])
            target_surf.set_at((mx + 1, my), PALETTE["moss_bright"])

        pygame.draw.rect(target_surf, PALETTE["stone_shadow"], rect, 1)

    # ═══════════════════════════════════════════════════════════════════════
    #  GRAND GOAL MONUMENT (Stardew Valley Golden Star / Stardrop Shrine)
    # ═══════════════════════════════════════════════════════════════════════

    def draw_grand_goal(
        self,
        target_surf: pygame.Surface,
        gx: int,
        gy: int,
        goal_radius_px: int,
        frame_count: int,
    ):
        """
        Vẽ Vùng Đích đại cảnh phong cách Stardew Valley:
        - Bệ thờ đá tròn khắc cổ tự ma thuật (Carved Stone Altar).
        - Vòng hoa dại thần tiên (Fairy Ring) tỏa hào quang.
        - Ngôi sao vàng Stardrop khổng lồ lơ lửng nhấp nhô (Floating levitation).
        - Bụi sao lấp lánh (Sparkling Fairy Dust).
        - Biển gỗ mộc mạc ghi chữ "★ GOAL ★".
        """
        t = frame_count * 0.08
        r = goal_radius_px

        # 1. Hào quang vàng tỏa rộng
        pulse = 1.0 + 0.18 * math.sin(t * 1.8)
        aura_r = int(r * 2.3 * pulse)
        aura_surf = pygame.Surface((aura_r * 2 + 4, aura_r * 2 + 4), pygame.SRCALPHA)
        alpha_outer = int(35 + 20 * math.sin(t * 2.0))
        alpha_inner = int(75 + 30 * math.sin(t * 2.0))

        pygame.draw.circle(aura_surf, (*PALETTE["star_gold_light"], alpha_outer),
                           (aura_r + 2, aura_r + 2), aura_r)
        pygame.draw.circle(aura_surf, (*PALETTE["star_gold_mid"], alpha_inner),
                           (aura_r + 2, aura_r + 2), int(aura_r * 0.65))
        target_surf.blit(aura_surf, (gx - aura_r - 2, gy - aura_r - 2))

        # 2. Vòng hoa dại cổ tích (Fairy Ring)
        num_flowers = 14
        for i in range(num_flowers):
            angle = (2 * math.pi * i / num_flowers) + (t * 0.1)
            dist = r * 1.6
            fx = gx + int(dist * math.cos(angle))
            fy = gy + int(dist * math.sin(angle))
            flower_col = PALETTE["flower_yellow"] if i % 2 == 0 else PALETTE["flower_white"]
            pygame.draw.circle(target_surf, flower_col, (fx, fy), 3)
            pygame.draw.circle(target_surf, (255, 180, 40), (fx, fy), 1)

        # 3. Bệ đá tròn có khắc rune
        pedestal_r = int(r * 1.3)
        ped_shadow = pygame.Surface((pedestal_r * 2 + 8, int(pedestal_r * 0.8)), pygame.SRCALPHA)
        pygame.draw.ellipse(ped_shadow, (20, 25, 15, 90), ped_shadow.get_rect())
        target_surf.blit(ped_shadow, (gx - pedestal_r - 4, gy + int(pedestal_r * 0.3)))

        pygame.draw.circle(target_surf, PALETTE["pedestal_dark"], (gx, gy + 3), pedestal_r)
        pygame.draw.circle(target_surf, PALETTE["pedestal_stone"], (gx, gy), pedestal_r)
        pygame.draw.circle(target_surf, (190, 185, 175), (gx - 2, gy - 2), pedestal_r - 3, 2)
        pygame.draw.circle(target_surf, PALETTE["pedestal_dark"], (gx, gy), pedestal_r, 2)

        # Các ký tự Rune ma thuật
        for i in range(8):
            ra = 2 * math.pi * i / 8
            rx = gx + int(pedestal_r * 0.72 * math.cos(ra))
            ry = gy + int(pedestal_r * 0.72 * math.sin(ra))
            pygame.draw.rect(target_surf, (220, 195, 100), (rx - 1, ry - 1, 3, 3))

        # 4. Ngôi sao vàng Stardrop bay lơ lửng
        float_y = int(math.sin(t * 2.2) * 5) - 4
        sgx, sgy = gx, gy + float_y

        num_pts = 5
        star_outer = int(r * 1.2 * (1.0 + 0.08 * math.sin(t * 3.0)))
        star_inner = int(star_outer * 0.44)
        rot_angle = -math.pi / 2 + math.sin(t * 0.8) * 0.15

        outer_pts = []
        inner_pts = []
        for i in range(num_pts * 2):
            ang = rot_angle + math.pi * i / num_pts
            cur_r = star_outer if i % 2 == 0 else star_inner
            outer_pts.append((sgx + int(cur_r * math.cos(ang)),
                              sgy + int(cur_r * math.sin(ang))))
            inner_cur_r = int(cur_r * 0.6)
            inner_pts.append((sgx + int(inner_cur_r * math.cos(ang)),
                              sgy + int(inner_cur_r * math.sin(ang))))

        if len(outer_pts) >= 3:
            pygame.draw.polygon(target_surf, PALETTE["star_outline"], outer_pts, 3)
            pygame.draw.polygon(target_surf, PALETTE["star_gold_mid"], outer_pts)
            pygame.draw.polygon(target_surf, PALETTE["star_gold_light"], inner_pts)
            pygame.draw.circle(target_surf, (255, 255, 240), (sgx, sgy), max(2, star_inner // 2))

        # 5. Hạt bụi sao thần tiên
        for i in range(6):
            sp_ang = t * (1.2 + i * 0.5) + i * 1.3
            sp_d = r * (1.4 + 0.6 * math.sin(t * 1.7 + i))
            sp_x = gx + int(sp_d * math.cos(sp_ang))
            sp_y = gy + int(sp_d * math.sin(sp_ang)) + float_y // 2
            sp_sz = max(1, int(2 + math.sin(t * 3.5 + i)))
            pygame.draw.circle(target_surf, (255, 255, 220), (sp_x, sp_y), sp_sz)

        # 6. Biển gỗ mộc mạc "★ GOAL ★"
        sign_w, sign_h = 80, 22
        sign_x, sign_y = gx - sign_w // 2, gy + pedestal_r + 4
        sign_rect = pygame.Rect(sign_x, sign_y, sign_w, sign_h)
        pygame.draw.rect(target_surf, PALETTE["wood_mid"], sign_rect, border_radius=4)
        pygame.draw.rect(target_surf, PALETTE["wood_dark"], sign_rect, 2, border_radius=4)
        pygame.draw.line(target_surf, PALETTE["wood_light"], (sign_x + 2, sign_y + 2),
                         (sign_x + sign_w - 3, sign_y + 2), 1)

        # Đinh gắn 2 bên
        pygame.draw.circle(target_surf, PALETTE["iron_highlight"], (sign_x + 5, sign_y + sign_h // 2), 2)
        pygame.draw.circle(target_surf, PALETTE["iron_highlight"], (sign_x + sign_w - 6, sign_y + sign_h // 2), 2)

        try:
            goal_font = pygame.font.SysFont("consolas", 12, bold=True)
            text_surf = goal_font.render("★ GOAL ★", True, PALETTE["hud_gold_trim"])
            target_surf.blit(text_surf, (gx - text_surf.get_width() // 2, sign_y + 3))
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════════════════════
    #  WOODEN BARN DOOR (Cửa nông trại trượt)
    # ═══════════════════════════════════════════════════════════════════════

    def draw_barn_door(
        self,
        target_surf: pygame.Surface,
        sx: int,
        sy: int,
        sw: int,
        sh: int,
        state_str: str,
    ):
        """Vẽ cửa gỗ trượt nông trại kiểu Stardew Valley."""
        rect = pygame.Rect(sx, sy, sw, sh)

        if state_str == "OPEN":
            open_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
            pygame.draw.rect(open_surf, (60, 145, 85, 50), open_surf.get_rect())
            pygame.draw.rect(open_surf, PALETTE["wood_dark"], open_surf.get_rect(), 2)
            target_surf.blit(open_surf, (sx, sy))
        else:
            is_transition = state_str in ("OPENING", "CLOSING")
            base_col = (195, 135, 50) if is_transition else PALETTE["wood_mid"]
            pygame.draw.rect(target_surf, base_col, rect)

            # Nan gỗ dọc
            plank_w = max(4, sw // max(1, sw // 8))
            for px in range(sx, sx + sw, plank_w):
                pygame.draw.line(target_surf, PALETTE["wood_dark"], (px, sy), (px, sy + sh), 1)

            # Khung chữ Z
            pygame.draw.line(target_surf, PALETTE["wood_dark"], (sx + 2, sy + 2),
                             (sx + sw - 2, sy + sh - 2), 3)
            pygame.draw.line(target_surf, PALETTE["wood_light"], (sx + 2, sy + 4),
                             (sx + sw - 2, sy + sh), 1)

            # Tay nắm cửa đồng
            handle_x, handle_y = sx + sw // 2, sy + sh // 2
            pygame.draw.circle(target_surf, (40, 40, 50), (handle_x, handle_y), 3)
            pygame.draw.circle(target_surf, (220, 180, 60), (handle_x, handle_y), 2)
            pygame.draw.rect(target_surf, PALETTE["wood_dark"], rect, 2)
